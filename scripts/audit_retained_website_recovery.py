#!/usr/bin/env python3
"""Audit zero-network recovery from retained exact-company website evidence.

Research-only. No network access and no production mutation.

Candidate families:
1. same-domain contact email found in already-retained exact-site page text or
   structured Organization data, beyond currently published external.contact_email;
2. structured Organization.description found in already-retained JSON-LD for an
   exact verified website, where no company_description is currently published.

The audit deliberately avoids arbitrary page summarisation.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

EMAIL_RE = re.compile(
    r"(?i)(?<![A-Z0-9._%+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![A-Z0-9._%+-])"
)
BLOCKED_LOCAL = {
    "example",
    "name",
    "yourname",
    "email",
    "test",
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
}


def _registered_domain_from_host(host: str) -> str:
    host = host.casefold().strip(".").removeprefix("www.")
    parts = [p for p in host.split(".") if p]
    if len(parts) < 2:
        return host
    # Sufficient for this Norwegian/company-domain audit; production continues
    # to use the existing website._registered_domain implementation.
    return ".".join(parts[-2:])


def registered_domain(url: str) -> str:
    try:
        return _registered_domain_from_host(urlparse(url).hostname or "")
    except ValueError:
        return ""


def same_domain_email(email: str, website_url: str) -> bool:
    value = str(email or "").strip().lower()
    if value.count("@") != 1:
        return False
    local, domain = value.split("@", 1)
    if not local or local in BLOCKED_LOCAL or not domain:
        return False
    return bool(
        registered_domain(website_url)
        and _registered_domain_from_host(domain) == registered_domain(website_url)
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def output_index(path: Path) -> dict[str, dict[str, Any]]:
    import gzip

    out: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            org = str(row.get("organisation_number") or "")
            if org:
                out[org] = row
    return out


def available_claim_values(row: dict[str, Any], field: str) -> list[Any]:
    return [
        claim.get("value")
        for claim in row.get("claims") or []
        if isinstance(claim, dict)
        and claim.get("field") == field
        and claim.get("availability") == "available"
        and claim.get("value") is not None
    ]


def website_record(profile: dict[str, Any]) -> dict[str, Any] | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return None
    return website


def retained_texts(value: dict[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    top = str(value.get("identity_text_excerpt") or "").strip()
    if top:
        rows.append(("identity_text_excerpt", top))
    for i, page in enumerate(value.get("pages") or []):
        if not isinstance(page, dict):
            continue
        text = str(page.get("main_text_excerpt") or "").strip()
        if text:
            rows.append((f"page_{i}_main_text_excerpt", text))
    for i, org in enumerate(value.get("structured_organisations") or []):
        if not isinstance(org, dict):
            continue
        # Serialize only already-retained structured data to permit email
        # discovery in explicit schema.org Organization fields.
        rows.append((f"structured_organisation_{i}", json.dumps(org, ensure_ascii=False)))
    return rows


def structured_descriptions(value: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for org in value.get("structured_organisations") or []:
        if not isinstance(org, dict):
            continue
        desc = str(org.get("description") or "").strip()
        if 30 <= len(desc) <= 2000:
            found.append(desc)
    return list(dict.fromkeys(found))


def audit(profiles: list[dict[str, Any]], outputs: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    verified_sites = 0
    email_candidate_companies = 0
    email_candidates = 0
    description_candidate_companies = 0
    description_candidates = 0
    email_source_counts = Counter()
    audit_rows: list[dict[str, Any]] = []

    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        output = outputs.get(org)
        if not output:
            continue
        website = website_record(profile)
        if not website:
            continue
        verified_sites += 1
        value = website.get("value") or {}
        url = str(value.get("final_url") or website.get("source_url") or "").strip()

        existing_emails = {
            str(v).strip().lower()
            for v in available_claim_values(output, "external.contact_email")
            if isinstance(v, str)
        }

        found_emails: dict[str, set[str]] = {}
        for source, text in retained_texts(value):
            for match in EMAIL_RE.finditer(text):
                email = match.group(1).strip().lower()
                if email in existing_emails or not same_domain_email(email, url):
                    continue
                found_emails.setdefault(email, set()).add(source)

        missing_description = not available_claim_values(output, "company_description")
        descs = structured_descriptions(value) if missing_description else []

        if found_emails:
            email_candidate_companies += 1
            email_candidates += len(found_emails)
            for sources in found_emails.values():
                for source in sources:
                    email_source_counts[source] += 1

        if descs:
            description_candidate_companies += 1
            description_candidates += len(descs)

        if found_emails or descs:
            # This research artifact intentionally retains no email address or
            # description text. It only keeps provenance class/counts for audit.
            audit_rows.append(
                {
                    "organisation_number": org,
                    "has_net_new_same_domain_email_candidate": bool(found_emails),
                    "net_new_email_candidate_count": len(found_emails),
                    "email_candidate_source_classes": sorted(
                        {source for sources in found_emails.values() for source in sources}
                    ),
                    "has_structured_description_candidate": bool(descs),
                    "structured_description_candidate_count": len(descs),
                }
            )

    total = len(profiles)
    report = {
        "screen_type": "retained_exact_site_zero_network_recovery",
        "profiles": total,
        "verified_site_companies": verified_sites,
        "net_new_same_domain_email_candidate_companies": email_candidate_companies,
        "net_new_same_domain_email_candidates": email_candidates,
        "email_candidate_reach_all_profiles": round(email_candidate_companies / total, 6) if total else 0.0,
        "email_candidate_reach_verified_sites": round(email_candidate_companies / verified_sites, 6) if verified_sites else 0.0,
        "email_candidate_source_counts": dict(sorted(email_source_counts.items())),
        "structured_description_candidate_companies": description_candidate_companies,
        "structured_description_candidates": description_candidates,
        "description_candidate_reach_all_profiles": round(description_candidate_companies / total, 6) if total else 0.0,
        "description_candidate_reach_verified_sites": round(description_candidate_companies / verified_sites, 6) if verified_sites else 0.0,
        "network_requests": 0,
        "production_publication_enabled": False,
        "notes": [
            "Only already-retained evidence from exact verified company websites is inspected.",
            "Email candidates must match the verified website registered domain.",
            "Existing published contact emails are excluded from net-new counts.",
            "Description candidates come only from retained structured Organization.description fields.",
            "No arbitrary main-text company-description synthesis is attempted.",
            "Candidate values are not retained in the research artifact.",
        ],
    }
    return report, audit_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    args = ap.parse_args()

    profile_paths = sorted(args.profiles_dir.rglob("profiles.jsonl"))
    if not profile_paths:
        raise SystemExit("no retained profiles.jsonl found")
    profiles: list[dict[str, Any]] = []
    for path in profile_paths:
        profiles.extend(read_jsonl(path))
    if len(profiles) != 1000 or len({str(p.get("organisation_number") or "") for p in profiles}) != 1000:
        raise SystemExit(f"expected 1000 unique retained profiles, got {len(profiles)}")

    outputs = output_index(args.output_contract_gz)
    report, audit_rows = audit(profiles, outputs)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.audit.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in audit_rows),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
