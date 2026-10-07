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
from .final_site_discovery import (
    _has_conflicting_explicit_org_number,
    _publishable,
    fetch_bounded_homepage,
)
from .identity import apply_website_identity_gate
from .zero_cost_registry_guard import apply_registry_risk_guard


def multitoken_compact_com_candidate(profile: dict[str, Any]) -> dict[str, str] | None:
    """Nominate compact <all distinctive legal-name tokens>.com for multi-token names only."""
    tokens = distinctive_legal_name_tokens(profile.get("name"))
    if len(tokens) < 2:
        return None
    label = "".join(tokens).strip("-")
    if not (3 <= len(label) <= 63):
        return None
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label):
        return None
    domain = f"{label}.com"
    return {
        "domain": domain,
        "url": f"https://{domain}/",
        "strategy": "multi_token_legal_name_compact_com",
    }


def _quarantine(assessment: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **assessment,
        "status": "review",
        "score": min(float(assessment.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [*list(assessment.get("reasons") or []), reason],
        "method": "h1i_multitoken_compact_com_identity_v1",
    }


def qualify_multitoken_compact_com_identity(
    profile: dict[str, Any],
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Require page-local exact identity for the guessed .com candidate.

    Compact-domain similarity is never sufficient. Publication requires exact target
    organisation number, or the complete legal name plus BRREG location corroboration.
    """

    if not assessment or not assessment.get("publishable") or website.get("status") != "available":
        return assessment

    if _has_conflicting_explicit_org_number(profile, website):
        return _quarantine(
            assessment,
            "H1i compact .com candidate independently identifies a different organisation number",
        )

    if _page_contains_org_number(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "H1i independently fetched compact .com homepage contains exact target organisation number",
            ],
            "method": "h1i_multitoken_compact_com_identity_v1",
        }

    if _page_contains_full_legal_name(profile, website) and _page_matches_registry_location(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": max(float(assessment.get("score") or 0.95), 0.98),
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "H1i independently fetched compact .com homepage has full legal name plus BRREG location corroboration",
            ],
            "method": "h1i_multitoken_compact_com_identity_v1",
        }

    return _quarantine(
        assessment,
        "H1i compact .com candidate lacks exact organisation-number or legal-name-plus-BRREG-location proof",
    )


def evaluate_multitoken_compact_com_candidate(
    profile: dict[str, Any],
    *,
    timeout: float = 6.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Sidecar-evaluate the candidate that would replace H1g's final two-request slot."""

    row = deepcopy(profile)
    website = (row.get("evidence") or {}).get("website") or {}
    candidate = multitoken_compact_com_candidate(row)
    result: dict[str, Any] = {
        "organisation_number": str(row.get("organisation_number") or ""),
        "candidate_available": bool(candidate),
        "candidate_domain": candidate.get("domain") if candidate else None,
        "attempted": False,
        "verified": False,
        "requests": 0,
        "bytes": 0,
        "latencies_ms": [],
        "selected_url": None,
        "guard_reasons": [],
        "skipped_reason": None,
    }

    if _publishable(website):
        result["skipped_reason"] = "verified_website_present"
        return row, result
    if not candidate:
        result["skipped_reason"] = "not_multi_token_legal_name"
        return row, result

    result["attempted"] = True
    record, operations = fetch_bounded_homepage(
        candidate["url"],
        source_type="deterministic_multi_token_compact_com_replacement",
        timeout=timeout,
    )
    result["requests"] = int(operations.get("requests") or 0)
    result["bytes"] = int(operations.get("bytes") or 0)
    result["latencies_ms"] = [
        int(value) for value in (operations.get("latencies_ms") or []) if value is not None
    ]

    record["source_class"] = "company_owned_candidate"
    gated = apply_website_identity_gate(row, record)
    candidate_record = gated["website"]
    assessment = qualify_multitoken_compact_com_identity(
        row,
        candidate_record,
        gated.get("assessment"),
    )
    if assessment is not None:
        value = candidate_record.get("value") or {}
        value["identity_assessment"] = assessment
        candidate_record["value"] = value

    result["website_status"] = candidate_record.get("status")
    result["identity_status"] = (assessment or {}).get("status")
    result["identity_score"] = (assessment or {}).get("score")
    result["identity_publishable"] = bool((assessment or {}).get("publishable"))
    result["identity_reasons"] = list((assessment or {}).get("reasons") or [])
    result["website_content_sha256"] = candidate_record.get("content_sha256")
    result["website_source_url"] = candidate_record.get("source_url")
    result["final_url"] = (candidate_record.get("value") or {}).get("final_url")

    if not (
        assessment
        and assessment.get("publishable")
        and candidate_record.get("status") == "available"
    ):
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
    guarded = (trial.get("evidence") or {}).get("website") or {}
    if not _publishable(guarded):
        return row, result

    row["evidence"]["website"] = guarded
    row["website"] = trial.get("website") or ""
    result["verified"] = True
    result["selected_url"] = row["website"]
    return row, result
