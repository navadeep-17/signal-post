#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.registry_contact import registered_contact_email  # noqa: E402


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def existing_contact_emails(profile: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for observation in profile.get("external_observations") or []:
        if not isinstance(observation, dict):
            continue
        value = str(observation.get("contact_email") or "").strip().casefold()
        if value and value not in values:
            values.append(value)
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen exact-org BRREG registered contact-email fallback with zero network.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()

    profiles = read_jsonl(Path(args.profiles))
    audit: list[dict[str, Any]] = []
    before_companies = 0
    after_companies = 0
    registry_rows = 0
    net_new_companies = 0
    same_as_existing = 0

    for profile in profiles:
        before = existing_contact_emails(profile)
        registry_email = registered_contact_email(profile)
        if before:
            before_companies += 1
        if registry_email:
            registry_rows += 1
        fallback = registry_email if registry_email and not before else ""
        if registry_email and registry_email in before:
            same_as_existing += 1
        if fallback:
            net_new_companies += 1
        if before or fallback:
            after_companies += 1
        if registry_email:
            registry = ((profile.get("evidence") or {}).get("registry") or {})
            audit.append(
                {
                    "organisation_number": str(profile.get("organisation_number") or ""),
                    "company_name": profile.get("name"),
                    "legal_form": profile.get("legal_form"),
                    "existing_first_party_contacts": before,
                    "registered_contact_email": registry_email,
                    "would_publish_as_fallback": bool(fallback),
                    "source_url": registry.get("source_url"),
                    "source_row_key": registry.get("source_row_key"),
                    "content_sha256": registry.get("content_sha256"),
                    "claim_semantics": "BRREG public registered contact email; not website/domain ownership or deliverability",
                }
            )

    report = {
        "experiment": "V6i exact-org BRREG registered contact email",
        "input_profiles": len(profiles),
        "contact_companies_before": before_companies,
        "companies_with_valid_registered_email": registry_rows,
        "registered_email_equal_to_existing_contact": same_as_existing,
        "net_new_contact_companies": net_new_companies,
        "contact_companies_after": after_companies,
        "added_logical_requests": 0,
        "added_conservative_request_charge": 0,
        "third_party_api_cost_usd": 0.0,
        "website_identity_changed": False,
        "publication_semantics": "Exact-org official registry contact fallback only when no stronger first-party contact is already published.",
        "candidate_is_website_evidence": False,
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path(args.audit).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.audit).open("w", encoding="utf-8") as handle:
        for row in audit:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
