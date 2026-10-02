#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_contact import attach_company_site_contact_email_observations  # noqa: E402
from norway_company_agent.company_site_social import attach_company_site_social_observations  # noqa: E402
from norway_company_agent.subunit_site_discovery import (  # noqa: E402
    probe_subunit_site_candidates,
    subunit_site_candidates,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _verified_orgs(profiles: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for profile in profiles:
        website = ((profile.get("evidence") or {}).get("website") or {})
        identity = ((website.get("value") or {}).get("identity_assessment") or {})
        if website.get("status") == "available" and identity.get("publishable"):
            result.add(str(profile.get("organisation_number") or ""))
    return result


def _observation_orgs(profiles: list[dict[str, Any]], kind: str) -> set[str]:
    out: set[str] = set()
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        for observation in profile.get("external_observations") or []:
            if not isinstance(observation, dict):
                continue
            if kind == "contact" and observation.get("signal_type") == "company_profile" and observation.get("contact_email"):
                out.add(org)
            elif kind == "social" and observation.get("signal_type") == "profile_handle":
                out.add(org)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="V6h zero-cost BRREG subunit website/email hint experiment.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output-profiles", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--attempts", required=True)
    parser.add_argument("--candidate-audit", required=True)
    parser.add_argument("--max-logical-requests", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--max-candidates-per-company", type=int, default=1)
    args = parser.parse_args()
    if args.max_logical_requests < 0:
        parser.error("--max-logical-requests cannot be negative")
    if args.max_candidates_per_company < 1:
        parser.error("--max-candidates-per-company must be positive")

    profiles = read_jsonl(Path(args.profiles))
    before_sites = _verified_orgs(profiles)
    before_contacts = _observation_orgs(profiles, "contact")
    before_socials = _observation_orgs(profiles, "social")

    candidate_audit: list[dict[str, Any]] = []
    unresolved_with_candidates: set[str] = set()
    companies_with_explicit_website_hint: set[str] = set()
    companies_with_email_hint: set[str] = set()
    unique_candidate_domains: set[str] = set()
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        candidates = subunit_site_candidates(profile, max_candidates=3)
        if not candidates:
            continue
        if org not in before_sites:
            unresolved_with_candidates.add(org)
        for item in candidates:
            unique_candidate_domains.add(str(item.get("domain") or ""))
            if item.get("strategy") == "brreg_subunit_registered_website":
                companies_with_explicit_website_hint.add(org)
            elif item.get("strategy") == "brreg_subunit_registered_email_domain":
                companies_with_email_hint.add(org)
            candidate_audit.append({
                "organisation_number": org,
                "company_name": profile.get("name"),
                **item,
                "already_verified_before_v6h": org in before_sites,
                "candidate_is_evidence": False,
            })

    result = probe_subunit_site_candidates(
        profiles,
        max_logical_requests=args.max_logical_requests,
        timeout=args.timeout,
        max_candidates_per_company=args.max_candidates_per_company,
        request_charge_multiplier=2,
    )
    after_probe_sites = _verified_orgs(profiles)
    new_site_orgs = after_probe_sites - before_sites

    # Reuse current zero-network downstream projections only after exact parent website proof.
    for profile in profiles:
        if str(profile.get("organisation_number") or "") in new_site_orgs:
            attach_company_site_social_observations(profile)
            attach_company_site_contact_email_observations(profile)

    after_contacts = _observation_orgs(profiles, "contact")
    after_socials = _observation_orgs(profiles, "social")
    write_jsonl(Path(args.output_profiles), profiles)
    write_jsonl(Path(args.attempts), list(result.get("attempt_audit") or []))
    write_jsonl(Path(args.candidate_audit), candidate_audit)

    report = {
        "experiment": "V6h BRREG subunit website candidates",
        "input_profiles": len(profiles),
        "verified_websites_before": len(before_sites),
        "companies_with_any_subunit_domain_hint": len({row["organisation_number"] for row in candidate_audit}),
        "unresolved_companies_with_subunit_domain_hint": len(unresolved_with_candidates),
        "companies_with_explicit_subunit_website_hint": len(companies_with_explicit_website_hint),
        "companies_with_subunit_email_domain_hint": len(companies_with_email_hint),
        "unique_candidate_domains": len(unique_candidate_domains),
        "candidate_rows": len(candidate_audit),
        "probe_attempts": int(result.get("attempts") or 0),
        "logical_requests_added": int(result.get("logical_requests") or 0),
        "conservative_request_charge_added": int(result.get("conservative_request_charge") or 0),
        "verified_by_challenger": int(result.get("verified") or 0),
        "verified_websites_after": len(after_probe_sites),
        "net_new_verified_websites": len(new_site_orgs),
        "net_new_verified_website_orgs": sorted(new_site_orgs),
        "contact_companies_before": len(before_contacts),
        "contact_companies_after": len(after_contacts),
        "net_new_contact_companies": len(after_contacts - before_contacts),
        "social_companies_before": len(before_socials),
        "social_companies_after": len(after_socials),
        "net_new_social_companies": len(after_socials - before_socials),
        "bytes_added": int(result.get("bytes") or 0),
        "runtime_seconds": float(result.get("runtime_seconds") or 0.0),
        "third_party_api_cost_usd": 0.0,
        "candidate_generation_network_requests": 0,
        "candidate_is_evidence": False,
        "publication_rule": "independent fetched page proves exact parent org OR exact multi-token parent legal name plus BRREG parent location; conflicting org rejects; subunit identity alone is insufficient",
        "optimization_metric": "net-new correct verified parent websites per conservative request charge",
        "manual_audit_required": True,
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
