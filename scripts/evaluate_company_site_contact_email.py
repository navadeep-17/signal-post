#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_contact import company_site_contact_email_observations  # noqa: E402
from norway_company_agent.external_footprint import validate_observation  # noqa: E402


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure zero-network H2c same-domain company contact email yield.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--observations", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    profiles = read_jsonl(Path(args.profiles))
    observations: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    validation_errors: list[dict[str, str]] = []
    verified_sites = 0

    for profile in profiles:
        website = ((profile.get("evidence") or {}).get("website") or {})
        value = website.get("value") or {}
        identity = value.get("identity_assessment") or {}
        if website.get("status") == "available" and identity.get("publishable"):
            verified_sites += 1

        rows = company_site_contact_email_observations(profile)
        observations.extend(rows)
        org = str(profile.get("organisation_number") or "")
        for item in rows:
            errors = validate_observation(item)
            validation_errors.extend(
                {
                    "organisation_number": org,
                    "observation_id": str(item.get("id") or ""),
                    "error": error,
                }
                for error in errors
            )
            audit.append(
                {
                    "organisation_number": org,
                    "legal_name": profile.get("name"),
                    "verified_website": value.get("final_url") or website.get("source_url"),
                    "website_identity_method": identity.get("method"),
                    "website_identity_score": identity.get("score"),
                    "contact_email": item.get("contact_email"),
                    "source_url": item.get("source_url"),
                    "content_sha256": item.get("content_sha256"),
                    "observation_id": item.get("id"),
                    "claim_scope": (item.get("metrics") or {}).get("claim_scope"),
                }
            )

    observations.sort(key=lambda row: (str(row.get("organisation_number") or ""), str(row.get("contact_email") or "")))
    audit.sort(key=lambda row: (str(row.get("organisation_number") or ""), str(row.get("contact_email") or "")))
    write_jsonl(Path(args.observations), observations)
    write_jsonl(Path(args.audit), audit)

    companies = {str(item.get("organisation_number") or "") for item in observations}
    report = {
        "profiles": len(profiles),
        "verified_websites": verified_sites,
        "companies_with_contact_email": len(companies),
        "contact_email_observations": len(observations),
        "reach_over_all_profiles": round(len(companies) / len(profiles), 6) if profiles else 0.0,
        "reach_over_verified_websites": round(len(companies) / verified_sites, 6) if verified_sites else 0.0,
        "network_requests_added": 0,
        "third_party_cost_usd_added": 0.0,
        "validation_errors": validation_errors,
        "passed": not validation_errors,
        "claim_boundary": (
            "Email explicitly present in bounded footer/contact/legal text on an exact verified company website, "
            "with email and website registered domains matching."
        ),
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if validation_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
