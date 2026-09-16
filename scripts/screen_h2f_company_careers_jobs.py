#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_careers_jobs import (  # noqa: E402
    discover_career_links,
    extract_structured_job_observations,
    fallback_role_candidates,
    fetch_html,
)
from norway_company_agent.external_footprint import validate_observation  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _verified_site(profile: dict) -> str | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not assessment.get("publishable"):
        return None
    url = str(value.get("final_url") or website.get("source_url") or "").strip()
    return url or None


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen verified company sites for same-domain structured job postings.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--observations", required=True)
    parser.add_argument("--expected-count", type=int, default=300)
    parser.add_argument("--timeout", type=float, default=6.0)
    args = parser.parse_args()

    profiles = read_jsonl(Path(args.profiles))
    if len(profiles) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} profiles, got {len(profiles)}")

    # At most 49 two-request careers follow-ups per 100 companies keeps the conservative
    # x2 challenge ceiling at 1,998/100: 1,802 + (49 * 2 * 2) = 1,998.
    production_followup_cap = (args.expected_count * 49) // 100

    verified_sites = 0
    homepage_attempts = 0
    homepage_available = 0
    sites_with_career_link = 0
    career_pages_attempted = 0
    career_pages_available = 0
    screen_requests = 0
    screen_bytes = 0
    observations: list[dict] = []
    validation_errors: list[dict] = []
    audit: list[dict] = []
    homepage_statuses: Counter[str] = Counter()
    career_statuses: Counter[str] = Counter()
    fallback_candidate_companies = 0
    companies_with_existing_workforce: set[str] = set()
    companies_with_jobs: set[str] = set()

    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        existing_workforce = any(
            isinstance(item, dict) and item.get("signal_type") == "workforce_snapshot"
            for item in (profile.get("external_observations") or [])
        )
        if existing_workforce:
            companies_with_existing_workforce.add(org)

        site_url = _verified_site(profile)
        if not site_url:
            continue
        verified_sites += 1
        homepage_attempts += 1
        homepage, home_metrics = fetch_html(site_url, timeout=args.timeout, max_bytes=750_000)
        screen_requests += int(home_metrics.get("requests") or 0)
        screen_bytes += int(home_metrics.get("bytes") or 0)
        homepage_statuses[str(home_metrics.get("status") or "unknown")] += 1
        row = {
            "organisation_number": org,
            "name": profile.get("name"),
            "verified_site": site_url,
            "homepage_status": home_metrics.get("status"),
            "career_links": [],
            "career_page_status": None,
            "structured_jobs": [],
            "structured_rejections": [],
            "fallback_role_candidates": [],
            "existing_workforce_snapshot": existing_workforce,
        }
        if homepage is None:
            audit.append(row)
            continue
        homepage_available += 1
        career_links = discover_career_links(homepage["url"], homepage["html"])
        row["career_links"] = career_links
        if not career_links:
            audit.append(row)
            continue
        sites_with_career_link += 1

        # Screen the exact production policy: only the strongest careers link and only while
        # the deterministic global follow-up cap has headroom.
        if career_pages_attempted >= production_followup_cap:
            row["career_page_status"] = "production_followup_cap_reached"
            audit.append(row)
            continue
        career_url = career_links[0]
        career_pages_attempted += 1
        career_page, career_metrics = fetch_html(career_url, timeout=args.timeout, max_bytes=1_000_000)
        screen_requests += int(career_metrics.get("requests") or 0)
        screen_bytes += int(career_metrics.get("bytes") or 0)
        status = str(career_metrics.get("status") or "unknown")
        career_statuses[status] += 1
        row["career_page_status"] = status
        row["career_page_url"] = career_url
        if career_page is None:
            audit.append(row)
            continue
        career_pages_available += 1
        extracted, rejected = extract_structured_job_observations(profile, career_page)
        fallback = fallback_role_candidates(career_page["html"], career_page["url"])
        row["structured_jobs"] = [
            {
                "id": item.get("id"),
                "title": (item.get("metrics") or {}).get("job_title"),
                "date_posted": (item.get("metrics") or {}).get("date_posted"),
                "valid_through": (item.get("metrics") or {}).get("valid_through"),
                "location": (item.get("metrics") or {}).get("location"),
                "source_url": item.get("source_url"),
                "evidence_span": item.get("evidence_span"),
            }
            for item in extracted
        ]
        row["structured_rejections"] = rejected
        row["fallback_role_candidates"] = fallback
        if fallback:
            fallback_candidate_companies += 1
        for item in extracted:
            errors = validate_observation(item)
            if errors:
                validation_errors.append({"organisation_number": org, "observation_id": item.get("id"), "errors": errors})
                continue
            observations.append(item)
            companies_with_jobs.add(org)
        audit.append(row)

    overlap = companies_with_jobs & companies_with_existing_workforce
    net_new_workforce_jobs = companies_with_jobs - companies_with_existing_workforce
    prospective_added_logical_requests = career_pages_attempted * 2
    prospective_added_conservative_charge = prospective_added_logical_requests * 2
    structural_ceiling_300 = 5406 + production_followup_cap * 2 * 2
    challenge_cap_300 = args.expected_count * 20

    report = {
        "experiment": "h2f_company_owned_structured_jobs_v1",
        "profiles": len(profiles),
        "verified_sites": verified_sites,
        "homepage_attempts": homepage_attempts,
        "homepage_available": homepage_available,
        "sites_with_career_link": sites_with_career_link,
        "career_link_rate_over_verified_sites": round(sites_with_career_link / verified_sites, 6) if verified_sites else 0.0,
        "career_pages_attempted": career_pages_attempted,
        "career_pages_available": career_pages_available,
        "companies_with_structured_jobs": len(companies_with_jobs),
        "job_company_coverage": round(len(companies_with_jobs) / len(profiles), 6) if profiles else 0.0,
        "structured_job_observations": len(observations),
        "companies_with_existing_workforce": len(companies_with_existing_workforce),
        "jobs_overlap_existing_workforce": len(overlap),
        "net_new_workforce_jobs_companies": len(net_new_workforce_jobs),
        "net_new_workforce_jobs_coverage": round(len(net_new_workforce_jobs) / len(profiles), 6) if profiles else 0.0,
        "fallback_role_candidate_companies": fallback_candidate_companies,
        "homepage_status_counts": dict(homepage_statuses),
        "career_status_counts": dict(career_statuses),
        "screen_logical_requests": screen_requests,
        "screen_bytes": screen_bytes,
        "prospective_production_followup_cap": production_followup_cap,
        "prospective_production_added_logical_requests_on_this_cohort": prospective_added_logical_requests,
        "prospective_production_added_conservative_charge_on_this_cohort": prospective_added_conservative_charge,
        "prospective_structural_challenge_charge_ceiling": structural_ceiling_300,
        "challenge_charge_cap": challenge_cap_300,
        "third_party_cost_usd": 0.0,
        "observation_validation_errors": validation_errors,
        "claim_boundary": (
            "Only concrete, non-expired schema.org JobPosting records from a same-registered-domain careers page "
            "of an already verified company website. Generic careers text and diagnostic fallback links are not published."
        ),
        "passed": structural_ceiling_300 <= challenge_cap_300 and not validation_errors,
    }

    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.audit).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in audit), encoding="utf-8")
    Path(args.observations).write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in observations),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
