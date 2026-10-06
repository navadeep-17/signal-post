#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs  # noqa: E402
from norway_company_agent.v9_m2_targeting import build_targeted_m2_cohort  # noqa: E402


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic consumed-100 cohort that actually exercises the V9 M2 candidate-slot delta."
    )
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--bulk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--target-count", type=int, default=100)
    args = parser.parse_args()

    source_inputs = read_organisation_inputs(args.source_manifest)
    source_orgs = [row["organisation_number"] for row in source_inputs]
    if len(source_orgs) != 1000:
        raise ValueError(f"expected consumed source manifest of 1000 companies, got {len(source_orgs)}")

    profiles, snapshot = profiles_from_bulk(args.bulk, source_orgs)
    selected_orgs, audit_rows, report = build_targeted_m2_cohort(
        profiles,
        target_count=args.target_count,
    )
    source_set = set(source_orgs)
    if any(org not in source_set for org in selected_orgs):
        raise AssertionError("target cohort contains organisation outside consumed source manifest")

    bucket_by_org = {row["organisation_number"]: row["bucket"] for row in audit_rows}
    output_rows = [
        {
            "organisation_number": org,
            "evaluation_split": "v9_m2_targeted_consumed_retune",
            "sample_slice": bucket_by_org[org],
        }
        for org in selected_orgs
    ]
    _write_jsonl(args.output, output_rows)
    _write_jsonl(args.audit, audit_rows)

    report.update(
        {
            "source_manifest": str(args.source_manifest),
            "source_manifest_companies": len(source_orgs),
            "source_manifest_sha256": _sha256(args.source_manifest),
            "target_manifest_sha256": _sha256(args.output),
            "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
            "registry_snapshot_missing_count": snapshot.get("missing_count"),
        }
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
