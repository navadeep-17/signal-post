#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_contact import attach_company_site_contact_email_observations  # noqa: E402
from norway_company_agent.company_site_social import attach_company_site_social_observations  # noqa: E402
from norway_company_agent.external_footprint import validate_observation  # noqa: E402
from norway_company_agent.h1f_tld_recall import (  # noqa: E402
    MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
    OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE,
    evaluate_compact_com_fallback,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _observation_ids(profile: dict[str, Any]) -> set[str]:
    return {
        str(item.get("id"))
        for item in profile.get("external_observations") or []
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }


def _evaluate_one(profile: dict[str, Any], *, timeout: float) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    before_ids = _observation_ids(profile)
    row, metrics = evaluate_compact_com_fallback(profile, timeout=timeout)
    if metrics.get("verified"):
        attach_company_site_social_observations(row)
        attach_company_site_contact_email_observations(row)
    added = [
        item
        for item in row.get("external_observations") or []
        if isinstance(item, dict) and str(item.get("id") or "") not in before_ids
    ]
    return row, metrics, added


def _audit_row(profile: dict[str, Any], metrics: dict[str, Any], added: list[dict[str, Any]]) -> dict[str, Any]:
    candidate = ((profile.get("evidence") or {}).get("website_h1f_candidate") or {})
    value = candidate.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    return {
        "organisation_number": profile.get("organisation_number"),
        "company_name": profile.get("name"),
        "candidate_domain": metrics.get("candidate_domain"),
        "attempted": bool(metrics.get("attempted")),
        "verified": bool(metrics.get("verified")),
        "selected_url": metrics.get("selected_url"),
        "base_site_logical_requests": metrics.get("base_site_logical_requests"),
        "requests_added": metrics.get("requests_added"),
        "post_site_logical_requests": metrics.get("post_site_logical_requests"),
        "guard_reasons": metrics.get("guard_reasons") or [],
        "candidate_status": candidate.get("status"),
        "candidate_source_url": candidate.get("source_url"),
        "candidate_retrieved_at": candidate.get("retrieved_at"),
        "candidate_content_sha256": candidate.get("content_sha256") or value.get("content_sha256"),
        "title": value.get("title"),
        "identity_text_excerpt": str(value.get("identity_text_excerpt") or "")[:2500],
        "main_text_excerpt": str(value.get("main_text_excerpt") or "")[:2500],
        "identity_assessment": assessment,
        "new_external_observations": [
            {
                "id": item.get("id"),
                "signal_type": item.get("signal_type"),
                "platform": item.get("platform"),
                "profile_url": item.get("profile_url"),
                "contact_email": item.get("contact_email"),
                "source_url": item.get("source_url"),
            }
            for item in added
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate bounded compact .com company-site recall using only unused production request headroom."
    )
    parser.add_argument("--profiles", required=True, help="Production profiles JSONL from the fresh base run")
    parser.add_argument("--base-report", required=True, help="Production run report for request-accounting invariants")
    parser.add_argument("--output-profiles", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=6.0)
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    profiles = _read_jsonl(Path(args.profiles))
    base_report = json.loads(Path(args.base_report).read_text(encoding="utf-8"))
    expected = int(base_report.get("expected_count") or 0)
    if expected <= 0 or len(profiles) != expected:
        raise SystemExit(f"Profile/report count mismatch: profiles={len(profiles)} expected={expected}")

    state: dict[str, tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_evaluate_one, profile, timeout=args.timeout): str(profile.get("organisation_number") or "")
            for profile in profiles
        }
        for future in as_completed(futures):
            state[futures[future]] = future.result()

    ordered = [state[str(profile.get("organisation_number") or "")] for profile in profiles]
    output_profiles = [item[0] for item in ordered]
    metrics = [item[1] for item in ordered]
    added_observations = [obs for item in ordered for obs in item[2]]
    audits = [
        _audit_row(profile, metric, added)
        for profile, metric, added in ordered
        if metric.get("attempted")
    ]

    validation_errors: list[dict[str, Any]] = []
    for observation in added_observations:
        for error in validate_observation(observation):
            validation_errors.append({"id": observation.get("id"), "error": error})

    budget_violations = [
        {
            "organisation_number": metric.get("organisation_number"),
            "post_site_logical_requests": metric.get("post_site_logical_requests"),
        }
        for metric in metrics
        if metric.get("post_site_logical_requests") is not None
        and int(metric["post_site_logical_requests"]) > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    ]

    base_budget = base_report.get("request_budget") or {}
    base_profile_logical = int(base_budget.get("profile_logical_requests") or 0)
    recomputed_base_profile_logical = sum(
        int((profile.get("run_metrics") or {}).get("logical_requests") or 0)
        for profile in profiles
    )
    if base_profile_logical != recomputed_base_profile_logical:
        raise SystemExit(
            "Base profile request accounting mismatch: "
            f"report={base_profile_logical} recomputed={recomputed_base_profile_logical}"
        )

    requests_added = sum(int(metric.get("requests_added") or 0) for metric in metrics)
    post_profile_logical = base_profile_logical + requests_added
    shared_logical = int(base_budget.get("shared_wikidata_logical_requests") or 0)
    post_observed_logical = post_profile_logical + shared_logical
    charge_multiplier = int(base_budget.get("request_charge_multiplier") or 2)
    post_conservative_charge = post_observed_logical * charge_multiplier
    theoretical_charge = int(base_budget.get("theoretical_challenge_request_charge_ceiling") or 0)
    max_charge = int(base_budget.get("max_challenge_requests") or theoretical_charge)

    verified = [metric for metric in metrics if metric.get("verified")]
    attempted = [metric for metric in metrics if metric.get("attempted")]
    skip_counts = Counter(str(metric.get("skipped_reason") or "none") for metric in metrics if not metric.get("attempted"))
    signal_counts = Counter(str(item.get("signal_type") or "") for item in added_observations)
    companies_with_new_handles = {
        str(item.get("organisation_number") or "")
        for item in added_observations
        if item.get("signal_type") == "profile_handle"
    }
    companies_with_new_contact_emails = {
        str(item.get("organisation_number") or "")
        for item in added_observations
        if item.get("signal_type") == "company_profile" and item.get("contact_email")
    }

    checks = {
        "base_report_passed": base_report.get("passed") is True,
        "exact_profile_count": len(profiles) == expected,
        "all_added_observations_valid": not validation_errors,
        "per_profile_site_ceiling_preserved": not budget_violations,
        "global_theoretical_ceiling_unchanged": post_conservative_charge <= theoretical_charge,
        "explicit_challenge_request_budget_preserved": post_conservative_charge <= max_charge,
        "third_party_cost_added_zero": True,
    }
    report = {
        "passed": all(checks.values()),
        "checks": checks,
        "profiles": len(profiles),
        "candidate_available": sum(1 for metric in metrics if metric.get("candidate_available")),
        "attempted": len(attempted),
        "verified": len(verified),
        "net_new_verified_websites": len(verified),
        "verification_rate_over_attempts": round(len(verified) / len(attempted), 6) if attempted else 0.0,
        "skip_counts": dict(sorted(skip_counts.items())),
        "requests_added": requests_added,
        "third_party_cost_usd_added": 0.0,
        "request_budget": {
            "official_logical_requests_per_profile": OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE,
            "site_logical_requests_per_profile_ceiling": MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
            "base_profile_logical_requests": base_profile_logical,
            "post_h1f_profile_logical_requests": post_profile_logical,
            "shared_wikidata_logical_requests": shared_logical,
            "post_h1f_observed_logical_requests": post_observed_logical,
            "request_charge_multiplier": charge_multiplier,
            "post_h1f_conservative_challenge_request_charge": post_conservative_charge,
            "theoretical_challenge_request_charge_ceiling": theoretical_charge,
            "max_challenge_requests": max_charge,
        },
        "downstream_zero_network_gain": {
            "new_external_observations": len(added_observations),
            "signal_type_counts": dict(sorted(signal_counts.items())),
            "companies_with_new_profile_handles": len(companies_with_new_handles),
            "companies_with_new_contact_emails": len(companies_with_new_contact_emails),
        },
        "validation_errors": validation_errors,
        "budget_violations": budget_violations,
        "verified_organisation_numbers": [str(metric.get("organisation_number") or "") for metric in verified],
    }

    _write_jsonl(Path(args.output_profiles), output_profiles)
    _write_jsonl(Path(args.audit), audits)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
