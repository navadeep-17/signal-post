from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable

from .v9_discovery import nominate_v9_candidate_urls
from .v9_provider_gate import ProviderContract, evaluate_provider_contract

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-6-luna"
WEB_SEARCH_TOOL_COST_USD = 0.01
LUNA_INPUT_USD_PER_TOKEN = 0.10 / 1_000_000
LUNA_OUTPUT_USD_PER_TOKEN = 0.50 / 1_000_000
MAX_WEB_SEARCH_CALLS = 1
MAX_CANDIDATES = 1


@dataclass(frozen=True)
class OpenAIWebSearchV2Settings:
    model: str = DEFAULT_MODEL
    timeout: float = 30.0
    max_output_tokens: int = 96

    def __post_init__(self) -> None:
        if self.model != DEFAULT_MODEL:
            raise ValueError(f"V9 provider experiment is pinned to {DEFAULT_MODEL}")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_output_tokens < 16:
            raise ValueError("max_output_tokens must be at least 16")


def _compact_profile(profile: dict[str, Any]) -> dict[str, str]:
    org = "".join(ch for ch in str(profile.get("organisation_number") or "") if ch.isdigit())
    name = " ".join(str(profile.get("name") or "").split())
    municipality = " ".join(str(profile.get("municipality") or "").split())
    if len(org) != 9 or not name:
        raise ValueError("OpenAI web-search discovery requires legal name and 9-digit organisation number")
    return {
        "organisation_number": org,
        "legal_name": name,
        "municipality": municipality,
    }


def build_request_body(
    profile: dict[str, Any],
    *,
    settings: OpenAIWebSearchV2Settings | None = None,
) -> dict[str, Any]:
    """Build one bounded provider request whose *tool results*, not model prose, are consumed.

    The response text is deliberately irrelevant to candidate nomination. Signalpost asks
    the API to include raw web-search results and complete search sources, then deterministically
    extracts URLs/result metadata from the web_search_call item only.
    """
    settings = settings or OpenAIWebSearchV2Settings()
    item = _compact_profile(profile)
    location = f" Municipality: {item['municipality']}." if item["municipality"] else ""
    prompt = (
        "Search the public web for the official first-party website of this exact Norwegian "
        "legal entity. Search primarily with the exact organisation number, then legal name. "
        "Prefer a company-owned homepage or a dedicated official hosted company page. "
        "Avoid directories, registries, social networks, marketplaces, review sites, and "
        "parent/group/brand pages that do not identify the exact legal entity. "
        "Use one web search only. Your prose answer will be ignored; the application consumes "
        "only the web_search tool's returned results/sources. "
        f"Organisation number: {item['organisation_number']}. "
        f"Legal name: {item['legal_name']}.{location}"
    )
    return {
        "model": settings.model,
        "store": False,
        "reasoning": {"effort": "none"},
        "tools": [
            {
                "type": "web_search",
                "search_context_size": "low",
                "external_web_access": True,
                "user_location": {
                    "type": "approximate",
                    "country": "NO",
                },
            }
        ],
        "tool_choice": "required",
        "max_tool_calls": MAX_WEB_SEARCH_CALLS,
        "parallel_tool_calls": False,
        "max_output_tokens": settings.max_output_tokens,
        "include": [
            "web_search_call.results",
            "web_search_call.action.sources",
        ],
        "input": [
            {
                "role": "system",
                "content": (
                    "Perform exactly one bounded web search. Do not decide publication identity; "
                    "Signalpost will independently fetch and verify any nominated URL."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }


def _web_search_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in response.get("output") or []
        if isinstance(item, dict) and item.get("type") == "web_search_call"
    ]


def _candidate_from_mapping(
    value: dict[str, Any],
    *,
    rank: int,
    provider: str,
    query: str,
) -> dict[str, Any] | None:
    raw_url = value.get("url") or value.get("link")
    if not raw_url:
        return None
    title = value.get("title") or value.get("name") or ""
    snippet = (
        value.get("snippet")
        or value.get("description")
        or value.get("text")
        or value.get("content")
        or ""
    )
    if not isinstance(snippet, str):
        snippet = ""
    return {
        "url": str(raw_url),
        "title": str(title or ""),
        "snippet": snippet,
        "rank": rank,
        "provider": provider,
        "query": query,
    }


def _walk_result_mappings(value: Any) -> Iterable[dict[str, Any]]:
    """Yield URL-bearing mappings only from the explicit web-search results payload."""
    if isinstance(value, dict):
        if value.get("url") or value.get("link"):
            yield value
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from _walk_result_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_result_mappings(child)


def extract_search_results(response: dict[str, Any]) -> dict[str, Any]:
    """Normalize only provider web-search call data into transient scorer records.

    Assistant message text, citations, annotations, reasoning, and generated URL strings are
    never inspected. The only accepted URL origins are web_search_call.results or
    web_search_call.action.sources.
    """
    items = _web_search_items(response)
    if len(items) != MAX_WEB_SEARCH_CALLS:
        return {
            "status": "tool_call_bound_violation",
            "results": [],
            "web_search_calls": len(items),
            "query_sha256": [],
        }

    item = items[0]
    action = item.get("action") or {}
    if not isinstance(action, dict) or action.get("type") != "search":
        return {
            "status": "non_search_tool_action",
            "results": [],
            "web_search_calls": len(items),
            "query_sha256": [],
        }

    queries: list[str] = []
    raw_queries = action.get("queries")
    if isinstance(raw_queries, list):
        queries.extend(str(value) for value in raw_queries if str(value or "").strip())
    legacy_query = str(action.get("query") or "").strip()
    if legacy_query:
        queries.append(legacy_query)
    query_hashes = [
        hashlib.sha256(query.encode("utf-8")).hexdigest()
        for query in dict.fromkeys(queries)
    ]
    transient_query = queries[0] if queries else ""

    normalized: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    rank = 0

    # Prefer raw returned search results because title/snippet are useful *transient*
    # nomination signals. They are discarded after v9_discovery selects URLs.
    for mapping in _walk_result_mappings(item.get("results")):
        candidate = _candidate_from_mapping(
            mapping,
            rank=rank + 1,
            provider="openai_responses_web_search",
            query=transient_query,
        )
        if not candidate:
            continue
        url = candidate["url"]
        if url in seen_urls:
            continue
        rank += 1
        candidate["rank"] = rank
        normalized.append(candidate)
        seen_urls.add(url)

    # Complete source lists are a URL-only fallback. They can be considered by the
    # existing transient scorer but carry no synthetic title/snippet evidence.
    sources = action.get("sources") or []
    if isinstance(sources, list):
        for source in sources:
            if not isinstance(source, dict):
                continue
            candidate = _candidate_from_mapping(
                source,
                rank=rank + 1,
                provider="openai_responses_web_search_source",
                query=transient_query,
            )
            if not candidate:
                continue
            url = candidate["url"]
            if url in seen_urls:
                continue
            rank += 1
            candidate["rank"] = rank
            normalized.append(candidate)
            seen_urls.add(url)

    return {
        "status": "results_found" if normalized else "no_results",
        "results": normalized,
        "web_search_calls": len(items),
        "query_sha256": query_hashes,
    }


def estimate_cost_usd(response: dict[str, Any]) -> dict[str, Any]:
    """Conservative standard-processing estimate using current GPT-6 Luna list rates."""
    usage = response.get("usage") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    web_search_calls = len(_web_search_items(response))
    estimate = (
        web_search_calls * WEB_SEARCH_TOOL_COST_USD
        + input_tokens * LUNA_INPUT_USD_PER_TOKEN
        + output_tokens * LUNA_OUTPUT_USD_PER_TOKEN
    )
    return {
        "web_search_calls": web_search_calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": round(estimate, 6),
        "pricing_assumption": {
            "web_search_usd_per_call": WEB_SEARCH_TOOL_COST_USD,
            "model": DEFAULT_MODEL,
            "input_usd_per_million_tokens": 0.10,
            "output_usd_per_million_tokens": 0.50,
            "processing": "standard",
        },
    }


def parse_response(
    profile: dict[str, Any],
    response: dict[str, Any],
) -> dict[str, Any]:
    """Turn actual web-search tool data into untrusted V9 URL nominations."""
    item = _compact_profile(profile)
    extracted = extract_search_results(response)
    cost = estimate_cost_usd(response)
    if extracted["status"] not in {"results_found", "no_results"}:
        return {
            "organisation_number": item["organisation_number"],
            "status": extracted["status"],
            "candidate_urls": [],
            "candidate_count": 0,
            "publication_authorized": False,
            "provider_result_text_retained": False,
            "provider_message_text_consumed": False,
            "provider_response_id": response.get("id"),
            "query_sha256": extracted["query_sha256"],
            "cost": cost,
        }

    decision = nominate_v9_candidate_urls(
        profile,
        extracted["results"],
        max_candidates=MAX_CANDIDATES,
    )
    return {
        "organisation_number": item["organisation_number"],
        "status": "candidates_found" if decision["candidate_urls"] else "no_candidate",
        "candidate_urls": decision["candidate_urls"],
        "candidate_count": decision["candidate_count"],
        "publication_authorized": False,
        "provider_result_text_retained": False,
        "provider_message_text_consumed": False,
        "provider_response_id": response.get("id"),
        "query_sha256": extracted["query_sha256"],
        "decisions": decision["decisions"],
        "cost": cost,
    }


def search_candidate_urls(
    profile: dict[str, Any],
    *,
    api_key: str | None = None,
    settings: OpenAIWebSearchV2Settings | None = None,
) -> dict[str, Any]:
    """Execute one provider search request.

    This remains experiment-only. It cannot authorize publication and returns no model prose,
    search snippet, title, or provider-generated reasoning. Every returned URL still requires
    a fresh Signalpost page fetch plus the existing exact-company verifier.
    """
    settings = settings or OpenAIWebSearchV2Settings()
    item = _compact_profile(profile)
    key = str(api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        return {
            "organisation_number": item["organisation_number"],
            "status": "provider_key_unavailable",
            "candidate_urls": [],
            "candidate_count": 0,
            "publication_authorized": False,
            "provider_result_text_retained": False,
            "provider_message_text_consumed": False,
        }

    encoded = json.dumps(
        build_request_body(profile, settings=settings),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=encoded,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "signal-post-v9-m13-websearch/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.timeout) as response:
            raw = response.read()
        payload = json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {
            "organisation_number": item["organisation_number"],
            "status": f"provider_http_{exc.code}",
            "candidate_urls": [],
            "candidate_count": 0,
            "publication_authorized": False,
            "provider_result_text_retained": False,
            "provider_message_text_consumed": False,
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "organisation_number": item["organisation_number"],
            "status": "provider_error",
            "error_type": type(exc).__name__,
            "candidate_urls": [],
            "candidate_count": 0,
            "publication_authorized": False,
            "provider_result_text_retained": False,
            "provider_message_text_consumed": False,
        }

    return parse_response(profile, payload)


def provider_readiness(
    *,
    max_searches: int,
    evaluator_key_available: bool,
    rights_status: str,
    challenge_cost_budget_usd: float,
    project_third_party_budget_usd: float = 0.0,
) -> dict[str, Any]:
    """Apply the existing V9 provider gate without self-approving rights or credentials."""
    if project_third_party_budget_usd < 0:
        raise ValueError("project_third_party_budget_usd cannot be negative")
    effective_budget = min(challenge_cost_budget_usd, project_third_party_budget_usd)
    contract = ProviderContract(
        name="openai_responses_web_search_v2",
        evaluator_reproducible=evaluator_key_available,
        rights_status=str(rights_status or "").strip().casefold(),
        key_available_to_evaluator=evaluator_key_available,
        cost_per_search_usd=WEB_SEARCH_TOOL_COST_USD,
        max_searches=max_searches,
    )
    decision = evaluate_provider_contract(
        contract,
        challenge_cost_budget_usd=effective_budget,
    )
    decision["challenge_cost_budget_usd"] = challenge_cost_budget_usd
    decision["project_third_party_budget_usd"] = project_third_party_budget_usd
    decision["effective_experiment_budget_usd"] = effective_budget
    if project_third_party_budget_usd <= 0 and "project_zero_cost_policy" not in decision["reasons"]:
        decision["reasons"].append("project_zero_cost_policy")
        decision["allowed_for_live_v9_experiment"] = False
    return decision
