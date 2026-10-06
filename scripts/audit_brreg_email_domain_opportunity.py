#!/usr/bin/env python3
"""Aggregate frozen-1000 BRREG email-domain website opportunity audit.

Zero-network, research-only. This does not change the verifier and does not publish
website candidates. It measures whether exact legal-name email domains are common
enough to justify a bounded shadow-verification replay.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.domain_discovery import (  # noqa: E402
    GENERIC_EMAIL_DOMAINS,
    _domain_identity_strength,
)


def _claims(row: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for claim in row.get("claims") or []:
        if not isinstance(claim, dict) or not claim.get("field"):
            continue
        out.setdefault(str(claim["field"]), []).append(claim)
    return out


def _available_value(claims: dict[str, list[dict[str, Any]]], field: str) -> Any:
    for claim in claims.get(field) or []:
        if claim.get("availability") == "available" and claim.get("value") not in (None, ""):
            return claim.get("value")
    return None


def _email_domain(value: Any) -> str | None:
    text = str(value or "").strip()
    if "@" not in text:
        return None
    domain = text.rsplit("@", 1)[1].strip().strip(".").casefold()
    if not domain or "." not in domain:
        return None
    return domain


def audit(path: Path) -> dict[str, Any]:
    companies = 0
    current_websites = 0
    registered_email_companies = 0
    missing_site_with_registered_email = 0
    nongeneric_domain_candidates = 0
    strengths: Counter[str] = Counter()
    exact_or_stronger = 0

    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            companies += 1
            claims = _claims(row)
            website = _available_value(claims, "official_website")
            if website:
                current_websites += 1

            email = _available_value(claims, "registered_contact_email")
            if not email:
                continue
            registered_email_companies += 1
            if website:
                continue
            missing_site_with_registered_email += 1

            domain = _email_domain(email)
            if not domain or domain in GENERIC_EMAIL_DOMAINS:
                continue
            nongeneric_domain_candidates += 1
            legal_name = _available_value(claims, "legal_name") or ""
            strength = _domain_identity_strength({"name": legal_name}, domain)
            strengths[strength] += 1
            if strength in {"exact", "multi", "acronym"}:
                exact_or_stronger += 1

    if companies != 1000:
        raise ValueError(f"expected frozen 1000 output rows, got {companies}")

    return {
        "screen_type": "zero_network_brreg_email_domain_opportunity_audit",
        "companies": companies,
        "current_verified_website_companies": current_websites,
        "registered_contact_email_companies": registered_email_companies,
        "missing_website_with_registered_email": missing_site_with_registered_email,
        "nongeneric_email_domain_candidate_companies": nongeneric_domain_candidates,
        "domain_identity_strength_counts": dict(sorted(strengths.items())),
        "exact_multi_acronym_candidate_companies": exact_or_stronger,
        "exact_multi_acronym_candidate_reach": round(exact_or_stronger / companies, 6),
        "network_requests": 0,
        "candidate_values_retained": False,
        "organisation_lists_retained": False,
        "production_publication_enabled": False,
        "notes": [
            "This is a counterfactual inventory only; the production website verifier is unchanged.",
            "Consumer mailbox domains are excluded using the existing production generic-domain set.",
            "Only domain-label/legal-name morphology is measured; it is never publication proof.",
            "A live shadow replay is justified only if the strong candidate bucket is material.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    report = audit(args.output_contract_gz)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
