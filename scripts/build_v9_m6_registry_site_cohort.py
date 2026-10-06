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
        description=(
            "Build a deterministic consumed cohort enriched for M6 exposure by selecting "
            "companies whose current BRREG row already contains an official website."
        )
    )
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--bulk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--target-count", type=int, default=100)
    args = parser.parse_args()

    source_inputs = read_organisation_inputs(args.source_manifest)
    source_orgs = [row["organisation_number"] for row in source_inputs]
    if len(source_orgs) != 1000:
        raise ValueError(
            f"expected frozen consumed source manifest of 1000 companies, got {len(source_orgs)}"
        )

    profiles, snapshot = profiles_from_bulk(args.bulk, source_orgs)
    profile_by_org = {
        str(profile.get("organisation_number") or ""): profile
        for profile in profiles
    }
    eligible = [
        org
        for org in source_orgs
        if str((profile_by_org.get(org) or {}).get("website") or "").strip()
    ]
    if len(eligible) < args.target_count:
        raise ValueError(
            f"only {len(eligible)} consumed companies currently have a BRREG website; "
            f"cannot build target of {args.target_count}"
        )

    selected = eligible[: args.target_count]
    rows = [
        {
            "organisation_number": org,
            "evaluation_split": "v9_m6_registry_website_consumed",
            "sample_slice": "registry_website_exposed",
        }
        for org in selected
    ]
    _write_jsonl(args.output, rows)

    report = {
        "screen_type": "v9_m6_registry_website_consumed_cohort",
        "source_manifest_companies": len(source_orgs),
        "registry_website_eligible_companies": len(eligible),
        "selected_companies": len(selected),
        "selection_rule": (
            "preserve frozen consumed-manifest order and take the first target_count companies "
            "whose current BRREG bulk row has a non-empty registered website"
        ),
        "outcome_blind_selection": True,
        "fresh_companies_used": 0,
        "source_manifest_sha256": _sha256(args.source_manifest),
        "target_manifest_sha256": _sha256(args.output),
        "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
        "registry_snapshot_missing_count": snapshot.get("missing_count"),
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
