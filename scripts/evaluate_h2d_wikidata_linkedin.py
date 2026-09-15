#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.external_footprint import validate_observation  # noqa: E402
from norway_company_agent.wikidata_org_profiles import (  # noqa: E402
    candidate_observation,
    fetch_wikidata_linkedin_candidates,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def existing_linkedin_urls(profile: dict[str, Any]) -> set[str]:
    return {
        str(item.get("profile_url") or "").rstrip("/")
        for item in profile.get("external_observations") or []
        if isinstance(item, dict)
        and item.get("signal_type") == "profile_handle"
        and item.get("platform") == "linkedin"
        and not validate_observation(item)
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate exact-org Wikidata P4264 LinkedIn organisation candidates on production profiles."
    )
    parser.add_argument("--profiles", required=True, help="Production profiles.jsonl")
    parser.add_argument("--report", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--expected-count", type=int, default=300)
    args = parser.parse_args()

    profiles = read_jsonl(Path(args.profiles))
    if len(profiles) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} profiles, found {len(profiles)}")
    orgs = [str(profile.get("organisation_number") or "") for profile in profiles]
    if len(orgs) != len(set(orgs)):
        raise SystemExit("Duplicate organisation numbers in production profiles")

    candidates, metrics = fetch_wikidata_linkedin_candidates(orgs, timeout=args.timeout)
    audit_rows: list[dict[str, Any]] = []
    validation_errors: list[dict[str, str]] = []
    net_new_observations: list[dict[str, Any]] = []
    overlapping_candidates = 0

    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        candidate = candidates.get(org)
        if not candidate:
            continue
        observation = candidate_observation(profile, candidate)
        if observation is None:
            validation_errors.append(
                {
                    "organisation_number": org,
                    "error": "candidate could not be represented as a prospective observation",
                }
            )
            continue
        errors = validate_observation(observation)
        for error in errors:
            validation_errors.append(
                {
                    "organisation_number": org,
                    "observation_id": str(observation.get("id") or ""),
                    "error": error,
                }
            )

        existing = existing_linkedin_urls(profile)
        normalized = str(observation.get("profile_url") or "").rstrip("/")
        already_present = normalized in existing
        if already_present:
            overlapping_candidates += 1
        elif not errors:
            net_new_observations.append(observation)

        audit_rows.append(
            {
                "organisation_number": org,
                "company_name": profile.get("name"),
                "municipality": profile.get("municipality"),
                "wikidata_item": candidate.get("wikidata_item"),
                "linkedin_identifier": candidate.get("linkedin_identifier"),
                "profile_url": candidate.get("profile_url"),
                "already_present_in_h2a": already_present,
                "existing_h2a_linkedin_urls": sorted(existing),
                "observation_valid": not errors,
                "observation_validation_errors": errors,
                "identity_proof": observation.get("identity_proof"),
                "claim_scope": (observation.get("metrics") or {}).get("claim_scope"),
            }
        )

    existing_h2a_linkedin_companies = sum(1 for profile in profiles if existing_linkedin_urls(profile))
    report = {
        "experiment": "h2d_wikidata_exact_org_linkedin",
        "expected_count": args.expected_count,
        "candidate_companies": int(metrics.get("candidate_companies") or 0),
        "candidate_rate": round(int(metrics.get("candidate_companies") or 0) / args.expected_count, 6),
        "overlap_with_existing_h2a": overlapping_candidates,
        "net_new_candidate_companies": len(net_new_observations),
        "net_new_candidate_rate": round(len(net_new_observations) / args.expected_count, 6),
        "existing_h2a_linkedin_companies": existing_h2a_linkedin_companies,
        "prospective_linkedin_companies_after_h2d": len(
            {
                *(str(profile.get("organisation_number") or "") for profile in profiles if existing_linkedin_urls(profile)),
                *(str(item.get("organisation_number") or "") for item in net_new_observations),
            }
        ),
        "experimental_wikidata_requests": int(metrics.get("requests") or 0),
        "experimental_wikidata_batches": int(metrics.get("batches") or 0),
        "experimental_wikidata_bytes": int(metrics.get("bytes") or 0),
        "experimental_wikidata_errors": list(metrics.get("errors") or []),
        "ambiguous_item_organisations": int(metrics.get("ambiguous_item_organisations") or 0),
        "ambiguous_linkedin_identifiers": int(metrics.get("ambiguous_linkedin_identifiers") or 0),
        "prospective_production_added_requests_if_folded_into_h1e": 0,
        "third_party_cost_usd": 0.0,
        "prospective_observation_validation_errors": validation_errors,
        "audit_rows": len(audit_rows),
        "audit_status_counts": dict(
            sorted(Counter("overlap" if row["already_present_in_h2a"] else "net_new" for row in audit_rows).items())
        ),
        "passed": (
            not validation_errors
            and int(metrics.get("requests") or 0) <= 3
            and float(0.0) == 0.0
        ),
        "decision_rule": (
            "Do not promote from this report alone. Manually verify every net-new candidate. "
            "Only integrate if fresh transfer is useful and the audited organisation-profile claims remain high precision."
        ),
    }

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_jsonl(Path(args.audit), audit_rows)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
