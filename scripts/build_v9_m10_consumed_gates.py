#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs  # noqa: E402
from norway_company_agent.v9_m2_targeting import (  # noqa: E402
    build_targeted_m2_cohort,
    classify_m2_candidate_slot,
)


DEFAULT_CANARIES = (
    "999096298",  # M2 site/social/careers/contact transfer
    "979943377",  # M4 structured contact transfer
    "927097532",  # M5 company-authored hiring intent
)


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inject_required_canaries(
    selected_rows: list[dict[str, Any]],
    *,
    canaries: list[str],
    profile_by_org: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep all causal M2 rows while forcing known consumed transfer canaries into Gate B.

    Gate B is a regression/transfer cohort, not a fresh qualification sample. Replacing only
    the lowest-priority control rows ensures that no behaviorally affected M2 row is silently
    dropped while M4/M5 canaries are exercised too.
    """
    rows = [dict(item) for item in selected_rows]
    removed: list[dict[str, Any]] = []
    existing = {str(item.get("organisation_number") or "") for item in rows}

    for org in canaries:
        if org in existing:
            continue
        if org not in profile_by_org:
            raise ValueError(f"required consumed canary {org} is missing from source population")

        replace_index = None
        for preferred in ("no_email_control", "preserved_email_control"):
            for index in range(len(rows) - 1, -1, -1):
                item = rows[index]
                item_org = str(item.get("organisation_number") or "")
                if item_org in canaries:
                    continue
                if item.get("bucket") == preferred:
                    replace_index = index
                    break
            if replace_index is not None:
                break
        if replace_index is None:
            raise ValueError(
                "cannot force M10 canary without dropping a behaviorally affected M2 row"
            )

        removed.append(rows.pop(replace_index))
        classified = classify_m2_candidate_slot(profile_by_org[org])
        classified = {
            **classified,
            "original_bucket": classified.get("bucket"),
            "bucket": "forced_canary",
            "canary_reason": (
                "previously-consumed positive transfer row required for M10 regression coverage"
            ),
        }
        rows.append(classified)
        existing.add(org)

    if len(rows) != len(selected_rows):
        raise AssertionError("Gate B size changed while injecting canaries")
    if len({str(item.get("organisation_number") or "") for item in rows}) != len(rows):
        raise AssertionError("Gate B contains duplicate organisation numbers")
    return rows, removed


def build_gate_a(
    gate_b_rows: list[dict[str, Any]],
    *,
    canaries: list[str],
    target_count: int = 20,
) -> list[dict[str, Any]]:
    if target_count < len(canaries):
        raise ValueError("Gate A target_count is smaller than required canary count")
    by_org = {
        str(item.get("organisation_number") or ""): dict(item)
        for item in gate_b_rows
    }
    missing = [org for org in canaries if org not in by_org]
    if missing:
        raise ValueError(f"Gate A canaries missing from Gate B: {missing}")

    selected = [by_org[org] for org in canaries]
    remaining = sorted(
        (
            dict(item)
            for item in gate_b_rows
            if str(item.get("organisation_number") or "") not in set(canaries)
        ),
        key=lambda item: str(item.get("organisation_number") or ""),
    )
    selected.extend(remaining[: target_count - len(selected)])
    if len(selected) != target_count:
        raise ValueError(f"insufficient Gate B rows for Gate A target_count={target_count}")
    return selected


def _manifest_rows(rows: list[dict[str, Any]], *, split: str) -> list[dict[str, Any]]:
    return [
        {
            "organisation_number": str(item["organisation_number"]),
            "evaluation_split": split,
            "sample_slice": str(item.get("bucket") or "unknown"),
        }
        for item in rows
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic consumed Gate A (20) and Gate B (100) cohorts for V9 M10."
    )
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--bulk", type=Path, required=True)
    parser.add_argument("--gate-a-output", type=Path, required=True)
    parser.add_argument("--gate-b-output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--gate-a-count", type=int, default=20)
    parser.add_argument("--gate-b-count", type=int, default=100)
    parser.add_argument("--canary", action="append", default=[])
    args = parser.parse_args()

    canaries = list(args.canary or DEFAULT_CANARIES)
    if len(canaries) != len(set(canaries)):
        raise ValueError("canaries contain duplicates")
    if any(len(org) != 9 or not org.isdigit() for org in canaries):
        raise ValueError(f"invalid organisation-number canary: {canaries}")

    source_inputs = read_organisation_inputs(args.source_manifest)
    source_orgs = [row["organisation_number"] for row in source_inputs]
    if len(source_orgs) != 1000 or len(set(source_orgs)) != 1000:
        raise ValueError(
            f"expected frozen consumed source population of 1000 unique companies, got {len(source_orgs)}"
        )

    profiles, snapshot = profiles_from_bulk(args.bulk, source_orgs)
    profile_by_org = {
        str(profile.get("organisation_number") or ""): profile
        for profile in profiles
    }
    missing_canaries = [org for org in canaries if org not in profile_by_org]
    if missing_canaries:
        raise ValueError(f"required canaries missing from current BRREG bulk: {missing_canaries}")

    _, base_rows, base_report = build_targeted_m2_cohort(
        profiles,
        target_count=args.gate_b_count,
    )
    gate_b_rows, removed_controls = inject_required_canaries(
        base_rows,
        canaries=canaries,
        profile_by_org=profile_by_org,
    )
    gate_a_rows = build_gate_a(
        gate_b_rows,
        canaries=canaries,
        target_count=args.gate_a_count,
    )

    gate_a_manifest = _manifest_rows(gate_a_rows, split="v9_m10_consumed_gate_a")
    gate_b_manifest = _manifest_rows(gate_b_rows, split="v9_m10_consumed_gate_b")
    _write_jsonl(args.gate_a_output, gate_a_manifest)
    _write_jsonl(args.gate_b_output, gate_b_manifest)

    selected_gate_b = {row["organisation_number"] for row in gate_b_manifest}
    if not set(canaries).issubset(selected_gate_b):
        raise AssertionError("Gate B does not contain every required canary")
    if any(org not in set(source_orgs) for org in selected_gate_b):
        raise AssertionError("M10 Gate B contains a company outside the consumed source population")

    audit_rows = []
    gate_a_set = {row["organisation_number"] for row in gate_a_manifest}
    for item in gate_b_rows:
        org = str(item.get("organisation_number") or "")
        audit_rows.append(
            {
                **item,
                "in_gate_a": org in gate_a_set,
                "in_gate_b": True,
                "required_canary": org in set(canaries),
            }
        )
    _write_jsonl(args.audit, audit_rows)

    report = {
        "screen_type": "v9_m10_consumed_transfer_gates",
        "source_manifest_companies": len(source_orgs),
        "source_manifest_sha256": _sha256(args.source_manifest),
        "fresh_companies_used": 0,
        "gate_a_companies": len(gate_a_manifest),
        "gate_b_companies": len(gate_b_manifest),
        "gate_a_manifest_sha256": _sha256(args.gate_a_output),
        "gate_b_manifest_sha256": _sha256(args.gate_b_output),
        "required_canaries": canaries,
        "gate_a_canaries": [
            row["organisation_number"]
            for row in gate_a_manifest
            if row["organisation_number"] in set(canaries)
        ],
        "gate_b_canaries": [
            row["organisation_number"]
            for row in gate_b_manifest
            if row["organisation_number"] in set(canaries)
        ],
        "gate_a_bucket_counts": dict(
            sorted(Counter(row["sample_slice"] for row in gate_a_manifest).items())
        ),
        "gate_b_bucket_counts": dict(
            sorted(Counter(row["sample_slice"] for row in gate_b_manifest).items())
        ),
        "gate_b_removed_controls": removed_controls,
        "m2_behaviorally_affected_companies_in_gate_b": sum(
            1 for row in gate_b_rows if row.get("bucket") == "m2_delta"
        ),
        "base_m2_target_report": base_report,
        "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
        "registry_snapshot_missing_count": snapshot.get("missing_count"),
        "selection_rule": [
            "start from deterministic consumed M2 causal-exposure Gate B 100",
            "never drop an m2_delta row when forcing cross-milestone canaries",
            "force known consumed M2/M4/M5 positive rows by replacing lowest-priority controls only",
            "Gate A = all required canaries plus lexicographically first remaining Gate B controls/affected rows",
            "all rows come from the frozen already-consumed 1000-company source population",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
