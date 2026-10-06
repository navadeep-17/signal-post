#!/usr/bin/env python3
"""Audit zero-network structured telephone recovery from exact verified websites.

Research-only. No network access and no production mutation.

A telephone candidate is accepted only when it appears in an explicit schema.org
field named telephone inside a retained Organization node that independently
identifies the exact target legal entity using the already-qualified structured
node identity rules.

The audit retains no telephone values. It only measures company-level coverage
and privacy-minimized provenance counts.
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

from norway_company_agent.company_site_contact import _structured_node_identity  # noqa: E402


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def output_index(path: Path) -> dict[str, dict[str, Any]]:
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


def _normalize_norwegian_phone(value: Any) -> str | None:
    """Return a conservative normalized Norwegian 8-digit phone number."""

    text = str(value or "").strip()
    if not text:
        return None
    if re.search(r"(?i)\b(?:ext|extension|x|innvalg)\b", text):
        return None

    compact = re.sub(r"[\s().-]", "", text)
    if compact.startswith("+47"):
        compact = compact[3:]
    elif compact.startswith("0047"):
        compact = compact[4:]
    elif compact.startswith("47") and len(compact) == 10:
        compact = compact[2:]

    if not re.fullmatch(r"\d{8}", compact):
        return None
    if compact[0] in {"0", "1"}:
        return None
    return compact


def _structured_telephone_values(value: Any, *, telephone_field: bool = False) -> set[str]:
    """Extract phones only from schema fields explicitly named telephone."""

    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.update(
                _structured_telephone_values(
                    child,
                    telephone_field=telephone_field or str(key).casefold() == "telephone",
                )
            )
    elif isinstance(value, list):
        for child in value:
            found.update(_structured_telephone_values(child, telephone_field=telephone_field))
    elif telephone_field and isinstance(value, (str, int)):
        phone = _normalize_norwegian_phone(value)
        if phone:
            found.add(phone)
    return found


def audit(
    profiles: list[dict[str, Any]],
    outputs: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    verified_sites = 0
    exact_node_companies = 0
    candidate_companies = 0
    candidate_values = 0
    current_registry_phone_companies = 0
    candidate_overlap_registry_phone = 0
    net_new_contact_phone_companies = 0
    identity_methods: Counter[str] = Counter()
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
        existing_phone = bool(
            available_claim_values(output, "registered_phone")
            or available_claim_values(output, "registered_mobile")
        )
        if existing_phone:
            current_registry_phone_companies += 1

        transient_phones: set[str] = set()
        accepted_nodes = 0
        methods: set[str] = set()
        for node in value.get("structured_organisations") or []:
            if not isinstance(node, dict):
                continue
            node_identity = _structured_node_identity(profile, node)
            if node_identity is None:
                continue
            accepted_nodes += 1
            methods.add(str(node_identity.get("method") or "unknown"))
            transient_phones.update(_structured_telephone_values(node))

        if accepted_nodes:
            exact_node_companies += 1
        if not transient_phones:
            continue

        candidate_companies += 1
        candidate_values += len(transient_phones)
        for method in methods:
            identity_methods[method] += 1

        if existing_phone:
            candidate_overlap_registry_phone += 1
        else:
            net_new_contact_phone_companies += 1

        audit_rows.append(
            {
                "organisation_number": org,
                "has_structured_phone_candidate": True,
                "structured_phone_candidate_count": len(transient_phones),
                "accepted_structured_node_count": accepted_nodes,
                "structured_identity_methods": sorted(methods),
                "already_has_registered_phone_or_mobile": existing_phone,
                "net_new_phone_coverage_candidate": not existing_phone,
            }
        )

    total = len(profiles)
    report = {
        "screen_type": "retained_exact_site_structured_phone_zero_network_audit",
        "profiles": total,
        "verified_site_companies": verified_sites,
        "companies_with_matching_structured_organization_node": exact_node_companies,
        "structured_phone_candidate_companies": candidate_companies,
        "structured_phone_candidate_values": candidate_values,
        "structured_phone_candidate_reach_all_profiles": round(candidate_companies / total, 6) if total else 0.0,
        "structured_phone_candidate_reach_verified_sites": round(candidate_companies / verified_sites, 6) if verified_sites else 0.0,
        "registered_phone_or_mobile_companies_among_verified_sites": current_registry_phone_companies,
        "structured_phone_overlap_registered_contact": candidate_overlap_registry_phone,
        "net_new_contact_phone_companies": net_new_contact_phone_companies,
        "net_new_contact_phone_reach_all_profiles": round(net_new_contact_phone_companies / total, 6) if total else 0.0,
        "structured_identity_method_company_counts": dict(sorted(identity_methods.items())),
        "network_requests": 0,
        "raw_phone_values_retained": False,
        "production_publication_enabled": False,
        "notes": [
            "Only already-retained exact verified company website snapshots are inspected.",
            "Only explicit schema.org telephone fields inside an independently target-matching Organization node are considered.",
            "Arbitrary free text and telephone values are never used as legal-entity identity evidence.",
            "Only conservative Norwegian 8-digit telephone shapes are counted.",
            "Raw telephone values are not written to the research artifact.",
            "Net-new coverage means the frozen output has neither registered_phone nor registered_mobile available.",
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
    unique = {str(p.get("organisation_number") or "") for p in profiles}
    if len(profiles) != 1000 or len(unique) != 1000:
        raise SystemExit(f"expected 1000 unique retained profiles, got {len(profiles)} / {len(unique)}")

    outputs = output_index(args.output_contract_gz)
    report, audit_rows = audit(profiles, outputs)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.audit.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in audit_rows),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
