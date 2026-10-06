#!/usr/bin/env python3
"""Aggregate frozen-1000 BRREG email-domain website opportunity audit.

Zero-network, research-only. Raw BRREG registry evidence is read from the archived
profiles; the frozen output is used only for the current verified-website baseline.
No candidate values or organisation-number lists are retained.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
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


def _email_domains(value: Any) -> list[str]:
    out: list[str] = []
    for part in re.split(r"[\s,;]+", str(value or "").strip()):
        candidate = part.strip("<>[](){}\"'")
        if "@" not in candidate:
            continue
        local, _, domain = candidate.rpartition("@")
        domain = domain.strip().strip(".").casefold()
        if local and domain and "." in domain:
            out.append(domain)
    return list(dict.fromkeys(out))


def read_profiles(path: Path) -> dict[str, dict[str, Any]]:
    files = sorted(path.rglob("profiles.jsonl"))
    if not files:
        raise ValueError("no profiles.jsonl found")
    out: dict[str, dict[str, Any]] = {}
    for file in files:
        for line in file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            org = re.sub(r"\D", "", str(row.get("organisation_number") or ""))
            if len(org) != 9 or org in out:
                raise ValueError(f"invalid or duplicate profile org: {org!r}")
            out[org] = row
    if len(out) != 1000:
        raise ValueError(f"expected 1000 archived profiles, got {len(out)}")
    return out


def current_website_orgs(path: Path) -> set[str]:
    out: set[str] = set()
    seen: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            org = re.sub(r"\D", "", str(row.get("organisation_number") or ""))
            if len(org) != 9 or org in seen:
                raise ValueError(f"invalid or duplicate output org: {org!r}")
            seen.add(org)
            if _available_value(_claims(row), "official_website"):
                out.add(org)
    if len(seen) != 1000:
        raise ValueError(f"expected 1000 output companies, got {len(seen)}")
    return out


def audit(profiles_dir: Path, output_path: Path) -> dict[str, Any]:
    profiles = read_profiles(profiles_dir)
    current_web = current_website_orgs(output_path)
    if set(profiles) != set(current_web) | (set(profiles) - current_web):
        raise AssertionError("unreachable set mismatch")

    registered_email_companies = 0
    missing_site_with_registered_email = 0
    nongeneric_domain_candidates = 0
    strengths: Counter[str] = Counter()
    strong_companies: set[str] = set()
    multi_domain_companies = 0

    for org, profile in profiles.items():
        registry = ((profile.get("evidence") or {}).get("registry") or {}).get("value") or {}
        domains = _email_domains(registry.get("epostadresse"))
        if not domains:
            continue
        registered_email_companies += 1
        if org in current_web:
            continue
        missing_site_with_registered_email += 1

        domains = [d for d in domains if d not in GENERIC_EMAIL_DOMAINS]
        if not domains:
            continue
        nongeneric_domain_candidates += 1
        if len(domains) > 1:
            multi_domain_companies += 1

        per_company_strengths = {
            _domain_identity_strength({"name": profile.get("name") or ""}, domain)
            for domain in domains
        }
        # Count one strongest bucket per company, not one count per address.
        rank = {"exact": 5, "acronym": 4, "multi": 3, "partial": 2, "none": 1}
        strongest = max(per_company_strengths, key=lambda x: rank.get(x, 0))
        strengths[strongest] += 1
        if per_company_strengths & {"exact", "multi", "acronym"}:
            strong_companies.add(org)

    companies = len(profiles)
    return {
        "screen_type": "zero_network_brreg_email_domain_opportunity_audit",
        "companies": companies,
        "current_verified_website_companies": len(current_web),
        "registered_contact_email_companies": registered_email_companies,
        "missing_website_with_registered_email": missing_site_with_registered_email,
        "nongeneric_email_domain_candidate_companies": nongeneric_domain_candidates,
        "multiple_nongeneric_domains_companies": multi_domain_companies,
        "domain_identity_strength_counts": dict(sorted(strengths.items())),
        "exact_multi_acronym_candidate_companies": len(strong_companies),
        "exact_multi_acronym_candidate_reach": round(len(strong_companies) / companies, 6),
        "network_requests": 0,
        "candidate_values_retained": False,
        "organisation_lists_retained": False,
        "production_publication_enabled": False,
        "notes": [
            "Raw BRREG epostadresse is read from exact registry evidence in archived profiles.",
            "Current verified websites are read independently from the frozen output contract.",
            "Consumer mailbox domains are excluded using the existing production generic-domain set.",
            "Domain-label/legal-name morphology is candidate-selection only and never publication proof.",
            "A live shadow replay is justified only if the strong candidate bucket is material.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    report = audit(args.profiles_dir, args.output_contract_gz)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
