#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from norway_company_agent.batch import read_organisation_inputs


EXPECTED_CONSUMED_SOURCE_SHA256 = "80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26"
EXPECTED_EXCLUSION_UNION_SHA256 = "5a1ac106dde4033d68a2751b6d0e15cf3b267c54286c27e45856cea8d5c966b7"
EXPECTED_EXCLUSION_UNION_COMPANIES = 428


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    ).encode("utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(jsonl_bytes(rows))


def read_exclusion_union(
    encoded_path: Path,
    report_path: Path,
    *,
    source_orgs: set[str],
) -> tuple[set[str], dict[str, Any]]:
    encoded = encoded_path.read_text(encoding="utf-8").strip()
    try:
        raw = gzip.decompress(base64.b64decode(encoded, validate=True))
    except Exception as exc:
        raise ValueError(f"cannot decode frozen exclusion union: {type(exc).__name__}: {exc}") from exc

    digest = sha256_bytes(raw)
    if digest != EXPECTED_EXCLUSION_UNION_SHA256:
        raise ValueError(
            f"exclusion union SHA mismatch: {digest} != {EXPECTED_EXCLUSION_UNION_SHA256}"
        )

    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"exclusion union line {lineno}: expected object")
        org = str(item.get("organisation_number") or "")
        reasons = item.get("excluded_by")
        if len(org) != 9 or not org.isdigit():
            raise ValueError(f"exclusion union line {lineno}: invalid organisation number")
        if not isinstance(reasons, list) or not reasons or not all(str(x).strip() for x in reasons):
            raise ValueError(f"exclusion union line {lineno}: missing excluded_by provenance")
        rows.append(item)

    excluded = {str(row["organisation_number"]) for row in rows}
    if len(rows) != len(excluded):
        raise ValueError("exclusion union contains duplicate organisation numbers")
    if len(excluded) != EXPECTED_EXCLUSION_UNION_COMPANIES:
        raise ValueError(
            f"exclusion union company count mismatch: {len(excluded)} != {EXPECTED_EXCLUSION_UNION_COMPANIES}"
        )
    outside = excluded - source_orgs
    if outside:
        raise ValueError(f"exclusion union contains organisations outside consumed source: {sorted(outside)[:5]}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("schema_version") != "v10_m19_prior_exclusion_union_v1":
        raise ValueError("unexpected exclusion provenance schema")
    if report.get("union_manifest_sha256") != digest:
        raise ValueError("exclusion provenance report manifest SHA mismatch")
    if int(report.get("union_companies") or 0) != len(excluded):
        raise ValueError("exclusion provenance report company count mismatch")
    if report.get("all_union_rows_are_in_consumed_source") is not True:
        raise ValueError("exclusion provenance report did not certify consumed-source membership")
    if report.get("consumed_source_manifest_sha256") != EXPECTED_CONSUMED_SOURCE_SHA256:
        raise ValueError("exclusion provenance report source SHA mismatch")
    return excluded, report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-manifest", type=Path, required=True)
    p.add_argument("--prior-exclusion-union-b64", type=Path, required=True)
    p.add_argument("--prior-exclusion-report", type=Path, required=True)
    p.add_argument("--gate-a-output", type=Path, required=True)
    p.add_argument("--gate-b-output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--count-per-gate", type=int, default=100)
    args = p.parse_args()

    if sha256(args.source_manifest) != EXPECTED_CONSUMED_SOURCE_SHA256:
        raise ValueError("M19 transfer source is not the exact frozen consumed 1000")

    source = read_organisation_inputs(args.source_manifest)
    source_orgs_ordered = [str(row["organisation_number"]) for row in source]
    source_orgs = set(source_orgs_ordered)
    if len(source_orgs_ordered) != 1000 or len(source_orgs) != 1000:
        raise ValueError("M19 transfer requires exactly 1000 unique consumed organisations")

    excluded, provenance = read_exclusion_union(
        args.prior_exclusion_union_b64,
        args.prior_exclusion_report,
        source_orgs=source_orgs,
    )

    remaining = sorted(source_orgs - excluded)
    if len(remaining) != 572:
        raise ValueError(f"unexpected remaining consumed population: {len(remaining)} != 572")

    needed = args.count_per_gate * 2
    if args.count_per_gate < 1 or len(remaining) < needed:
        raise ValueError(
            f"invalid requested transfer size: remaining={len(remaining)}, needed={needed}"
        )

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
        "screen_type": "v10_m19_consumed_disjoint_transfer_freeze_v2",
        "source_population_companies": 1000,
        "source_manifest_sha256": sha256(args.source_manifest),
        "prior_exclusion_union_companies": len(excluded),
        "prior_exclusion_union_sha256": EXPECTED_EXCLUSION_UNION_SHA256,
        "prior_exclusion_provenance_schema": provenance.get("schema_version"),
        "remaining_uninspected_companies": len(remaining),
        "gate_a_companies": len(gate_a),
        "gate_b_companies": len(gate_b),
        "gate_a_gate_b_disjoint": True,
        "fresh_companies_used": 0,
        "gate_a_manifest_sha256": sha256(args.gate_a_output),
        "gate_b_manifest_sha256": sha256(args.gate_b_output),
        "selection_rule": [
            "start from exact frozen already-consumed 1000-company population",
            "subtract immutable source-relative prior-experiment exclusion union (428 organisations)",
            "sort remaining organisation numbers ascending",
            f"freeze first {args.count_per_gate} as M19 transfer Gate A",
            f"freeze next {args.count_per_gate} as M19 transfer Gate B",
            "freeze both manifests before any retained webpage/profile output is observed",
            "Gate B remains sealed until Gate A machine + complete manual evidence review pass",
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
