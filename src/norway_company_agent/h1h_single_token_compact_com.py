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


def single_token_compact_com_candidate(profile: dict[str, Any]) -> dict[str, str] | None:
    """Return <single-distinctive-legal-name-token>.com for otherwise-idle final site capacity.

    This is nomination only. It intentionally applies only when the legal name has exactly
    one distinctive token, a case where H1g's hyphenated .no strategy has no candidate.
    """
    tokens = distinctive_legal_name_tokens(profile.get("name"))
    if len(tokens) != 1:
        return None
    label = tokens[0].strip("-")
    if not (3 <= len(label) <= 63):
        return None
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label):
        return None
    domain = f"{label}.com"
    return {
        "domain": domain,
        "url": f"https://{domain}/",
        "strategy": "single_token_legal_name_compact_com",
    }


def _quarantine(assessment: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **assessment,
        "status": "review",
        "score": min(float(assessment.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [*list(assessment.get("reasons") or []), reason],
        "method": "h1h_single_token_compact_com_identity_v1",
    }


def qualify_single_token_compact_com_identity(
    profile: dict[str, Any],
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Fail closed on guessed .com domains.

    Exact target organisation number is required. A guessed single-token .com may be a
    parent/group site that mentions a Norwegian affiliate, so legal-name/location similarity
    alone never authorizes publication.
    """
    if not assessment or not assessment.get("publishable") or website.get("status") != "available":
        return assessment

    if _has_conflicting_explicit_org_number(profile, website):
        return _quarantine(
            assessment,
            "H1h independently fetched .com candidate identifies a different organisation number",
        )

    if _page_contains_org_number(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "H1h independently fetched .com homepage contains exact target organisation number",
            ],
            "method": "h1h_single_token_compact_com_identity_v1",
        }

    # A guessed single-token .com is unusually collision-prone and may be a group/parent
    # website that merely lists a Norwegian affiliate or location. Full legal-name +
    # location text is therefore insufficient. H1h publication requires the exact target
    # Norwegian organisation number on the independently fetched page.
    return _quarantine(
        assessment,
        "H1h single-token .com candidate lacks exact target organisation-number proof",
    )


def evaluate_single_token_compact_com_fallback(
    profile: dict[str, Any],
    *,
    timeout: float = 6.0,
    base_site_logical_requests: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Use two otherwise-idle site requests for a single-token compact .com candidate."""

    row = deepcopy(profile)
    website = (row.get("evidence") or {}).get("website") or {}
    candidate = single_token_compact_com_candidate(row)

    try:
        base_requests = int(base_site_logical_requests) if base_site_logical_requests is not None else -1
    except (TypeError, ValueError):
        base_requests = -1
    base_requests = base_requests if 0 <= base_requests <= MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE else None

    result: dict[str, Any] = {
        "organisation_number": str(row.get("organisation_number") or ""),
        "candidate_available": bool(candidate),
        "candidate_domain": candidate.get("domain") if candidate else None,
        "attempted": False,
        "verified": False,
        "base_site_logical_requests": base_requests,
        "requests_added": 0,
        "post_site_logical_requests": base_requests,
        "bytes_added": 0,
        "latencies_ms": [],
        "skipped_reason": None,
        "guard_reasons": [],
        "selected_url": None,
    }

    if _publishable(website):
        result["skipped_reason"] = "verified_website_present"
        return row, result
    if base_requests is None:
        result["skipped_reason"] = "base_site_request_accounting_unavailable"
        return row, result
    if not candidate:
        result["skipped_reason"] = "not_single_token_legal_name"
        return row, result
    if base_requests + 2 > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        result["skipped_reason"] = "site_request_budget_consumed"
        return row, result

    result["attempted"] = True
    record, operations = fetch_bounded_homepage(
        candidate["url"],
        source_type="deterministic_single_token_compact_com_fallback",
        timeout=timeout,
    )
    added_requests = int(operations.get("requests") or 0)
    post_site_requests = base_requests + added_requests
    if post_site_requests > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        raise RuntimeError(
            f"H1h exceeded site request ceiling for {row.get('organisation_number')}: "
            f"{post_site_requests}>{MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE}"
        )
    result["requests_added"] = added_requests
    result["post_site_logical_requests"] = post_site_requests
    result["bytes_added"] = int(operations.get("bytes") or 0)
    result["latencies_ms"] = [
        int(value) for value in (operations.get("latencies_ms") or []) if value is not None
    ]

    record["source_class"] = "company_owned_candidate"
    gated = apply_website_identity_gate(row, record)
    candidate_record = gated["website"]
    assessment = qualify_single_token_compact_com_identity(
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
    evidence_map["website_h1h_compact_com_discovery"] = evidence(
        "website_h1h_compact_com_discovery",
        "available" if selected else "not_found",
        "deterministic_single_token_compact_com_fallback",
        BRREG_BULK_URL,
        value={
            "candidate_strategy": candidate["strategy"],
            "candidate_domain": candidate["domain"],
            "independent_page_url": (
                (candidate_record.get("value") or {}).get("final_url") if selected else None
            ),
            "publishable_before_registry_guard": selected,
            "base_site_logical_requests": base_requests,
            "requests_added": added_requests,
            "post_site_logical_requests": post_site_requests,
            "third_party_cost_usd": 0.0,
        },
        source_row_key=row.get("organisation_number"),
        note=(
            "H1h compact .com candidate is deterministically derived only for a single-token "
            "BRREG legal name and independently fetched; publication requires exact page identity."
        ),
    )
    evidence_map["website_h1h_candidate"] = candidate_record

    if not selected:
        return row, result

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

    return row, result
