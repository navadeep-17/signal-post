#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.annual_report_domain_discovery import probe_annual_report_candidates  # noqa: E402
from norway_company_agent.company_site_contact import attach_company_site_contact_email_observations  # noqa: E402
from norway_company_agent.company_site_social import attach_company_site_social_observations  # noqa: E402


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def verified_orgs(profiles: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for profile in profiles:
        website = ((profile.get("evidence") or {}).get("website") or {})
        identity = ((website.get("value") or {}).get("identity_assessment") or {})
        if website.get("status") == "available" and identity.get("publishable"):
            out.add(str(profile.get("organisation_number") or ""))
    return out


def observation_orgs(profiles: list[dict[str, Any]], *, kind: str) -> set[str]:
    out: set[str] = set()
    for profile in profiles:
        for observation in profile.get("external_observations") or []:
            if not isinstance(observation, dict):
                continue
            if kind == "contact" and observation.get("signal_type") == "company_profile" and observation.get("contact_email"):
                out.add(str(profile.get("organisation_number") or ""))
            elif kind == "social" and observation.get("signal_type") == "profile_handle":
                out.add(str(profile.get("organisation_number") or ""))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe annual-report-nominated website domains under strict independent identity gates.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output-profiles", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--attempts", required=True)
    parser.add_argument("--max-logical-requests", type=int, required=True)
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--max-candidates-per-company", type=int, default=1)
    args = parser.parse_args()
    if args.max_logical_requests < 0:
        parser.error("--max-logical-requests cannot be negative")
    if args.max_candidates_per_company < 1:
        parser.error("--max-candidates-per-company must be positive")

    profiles = read_jsonl(Path(args.profiles))
    before_sites = verified_orgs(profiles)
    before_contacts = observation_orgs(profiles, kind="contact")
    before_socials = observation_orgs(profiles, kind="social")
    candidate_orgs = {
        str(profile.get("organisation_number") or "")
        for profile in profiles
        if profile.get("annual_report_website_candidates")
    }

    result = probe_annual_report_candidates(
        profiles,
        max_logical_requests=args.max_logical_requests,
        timeout=args.timeout,
        max_candidates_per_company=args.max_candidates_per_company,
        request_charge_multiplier=2,
    )

    # Existing zero-network downstream extractors run only after a site has independently
    # passed the exact-company publication gate.
    after_probe_sites = verified_orgs(profiles)
    new_site_orgs = after_probe_sites - before_sites
    for profile in profiles:
        if str(profile.get("organisation_number") or "") in new_site_orgs:
            attach_company_site_social_observations(profile)
            attach_company_site_contact_email_observations(profile)

    after_contacts = observation_orgs(profiles, kind="contact")
    after_socials = observation_orgs(profiles, kind="social")
    write_jsonl(Path(args.output_profiles), profiles)
    write_jsonl(Path(args.attempts), list(result.get("attempt_audit") or []))

    report = {
        "experiment": "V6e annual-report domain discovery",
        "input_profiles": len(profiles),
        "companies_with_annual_report_candidates": len(candidate_orgs),
        "verified_websites_before": len(before_sites),
        "verified_websites_after": len(after_probe_sites),
        "net_new_verified_websites": len(new_site_orgs),
        "net_new_verified_website_orgs": sorted(new_site_orgs),
        "contact_companies_before": len(before_contacts),
        "contact_companies_after": len(after_contacts),
        "net_new_contact_companies": len(after_contacts - before_contacts),
        "social_companies_before": len(before_socials),
        "social_companies_after": len(after_socials),
        "net_new_social_companies": len(after_socials - before_socials),
        "logical_requests_added": int(result.get("logical_requests") or 0),
        "conservative_request_charge_added": int(result.get("conservative_request_charge") or 0),
        "attempts": int(result.get("attempts") or 0),
        "verified_by_challenger": int(result.get("verified") or 0),
        "bytes_added": int(result.get("bytes") or 0),
        "runtime_seconds": float(result.get("runtime_seconds") or 0.0),
        "third_party_api_cost_usd": 0.0,
        "candidate_is_evidence": False,
        "publication_gate": "independently fetched page must show exact org number OR exact multi-token legal name plus BRREG location; conflicting org number rejects",
        "manual_audit_required": True,
        "optimization_metric": "net-new correct verified websites per conservative request charge",
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
