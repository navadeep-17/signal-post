from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from .discovery import qualify_search_discovered_website
from .final_site_discovery import MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE, _publishable, fetch_bounded_homepage
from .h1g_hyphenated_no_recall import evaluate_hyphenated_no_fallback, hyphenated_no_candidate
from .identity import apply_website_identity_gate
from .v9_openai_websearch_v2 import search_candidate_urls
from .zero_cost_registry_guard import apply_registry_risk_guard


def _provider_cost(nomination: dict[str, Any]) -> dict[str, Any]:
    value = nomination.get("cost") or {}
    return {
        "web_search_calls": int(value.get("web_search_calls") or 0),
        "input_tokens": int(value.get("input_tokens") or 0),
        "output_tokens": int(value.get("output_tokens") or 0),
        "estimated_cost_usd": float(value.get("estimated_cost_usd") or 0.0),
    }


def evaluate_m13_search_slot(
    profile: dict[str, Any],
    *,
    enabled: bool,
    api_key: str,
    timeout: float = 6.0,
    base_site_logical_requests: int | None = None,
    search_fn: Callable[..., dict[str, Any]] = search_candidate_urls,
    fetch_fn: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = fetch_bounded_homepage,
    h1g_evaluator: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = evaluate_hyphenated_no_fallback,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Use one provider search to nominate a replacement for the final H1g site slot.

    The provider is never publication evidence. Search is attempted only when the frozen
    baseline could itself spend H1g's final two logical site requests. A nominated URL may
    consume those same two site requests and must pass the existing page identity gate,
    the stricter search-discovered-page guard, and the registry-risk guard. If no URL is
    nominated, the original H1g path runs unchanged. If a nominated URL is fetched but
    rejected, H1g is not attempted because the final site slot has already been consumed.

    The one provider HTTP request is accounted separately by the caller. It is the only
    structural request increment M13 introduces.
    """
    row = deepcopy(profile)
    website = ((row.get("evidence") or {}).get("website") or {})
    result: dict[str, Any] = {
        "organisation_number": str(row.get("organisation_number") or ""),
        "strategy": "preserve_h1g",
        "search_eligible": False,
        "provider_attempted": False,
        "provider_api_requests": 0,
        "provider_web_search_calls": 0,
        "provider_input_tokens": 0,
        "provider_output_tokens": 0,
        "provider_estimated_cost_usd": 0.0,
        "provider_status": None,
        "query_sha256": [],
        "candidate_count": 0,
        "candidate_url": None,
        "candidate_fetch_attempted": False,
        "candidate_fetch_logical_requests": 0,
        "candidate_fetch_bytes": 0,
        "candidate_fetch_latencies_ms": [],
        "verified": False,
        "selected_url": None,
        "registry_risk_reasons": [],
        "h1g_fallback_attempted": False,
        "h1g_result": None,
    }

    # Preserve baseline behavior, including spare-slot activity feed, when a site is already exact.
    if _publishable(website) or not enabled or not str(api_key or "").strip():
        baseline_row, h1g = h1g_evaluator(
            row,
            timeout=timeout,
            base_site_logical_requests=base_site_logical_requests,
        )
        result["h1g_result"] = h1g
        result["h1g_fallback_attempted"] = bool(h1g.get("attempted"))
        result["strategy"] = (
            "preserve_verified_site_behavior"
            if _publishable(website)
            else "preserve_h1g_search_disabled"
        )
        return baseline_row, result

    try:
        base_requests = int(base_site_logical_requests) if base_site_logical_requests is not None else -1
    except (TypeError, ValueError):
        base_requests = -1

    baseline_candidate = hyphenated_no_candidate(row)
    if (
        base_requests < 0
        or baseline_candidate is None
        or base_requests + 2 > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    ):
        baseline_row, h1g = h1g_evaluator(
            row,
            timeout=timeout,
            base_site_logical_requests=base_site_logical_requests,
        )
        result["h1g_result"] = h1g
        result["h1g_fallback_attempted"] = bool(h1g.get("attempted"))
        result["strategy"] = "preserve_h1g_no_replaceable_slot"
        return baseline_row, result

    result["search_eligible"] = True
    result["provider_attempted"] = True
    # Count the outbound Responses API request even if the hosted search tool fails/abstains.
    result["provider_api_requests"] = 1

    nomination = search_fn(row, api_key=api_key)
    cost = _provider_cost(nomination)
    result["provider_web_search_calls"] = cost["web_search_calls"]
    result["provider_input_tokens"] = cost["input_tokens"]
    result["provider_output_tokens"] = cost["output_tokens"]
    result["provider_estimated_cost_usd"] = cost["estimated_cost_usd"]
    result["provider_status"] = str(nomination.get("status") or "")
    result["query_sha256"] = [
        str(value) for value in (nomination.get("query_sha256") or []) if len(str(value)) == 64
    ]
    candidates = [str(value) for value in (nomination.get("candidate_urls") or []) if str(value).strip()]
    candidates = candidates[:1]
    result["candidate_count"] = len(candidates)

    # Provider failure/no candidate spends only the provider request, then leaves the original
    # H1g site slot unchanged.
    if not candidates:
        baseline_row, h1g = h1g_evaluator(
            row,
            timeout=timeout,
            base_site_logical_requests=base_requests,
        )
        result["h1g_result"] = h1g
        result["h1g_fallback_attempted"] = bool(h1g.get("attempted"))
        result["strategy"] = "search_no_candidate_then_h1g"
        return baseline_row, result

    candidate_url = candidates[0]
    result["candidate_url"] = candidate_url
    result["candidate_fetch_attempted"] = True
    fetched, operations = fetch_fn(
        candidate_url,
        source_type="v9_m13_search_candidate_website",
        timeout=timeout,
    )
    added = int(operations.get("requests") or 0)
    if base_requests + added > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        raise RuntimeError(
            f"M13 search candidate exceeded site ceiling for {row.get('organisation_number')}: "
            f"{base_requests + added}>{MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE}"
        )
    result["candidate_fetch_logical_requests"] = added
    result["candidate_fetch_bytes"] = int(operations.get("bytes") or 0)
    result["candidate_fetch_latencies_ms"] = [
        int(value) for value in (operations.get("latencies_ms") or []) if value is not None
    ]

    fetched["source_class"] = "company_owned_candidate"
    gated = apply_website_identity_gate(row, fetched)
    candidate_record = gated["website"]
    assessment = qualify_search_discovered_website(
        row,
        candidate_record,
        gated.get("assessment"),
    )
    if assessment is not None:
        value = candidate_record.get("value") or {}
        value["identity_assessment"] = assessment
        candidate_record["value"] = value

    row.setdefault("evidence", {})["website_m13_search_candidate"] = candidate_record
    row.setdefault("discovery_audit", {})["m13_search"] = {
        "provider_status": result["provider_status"],
        "query_sha256": list(result["query_sha256"]),
        "candidate_url": candidate_url,
        "candidate_count": len(candidates),
        "provider_result_text_persisted": False,
        "provider_message_text_consumed": False,
        "provider_is_publication_evidence": False,
    }

    selected = bool(
        assessment
        and assessment.get("publishable")
        and candidate_record.get("status") == "available"
    )
    if selected:
        trial = deepcopy(row)
        trial.setdefault("evidence", {})["website"] = candidate_record
        trial["website"] = (
            (candidate_record.get("value") or {}).get("final_url")
            or candidate_record.get("source_url")
            or ""
        )
        trial, risks = apply_registry_risk_guard(trial)
        result["registry_risk_reasons"] = list(risks or [])
        guarded = ((trial.get("evidence") or {}).get("website") or {})
        if _publishable(guarded):
            row["evidence"]["website"] = guarded
            row["website"] = trial.get("website") or ""
            result["verified"] = True
            result["selected_url"] = row["website"]
            result["strategy"] = "m13_search_replaced_h1g"
            return row, result

    # The candidate consumed the two-request site slot. Fail closed instead of adding H1g.
    result["strategy"] = "m13_search_candidate_rejected_slot_consumed"
    return row, result
