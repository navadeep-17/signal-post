from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


FAMILY_FIELDS: dict[str, frozenset[str]] = {
    "verified_website": frozenset({"official_website"}),
    "social": frozenset({"external.profile_handle"}),
    "external_contact": frozenset({"external.contact_email", "external.contact_phone"}),
    "careers_surface": frozenset({"external.careers_page"}),
    "company_authored_hiring_intent": frozenset({"external.hiring_intent"}),
    "specific_active_job": frozenset({"external.job_posting"}),
    "dated_first_party_activity": frozenset({"external.company_update"}),
}


def _available_claim_fields(row: dict[str, Any]) -> set[str]:
    fields: set[str] = set()
    for claim in row.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        field = str(claim.get("field") or "").strip()
        if not field or claim.get("availability") != "available":
            continue
        if claim.get("value") in (None, ""):
            continue
        fields.add(field)
    return fields


def _index_rows(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        org = str(row.get("organisation_number") or "").strip()
        if len(org) != 9 or not org.isdigit():
            raise ValueError(f"invalid organisation number: {org!r}")
        if org in indexed:
            raise ValueError(f"duplicate organisation number: {org}")
        indexed[org] = row
    return indexed


def _family_orgs(rows: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    result = {family: set() for family in FAMILY_FIELDS}
    for org, row in rows.items():
        available = _available_claim_fields(row)
        for family, fields in FAMILY_FIELDS.items():
            if available.intersection(fields):
                result[family].add(org)
    return result


def summarize_rows(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    indexed = _index_rows(rows)
    families = _family_orgs(indexed)
    terminal = Counter(
        str(((row.get("run") or {}).get("terminal_status") or "unknown"))
        for row in indexed.values()
    )
    errors = sum(len(row.get("errors") or []) for row in indexed.values())
    logical_requests = sum(
        int(((row.get("operations") or {}).get("requests") or 0))
        for row in indexed.values()
    )
    third_party_cost = sum(
        float(((row.get("operations") or {}).get("third_party_cost_usd") or 0.0))
        for row in indexed.values()
    )
    runtime_ms_values = [
        int((row.get("operations") or {}).get("runtime_ms"))
        for row in indexed.values()
        if (row.get("operations") or {}).get("runtime_ms") is not None
    ]
    return {
        "companies": len(indexed),
        "terminal_status_counts": dict(sorted(terminal.items())),
        "reported_errors": errors,
        "logical_requests": logical_requests,
        "conservative_request_charge": logical_requests * 2,
        "third_party_cost_usd": round(third_party_cost, 6),
        "profile_runtime_ms_sum": sum(runtime_ms_values),
        "family_company_coverage": {
            family: len(orgs) for family, orgs in families.items()
        },
    }


def compare_company_family_coverage(
    baseline_rows: Iterable[dict[str, Any]],
    challenger_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    baseline = _index_rows(baseline_rows)
    challenger = _index_rows(challenger_rows)
    if set(baseline) != set(challenger):
        missing = sorted(set(baseline) - set(challenger))
        extra = sorted(set(challenger) - set(baseline))
        raise ValueError(
            "baseline/challenger organisation sets differ: "
            f"missing={len(missing)} extra={len(extra)}"
        )

    baseline_families = _family_orgs(baseline)
    challenger_families = _family_orgs(challenger)
    deltas: dict[str, dict[str, int]] = {}
    for family in FAMILY_FIELDS:
        before = baseline_families[family]
        after = challenger_families[family]
        deltas[family] = {
            "baseline_companies": len(before),
            "challenger_companies": len(after),
            "net_new_companies": len(after - before),
            "lost_companies": len(before - after),
        }

    return {
        "companies": len(baseline),
        "same_company_set": True,
        "families": deltas,
        "baseline": summarize_rows(baseline.values()),
        "challenger": summarize_rows(challenger.values()),
        "wrong_company_publications": None,
        "manual_precision_audit_required": True,
        "notes": [
            "Company-family coverage is measured, not raw claim count.",
            "Conservative request charge uses the project's two-times logical-request theorem.",
            "Wrong-company publication count is deliberately not inferred automatically.",
        ],
    }
