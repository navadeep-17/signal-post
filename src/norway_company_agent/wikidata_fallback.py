from __future__ import annotations

from copy import deepcopy
from typing import Any

from .evidence import evidence
from .final_site_discovery import (
    MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
    _add_metrics,
    _publishable,
    fetch_bounded_homepage,
)
from .identity import apply_website_identity_gate
from .wikidata_discovery import WIKIDATA_SPARQL_URL, qualify_wikidata_candidate_identity
from .zero_cost_registry_guard import apply_registry_risk_guard


def apply_wikidata_fallback_to_existing_profile(
    profile: dict[str, Any],
    *,
    wikidata_candidate: dict[str, Any] | None,
    current_site_requests: int,
    timeout: float = 6.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply only H1e to an already-completed H1d profile.

    This is used for same-corpus experimentation so H1d is not rerun or displaced. The
    returned metrics contain the existing site-request count plus any H1e homepage probe.
    """
    if current_site_requests < 0 or current_site_requests > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        raise ValueError("current_site_requests is outside the qualified H1d site budget")

    row = deepcopy(profile)
    total: dict[str, Any] = {
        "requests": current_site_requests,
        "added_requests": 0,
        "bytes": 0,
        "latencies_ms": [],
        "wikidata_candidate_available": bool(wikidata_candidate),
        "wikidata_attempted": False,
        "wikidata_verified": False,
        "selected_source": None,
        "promoted": False,
    }
    existing_website = (row.get("evidence") or {}).get("website") or {}
    if _publishable(existing_website):
        total["wikidata_skipped_reason"] = "verified_site_already_present"
        return row, total
    if not wikidata_candidate:
        total["wikidata_skipped_reason"] = "no_unambiguous_candidate"
        return row, total
    if current_site_requests + 2 > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        total["wikidata_skipped_reason"] = "site_request_budget_consumed"
        return row, total

    candidate_url = str(wikidata_candidate.get("url") or "")
    if not candidate_url:
        total["wikidata_skipped_reason"] = "candidate_url_missing"
        return row, total

    total["wikidata_attempted"] = True
    before = int(total["requests"])
    record, ops = fetch_bounded_homepage(
        candidate_url,
        source_type="wikidata_official_website_candidate",
        timeout=timeout,
    )
    _add_metrics(total, ops)
    total["added_requests"] = int(total["requests"]) - before
    record["source_class"] = "open_knowledge_graph_candidate"

    gated = apply_website_identity_gate(row, record)
    candidate_record = gated["website"]
    assessment = qualify_wikidata_candidate_identity(
        row,
        candidate_record,
        gated.get("assessment"),
    )
    if assessment is not None:
        value = candidate_record.get("value") or {}
        value["identity_assessment"] = assessment
        candidate_record["value"] = value

    selected = bool(
        assessment
        and assessment.get("publishable")
        and candidate_record.get("status") == "available"
    )
    evidence_map = row.setdefault("evidence", {})
    item_url = str(wikidata_candidate.get("wikidata_item") or WIKIDATA_SPARQL_URL)
    evidence_map["website_wikidata_discovery"] = evidence(
        "website_wikidata_discovery",
        "available" if selected else "not_found",
        "wikidata_exact_org_candidate_discovery",
        item_url,
        value={
            "organisation_number_property": "P2333",
            "official_website_property": "P856",
            "candidate_url": candidate_url,
            "independent_page_url": (candidate_record.get("value") or {}).get("final_url") if selected else None,
            "publishable": selected,
            "third_party_cost_usd": 0.0,
        },
        source_row_key=row.get("organisation_number"),
        note="Exact Wikidata P2333/P856 mapping nominates a candidate only; publication requires independent company-page identity proof.",
    )
    evidence_map["website_wikidata_candidate"] = candidate_record

    if selected:
        candidate_row = deepcopy(row)
        candidate_evidence = candidate_row.setdefault("evidence", {})
        candidate_evidence["website"] = candidate_record
        candidate_row["website"] = (
            (candidate_record.get("value") or {}).get("final_url")
            or candidate_record.get("source_url")
            or ""
        )
        guarded, reasons = apply_registry_risk_guard(candidate_row)
        if _publishable((guarded.get("evidence") or {}).get("website") or {}):
            row = guarded
            total["selected_source"] = "wikidata_candidate"
            total["promoted"] = True
            total["wikidata_verified"] = True
        else:
            total["wikidata_guard_reasons"] = reasons

    if int(total.get("requests") or 0) > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        raise RuntimeError(f"H1e fallback exceeded logical site request ceiling: {total['requests']}")
    return row, total
