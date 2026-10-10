"""Offline-only Tavily domain *nomination* adapter for the Signalpost M23 screen.

No network functions, credentials, provider client, or production hooks exist here.
Search metadata must remain transient and can NEVER establish a published claim.
Actual authorisation, evaluator reproducibility, runtime and new-site yield are
separate gates. Deliberately reusable only for fixture-based offline testing.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from .discovery import (
    build_company_search_query,
    choose_search_candidate,
    qualify_search_discovered_website,
)
from .final_site_discovery import _has_conflicting_explicit_org_number
from .identity import apply_website_identity_gate
from .website import normalize_homepage
from .zero_cost_registry_guard import registry_risk_reasons

MAX_RESULTS = 10
SITE_LOGICAL_REQUEST_CEILING = 4
SEARCH_LOGICAL_REQUESTS = 1
BOUNDED_HOMEPAGE_LOGICAL_REQUESTS = 2


@dataclass(frozen=True)
class ProviderPrerequisites:
    terms_clearance: bool = False
    benchmark_disclosure_permission: bool = False
    api_key_in_evaluator: bool = False
    zero_dollar_plan_confirmed: bool = False
    available_monthly_credits_confirmed: bool = False
    bounded_runtime_confirmed: bool = False

    @property
    def all_met(self) -> bool:
        return all((
            self.terms_clearance, self.benchmark_disclosure_permission,
            self.api_key_in_evaluator, self.zero_dollar_plan_confirmed,
            self.available_monthly_credits_confirmed, self.bounded_runtime_confirmed,
        ))


def tavily_basic_search_body(profile: dict[str, Any]) -> dict[str, Any]:
    """One free-credit search with zero provider-generated answer or raw content."""
    return {
        "query": build_company_search_query(profile),
        "topic": "general",
        "search_depth": "basic",
        "max_results": MAX_RESULTS,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
        "auto_parameters": False,
    }


def normalize_tavily_results(
    payload: dict[str, Any], *, query: str
) -> list[dict[str, Any]]:
    """Transient minimal fields only; no scores, answer, images or raw content."""
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    parsed: list[dict[str, Any]] = []
    for rank, item in enumerate(results[:MAX_RESULTS], start=1):
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        parsed.append({
            "url": url.strip(),
            "title": str(item.get("title") or "")[:500],
            "snippet": str(item.get("content") or "")[:1000],
            "rank": rank,
            "provider": "tavily_basic",
            "query": query,
        })
    return parsed


def _matching_independent_page(
    candidate_url: str, website: dict[str, Any]
) -> bool:
    """Fail closed unless fixture ties page's REQUESTED URL to selected domain."""
    requested = (website.get("value") or {}).get("requested_url")
    a = normalize_homepage(candidate_url)
    b = normalize_homepage(requested)
    if not a or not b:
        return False
    a_parts, b_parts = urlsplit(a), urlsplit(b)
    return (
        a_parts.scheme == b_parts.scheme
        and a_parts.netloc.casefold() == b_parts.netloc.casefold()
        and a_parts.path.rstrip("/") == b_parts.path.rstrip("/")
        and a_parts.query == b_parts.query
    )


def offline_screen(
    profile: dict[str, Any],
    payload: dict[str, Any],
    independently_fetched_website: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate synthetic/previously retained page proof without publishing data.

    Returns only aggregate-safe audit flags. Never returns provider titles,
    snippets, query text, rank, raw content or a company claim.
    No production logic invokes this function.
    """
    result = {
        "screen": "m23_tavily_offline_fixture_only",
        "candidate_nominated": False,
        "independent_page_supplied": bool(independently_fetched_website),
        "independent_exact_site_eligible": False,
        "published_claims": 0,
        "provider_requests_executed": 0,
        "network_requests_executed": 0,
        "site_logical_requests_worst_case": 0,
        "status": "abstained",
    }
    if str(profile.get("website") or "").strip():
        result["status"] = "existing_registry_site_seed"
        return result
    body = tavily_basic_search_body(profile)
    parsed = normalize_tavily_results(payload, query=body["query"])
    nominated = choose_search_candidate(profile, parsed).get("selected")
    result["site_logical_requests_worst_case"] = SEARCH_LOGICAL_REQUESTS
    if not nominated:
        result["status"] = "no_qualifying_search_candidate"
        return result
    result["candidate_nominated"] = True
    result["site_logical_requests_worst_case"] = (
        SEARCH_LOGICAL_REQUESTS + BOUNDED_HOMEPAGE_LOGICAL_REQUESTS
    )
    assert result["site_logical_requests_worst_case"] <= SITE_LOGICAL_REQUEST_CEILING
    if independently_fetched_website is None:
        result["status"] = "independent_fetch_required"
        return result
    if not _matching_independent_page(
        str(nominated["url"]), independently_fetched_website
    ):
        result["status"] = "independent_page_provenance_mismatch"
        return result
    copy = deepcopy(independently_fetched_website)
    gated = apply_website_identity_gate(profile, copy)
    website = gated["website"]
    assessment = qualify_search_discovered_website(
        profile, website, gated.get("assessment")
    )
    if _has_conflicting_explicit_org_number(profile, website):
        result["status"] = "conflicting_organisation_number"
        return result
    if registry_risk_reasons(profile, website):
        result["status"] = "registry_collision_risk"
        return result
    if (
        website.get("status") != "available"
        or not assessment
        or not assessment.get("publishable")
    ):
        result["status"] = "page_identity_not_proven"
        return result
    result["independent_exact_site_eligible"] = True
    result["status"] = "eligible_for_future_manual_review_only"
    return result
