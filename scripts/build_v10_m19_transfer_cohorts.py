#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs
from norway_company_agent.h1g_hyphenated_no_recall import hyphenated_no_candidate

M13B_TARGET_MANIFEST_SHA256 = "eddd8ed807f1116a3fd2d780b21796d546717fd3a27ee7983d8a89d14d891cbe"

KNOWN_RESEARCHED_ORGS = {
    "927097532", "979943377", "999096298",
    "828829092", "870418892", "896488562", "898321622",
    "911546221", "914384729", "936455298", "976533194",
    "979436661", "988936987", "992784229", "996405524",
    "811413682", "811730912", "883971752", "923609016",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_orgs(path: Path) -> set[str]:
    rows = read_organisation_inputs(path)
    values = {str(row["organisation_number"]) for row in rows}
    if len(values) != len(rows):
        raise ValueError(f"{path}: duplicate organisation numbers")
    return values


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    ).encode("utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(jsonl_bytes(rows))


def reconstruct_m13b(
    profiles: list[dict[str, Any]],
    *,
    base_excluded: set[str],
) -> tuple[set[str], str]:
    eligible: list[str] = []
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        if org in base_excluded:
            continue
        if str(profile.get("website") or "").strip():
            continue
        if hyphenated_no_candidate(profile) is None:
            continue
        eligible.append(org)
    eligible.sort()
    if len(eligible) < 100:
        raise ValueError(f"cannot reconstruct M13b: only {len(eligible)} eligible")
    selected = eligible[:100]
    manifest = [
        {
            "organisation_number": org,
            "evaluation_split": "v9_m13b_consumed_search_replacement",
            "sample_slice": "m13b_search_holdout" if i < 20 else "m13b_control_unsearched",
        }
        for i, org in enumerate(selected)
    ]
    digest = hashlib.sha256(jsonl_bytes(manifest)).hexdigest()
    if digest != M13B_TARGET_MANIFEST_SHA256:
        raise ValueError(
            f"M13b reconstruction mismatch: {digest} != {M13B_TARGET_MANIFEST_SHA256}"
        )
    return set(selected), digest


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-manifest", type=Path, required=True)
    p.add_argument("--bulk", type=Path, required=True)
    p.add_argument("--m13b-base-exclude", action="append", type=Path, default=[])
    p.add_argument("--exclude", action="append", type=Path, default=[])
    p.add_argument("--gate-a-output", type=Path, required=True)
    p.add_argument("--gate-b-output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--count-per-gate", type=int, default=100)
    args = p.parse_args()

    source = read_organisation_inputs(args.source_manifest)
    source_orgs = [str(row["organisation_number"]) for row in source]
    if len(source_orgs) != 1000 or len(set(source_orgs)) != 1000:
        raise ValueError("M19 transfer requires exact frozen consumed 1000")

    profiles, snapshot = profiles_from_bulk(args.bulk, source_orgs)

    base_excluded = set(KNOWN_RESEARCHED_ORGS)
    exclusion_manifest_rows: list[dict[str, Any]] = []
    for path in args.m13b_base_exclude:
        values = read_orgs(path)
        base_excluded |= values
        exclusion_manifest_rows.append({
            "role": "m13b_base_exclude",
            "file": path.name,
            "companies": len(values),
            "sha256": sha256(path),
        })

    m13b, m13b_sha = reconstruct_m13b(profiles, base_excluded=base_excluded)
    excluded = base_excluded | m13b

    for path in args.exclude:
        values = read_orgs(path)
        excluded |= values
        exclusion_manifest_rows.append({
            "role": "exclude",
            "file": path.name,
            "companies": len(values),
            "sha256": sha256(path),
        })

    remaining = [org for org in source_orgs if org not in excluded]
    remaining.sort()
    needed = args.count_per_gate * 2
    if len(remaining) < needed:
        raise ValueError(f"only {len(remaining)} unexcluded companies remain; need {needed}")

    gate_a_orgs = remaining[: args.count_per_gate]
    gate_b_orgs = remaining[args.count_per_gate : needed]
    if set(gate_a_orgs) & set(gate_b_orgs):
        raise AssertionError("Gate A/B overlap")

    gate_a = [
        {
            "organisation_number": org,
            "evaluation_split": "v10_m19_consumed_transfer",
            "sample_slice": "m19_transfer_gate_a",
        }
        for org in gate_a_orgs
    ]
    gate_b = [
        {
            "organisation_number": org,
            "evaluation_split": "v10_m19_consumed_transfer",
            "sample_slice": "m19_transfer_gate_b",
        }
        for org in gate_b_orgs
    ]
    write_jsonl(args.gate_a_output, gate_a)
    write_jsonl(args.gate_b_output, gate_b)

    report = {
        "screen_type": "v10_m19_consumed_disjoint_transfer_freeze",
        "source_population_companies": 1000,
        "excluded_companies": len(excluded),
        "remaining_uninspected_companies": len(remaining),
        "gate_a_companies": len(gate_a),
        "gate_b_companies": len(gate_b),
        "gate_a_gate_b_disjoint": True,
        "fresh_companies_used": 0,
        "m13b_reconstructed_companies_excluded": len(m13b),
        "m13b_reconstructed_manifest_sha256": m13b_sha,
        "source_manifest_sha256": sha256(args.source_manifest),
        "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
        "gate_a_manifest_sha256": sha256(args.gate_a_output),
        "gate_b_manifest_sha256": sha256(args.gate_b_output),
        "exclusion_manifests": exclusion_manifest_rows,
        "selection_rule": [
            "start from the exact frozen already-consumed 1000-company population",
            "exclude known researched/public-practice cases",
            "reconstruct and exclude the entire frozen M13b cohort",
            "exclude Q8 development, M10, PR137, M13, M14, M14b, M15, M16 and M17 cohorts",
            "sort remaining organisation numbers ascending",
            f"freeze first {args.count_per_gate} as M19 transfer Gate A",
            f"freeze next {args.count_per_gate} as M19 transfer Gate B",
            "both gates are frozen before any retained webpage/profile output is observed",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "gate_a_companies": report["gate_a_companies"],
        "gate_b_companies": report["gate_b_companies"],
        "remaining_uninspected_companies": report["remaining_uninspected_companies"],
        "gate_a_manifest_sha256": report["gate_a_manifest_sha256"],
        "gate_b_manifest_sha256": report["gate_b_manifest_sha256"],
        "fresh_companies_used": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
