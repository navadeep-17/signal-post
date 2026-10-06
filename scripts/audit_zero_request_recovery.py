#!/usr/bin/env python3
"""Offline audit for zero-request evaluator-facing recovery opportunities.

Reads only the frozen Signalpost output contract. No network access.

The audit does not create or relabel claims. It measures where facts that are
already present/evidenced may be under-surfaced in canonical evaluator areas.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def read_jsonl_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                if isinstance(row, dict):
                    yield row


def available_fields(row: dict[str, Any]) -> set[str]:
    return {
        str(c.get("field"))
        for c in row.get("claims") or []
        if isinstance(c, dict)
        and c.get("availability") == "available"
        and c.get("field")
    }


def canonical_types(row: dict[str, Any]) -> set[str]:
    return {
        str(f.get("type"))
        for f in row.get("canonical_facts") or []
        if isinstance(f, dict) and f.get("type")
    }


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    company_count = len(rows)
    field_companies: dict[str, set[str]] = defaultdict(set)
    type_companies: dict[str, set[str]] = defaultdict(set)
    data_area_companies: dict[str, set[str]] = defaultdict(set)

    opportunity_counts = Counter()
    opportunity_orgs: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        org = str(row.get("organisation_number") or "")
        fields = available_fields(row)
        types = canonical_types(row)

        for field in fields:
            field_companies[field].add(org)
        for typ in types:
            type_companies[typ].add(org)

        canonical = row.get("canonical_profile") or {}
        for area, present in (canonical.get("data_areas") or {}).items():
            if present:
                data_area_companies[str(area)].add(org)

        def mark(name: str, condition: bool) -> None:
            if condition:
                opportunity_counts[name] += 1
                opportunity_orgs[name].add(org)

        mark(
            "social_links_without_external_profile_handle",
            "social_links" in fields and "external.profile_handle" not in fields,
        )
        mark(
            "verified_website_without_external_contact_email",
            "official_website" in fields and "external.contact_email" not in fields,
        )
        mark(
            "verified_website_without_company_description",
            "official_website" in fields and "company_description" not in fields,
        )
        mark(
            "registered_contact_email_without_external_contact_email",
            "registered_contact_email" in fields and "external.contact_email" not in fields,
        )
        mark(
            "registered_phone_or_mobile_present",
            bool(fields & {"registered_phone", "registered_mobile"}),
        )
        mark(
            "registry_change_present",
            "official_registry_change" in fields,
        )
        mark(
            "registry_change_without_company_update",
            "official_registry_change" in fields and "external.company_update" not in fields,
        )
        mark(
            "workforce_snapshot_present",
            "external.workforce_snapshot" in fields,
        )
        mark(
            "workforce_snapshot_but_hiring_activity_area_false",
            "external.workforce_snapshot" in fields
            and not bool((canonical.get("data_areas") or {}).get("hiring_and_public_activity")),
        )
        mark(
            "support_award_but_hiring_activity_area_false",
            "official.support_award" in fields
            and not bool((canonical.get("data_areas") or {}).get("hiring_and_public_activity")),
        )
        mark(
            "registry_change_but_hiring_activity_area_false",
            "official_registry_change" in fields
            and not bool((canonical.get("data_areas") or {}).get("hiring_and_public_activity")),
        )

    fields_report = {
        field: {
            "companies": len(orgs),
            "coverage_pct": round(100 * len(orgs) / company_count, 2) if company_count else 0.0,
        }
        for field, orgs in sorted(field_companies.items())
    }
    types_report = {
        typ: {
            "companies": len(orgs),
            "coverage_pct": round(100 * len(orgs) / company_count, 2) if company_count else 0.0,
        }
        for typ, orgs in sorted(type_companies.items())
    }
    areas_report = {
        area: {
            "companies": len(orgs),
            "coverage_pct": round(100 * len(orgs) / company_count, 2) if company_count else 0.0,
        }
        for area, orgs in sorted(data_area_companies.items())
    }
    opp_report = {
        name: {
            "companies": int(count),
            "coverage_pct": round(100 * count / company_count, 2) if company_count else 0.0,
        }
        for name, count in sorted(opportunity_counts.items())
    }

    # Zero-request upper bounds if already-evidenced typed facts were surfaced in
    # evaluator-facing areas without changing their semantic type.
    hiring_now = data_area_companies.get("hiring_and_public_activity", set())
    workforce = field_companies.get("external.workforce_snapshot", set())
    registry_changes = field_companies.get("official_registry_change", set())
    support = field_companies.get("official.support_award", set())
    typed_activity_union = set(hiring_now) | set(workforce) | set(registry_changes) | set(support)

    return {
        "screen_type": "offline_zero_request_recovery_audit",
        "companies": company_count,
        "network_requests": 0,
        "available_claim_field_coverage": fields_report,
        "canonical_fact_type_coverage": types_report,
        "canonical_data_area_coverage": areas_report,
        "opportunities": opp_report,
        "typed_activity_surface_upper_bound": {
            "current_hiring_and_public_activity_companies": len(hiring_now),
            "current_hiring_and_public_activity_coverage_pct": round(100 * len(hiring_now) / company_count, 2) if company_count else 0.0,
            "workforce_snapshot_companies": len(workforce),
            "registry_change_companies": len(registry_changes),
            "support_award_companies": len(support),
            "union_if_typed_facts_are_surfaced_without_relabeling": len(typed_activity_union),
            "union_coverage_pct": round(100 * len(typed_activity_union) / company_count, 2) if company_count else 0.0,
            "net_new_area_companies_upper_bound": len(typed_activity_union - set(hiring_now)),
        },
        "privacy_boundary": {
            "organisation_number_lists_retained": False,
            "claim_values_retained": False,
            "evidence_text_retained": False,
            "aggregate_counts_only": True,
        },
        "notes": [
            "This audit is read-only and performs zero network requests.",
            "Upper bounds do not authorize semantic relabeling.",
            "Registry changes must remain typed as official registry changes, never company-authored news.",
            "Workforce snapshots must remain workforce facts, never active-hiring claims.",
            "Any projection change requires contract/canonical/synthesis regression checks before production.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-contract-gz", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    rows = list(read_jsonl_gz(args.output_contract_gz))
    if not rows:
        raise SystemExit("empty output contract")
    report = audit(rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
