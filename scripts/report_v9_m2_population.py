#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs  # noqa: E402
from norway_company_agent.v9_m2_targeting import classify_m2_candidate_slot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate-only census of V9 M2 causal exposure on the frozen consumed 1000."
    )
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--bulk", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source_inputs = read_organisation_inputs(args.source_manifest)
    source_orgs = [row["organisation_number"] for row in source_inputs]
    if len(source_orgs) != 1000:
        raise ValueError(f"expected consumed source manifest of 1000 companies, got {len(source_orgs)}")

    profiles, snapshot = profiles_from_bulk(args.bulk, source_orgs)
    buckets: Counter[str] = Counter()
    baseline_strengths: Counter[str] = Counter()
    challenger_strengths: Counter[str] = Counter()
    registry_website_present = 0

    for profile in profiles:
        if str(profile.get("website") or "").strip():
            registry_website_present += 1
            continue
        row = classify_m2_candidate_slot(profile)
        buckets[str(row.get("bucket") or "unknown")] += 1
        if row.get("baseline_candidate_domain"):
            baseline_strengths[str(row.get("baseline_candidate_strength") or "none")] += 1
        if row.get("challenger_candidate_domain"):
            challenger_strengths[str(row.get("challenger_candidate_strength") or "none")] += 1

    report = {
        "screen_type": "v9_m2_consumed_1000_causal_exposure_census",
        "source_companies": len(source_orgs),
        "registry_website_present_companies": registry_website_present,
        "eligible_without_registry_website": sum(buckets.values()),
        "bucket_counts": dict(sorted(buckets.items())),
        "m2_behaviorally_affected_companies": int(buckets.get("m2_delta") or 0),
        "strong_email_control_companies": int(buckets.get("strong_email_control") or 0),
        "no_email_control_companies": int(buckets.get("no_email_control") or 0),
        "baseline_candidate_strength_counts": dict(sorted(baseline_strengths.items())),
        "challenger_candidate_strength_counts": dict(sorted(challenger_strengths.items())),
        "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
        "registry_snapshot_missing_count": snapshot.get("missing_count"),
        "fresh_companies_used": 0,
        "candidate_values_retained": False,
        "organisation_lists_retained": False,
        "notes": [
            "The source population is the frozen consumed final-release 1000 manifest, not a fresh cohort.",
            "m2_delta means the V8 and V9 first email-domain candidate slot differs.",
            "strong_email_control means both versions nominate the same strong email-domain candidate.",
            "no_email_control means neither version uses an email-domain candidate.",
            "Only aggregate counts are retained by this census.",
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
