from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from .domain_discovery import (
    _page_contains_full_legal_name,
    _page_contains_org_number,
    _page_matches_registry_location,
    distinctive_legal_name_tokens,
)
from .evidence import evidence
from .final_site_discovery import (
    BRREG_BULK_URL,
    MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
    _has_conflicting_explicit_org_number,
    _publishable,
    fetch_bounded_homepage,
)
from .identity import apply_website_identity_gate
from .zero_cost_registry_guard import apply_registry_risk_guard

OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE = 5


def hyphenated_no_candidate(profile: dict[str, Any]) -> dict[str, str] | None:
    """Return the second deterministic H1c-style legal-name candidate: hyphenated `.no`."""

    tokens = distinctive_legal_name_tokens(profile.get("name"))
    if len(tokens) < 2:
        return None
    label = "-".join(tokens).strip("-")
    if not (3 <= len(label) <= 63):
        return None
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label):
        return None
    domain = f"{label}.no"
    return {
        "domain": domain,
        "url": f"https://{domain}/",
        "strategy": "legal_name_hyphenated_no",
    }


def _quarantine(assessment: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **assessment,
        "status": "review",
        "score": min(float(assessment.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [*list(assessment.get("reasons") or []), reason],
        "method": "h1g_hyphenated_no_homepage_identity_v1",
    }


def qualify_hyphenated_no_identity(
    profile: dict[str, Any],
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Require strong independent identity proof for the second guessed `.no` homepage.

    Because H1g uses only remaining request headroom and does not allocate a secondary
    legal/contact page, title/domain similarity alone is insufficient. Publication needs
    the exact target organisation number or full legal name plus BRREG location.
    """

    if not assessment or not assessment.get("publishable") or website.get("status") != "available":
        return assessment

    if _has_conflicting_explicit_org_number(profile, website):
        return _quarantine(
            assessment,
            "H1g independently fetched hyphenated .no candidate identifies a different organisation number",
        )

    if _page_contains_org_number(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "H1g independently fetched hyphenated .no homepage contains exact target organisation number",
            ],
            "method": "h1g_hyphenated_no_homepage_identity_v1",
        }

    if _page_contains_full_legal_name(profile, website) and _page_matches_registry_location(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": max(float(assessment.get("score") or 0.95), 0.98),
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "H1g independently fetched hyphenated .no homepage has full legal name plus BRREG location corroboration",
            ],
            "method": "h1g_hyphenated_no_homepage_identity_v1",
        }

    return _quarantine(
        assessment,
        "H1g hyphenated .no candidate lacks exact organisation-number or legal-name-plus-BRREG-location proof",
    )


def _base_site_logical_requests(profile: dict[str, Any]) -> int | None:
    metrics = profile.get("run_metrics") or {}
    try:
        logical = int(metrics.get("logical_requests"))
    except (TypeError, ValueError):
        return None
    site = logical - OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE
    return site if 0 <= site <= MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE else None


def evaluate_hyphenated_no_fallback(
    profile: dict[str, Any],
    *,
    timeout: float = 6.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Evaluate H1g only inside request headroom left by unchanged production discovery."""

    row = deepcopy(profile)
    website = (row.get("evidence") or {}).get("website") or {}
    candidate = hyphenated_no_candidate(row)
    base_site_requests = _base_site_logical_requests(row)
    result: dict[str, Any] = {
        "organisation_number": str(row.get("organisation_number") or ""),
        "candidate_available": bool(candidate),
        "candidate_domain": candidate.get("domain") if candidate else None,
        "attempted": False,
        "verified": False,
        "base_site_logical_requests": base_site_requests,
        "requests_added": 0,
        "post_site_logical_requests": base_site_requests,
        "bytes_added": 0,
        "latencies_ms": [],
        "skipped_reason": None,
        "guard_reasons": [],
    }

    if _publishable(website):
        result["skipped_reason"] = "verified_website_present"
        return row, result
    if base_site_requests is None:
        result["skipped_reason"] = "base_site_request_accounting_unavailable"
        return row, result
    if not candidate:
        result["skipped_reason"] = "no_distinct_hyphenated_no_candidate"
        return row, result
    if base_site_requests + 2 > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        result["skipped_reason"] = "site_request_budget_consumed"
        return row, result

    result["attempted"] = True
    record, operations = fetch_bounded_homepage(
        candidate["url"],
        source_type="deterministic_legal_name_hyphenated_no_fallback",
        timeout=timeout,
    )
    added_requests = int(operations.get("requests") or 0)
    post_site_requests = base_site_requests + added_requests
    if post_site_requests > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        raise RuntimeError(
            f"H1g exceeded site request ceiling for {row.get('organisation_number')}: "
            f"{post_site_requests}>{MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE}"
        )
    result["requests_added"] = added_requests
    result["post_site_logical_requests"] = post_site_requests
    result["bytes_added"] = int(operations.get("bytes") or 0)
    result["latencies_ms"] = [int(value) for value in operations.get("latencies_ms") or []]

    record["source_class"] = "company_owned_candidate"
    gated = apply_website_identity_gate(row, record)
    candidate_record = gated["website"]
    assessment = qualify_hyphenated_no_identity(row, candidate_record, gated.get("assessment"))
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
    evidence_map["website_h1g_hyphenated_no_discovery"] = evidence(
        "website_h1g_hyphenated_no_discovery",
        "available" if selected else "not_found",
        "deterministic_legal_name_hyphenated_no_fallback",
        BRREG_BULK_URL,
        value={
            "candidate_strategy": candidate["strategy"],
            "candidate_domain": candidate["domain"],
            "independent_page_url": (candidate_record.get("value") or {}).get("final_url") if selected else None,
            "publishable_before_registry_guard": selected,
            "base_site_logical_requests": base_site_requests,
            "requests_added": added_requests,
            "post_site_logical_requests": post_site_requests,
            "third_party_cost_usd": 0.0,
        },
        source_row_key=row.get("organisation_number"),
        note=(
            "H1g hyphenated .no candidate is derived from the BRREG legal name and independently fetched; "
            "publication requires exact org-number or legal-name-plus-location proof."
        ),
    )
    evidence_map["website_h1g_candidate"] = candidate_record

    if selected:
        trial = deepcopy(row)
        trial.setdefault("evidence", {})["website"] = candidate_record
        trial["website"] = (
            (candidate_record.get("value") or {}).get("final_url")
            or candidate_record.get("source_url")
            or ""
        )
        trial, guard_reasons = apply_registry_risk_guard(trial)
        result["guard_reasons"] = list(guard_reasons or [])
        guarded_website = (trial.get("evidence") or {}).get("website") or {}
        if _publishable(guarded_website):
            row["evidence"]["website"] = guarded_website
            row["website"] = trial.get("website") or ""
            result["verified"] = True
            result["selected_url"] = row["website"]
        else:
            result["selected_url"] = None
    else:
        result["selected_url"] = None

    return row, result
