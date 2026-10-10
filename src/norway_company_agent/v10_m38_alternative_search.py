"""M38 experimental single Basic Search transport for ONE frozen query hypothesis.

Only a separately approved, explicitly activated consumed-development workflow
may call this function. No import side effects, environment secrets, retries,
redirects, responses retained to disk, second/fallback searches or LLM answers.
Never wired to qualified V8 or the challenge evaluator.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .tavily_bounded_transport import (
    MAX_RESPONSE_BYTES, MAX_TIMEOUT_SECONDS, NoRedirect, Opener, SearchResult,
    TAVILY_SEARCH_ENDPOINT, _safe_search_body,
)
from .v10_m37_offline_query_design import build_offline_one_query

FROZEN_VARIANT = "legal_name_municipality_homepage"


def _single_alternative_body(profile: dict[str, Any]) -> dict[str, Any]:
    """Clone M25's fixed Basic request options, changing ONLY the query."""
    result = build_offline_one_query(profile, variant=FROZEN_VARIANT)
    body = _safe_search_body(profile)
    assert body["search_depth"] == "basic" and body["auto_parameters"] is False
    assert body["include_answer"] is False and body["include_raw_content"] is False
    assert body["include_images"] is False and body["max_results"] <= 10
    body["query"] = result.transient_query
    return body


def execute_bounded_alternative(
    profile: dict[str, Any], *,
    api_key: str,
    timeout_seconds: float = 8.0,
    opener: Opener | None = None,
) -> SearchResult:
    """Exactly one fixed-endpoint POST, no redirects/retries/fallbacks.

    The result is transient; a returned URL is NOT a verified company website.
    """
    body = _single_alternative_body(profile)
    if not isinstance(api_key, str) or not api_key.strip():
        return SearchResult("no_key_no_request", 0, 0)
    if not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise ValueError("Time must be within the eight-second limit")
    encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        TAVILY_SEARCH_ENDPOINT,
        data=encoded,
        method="POST",
        headers={
            "Content-Type": "application/json", "Accept": "application/json",
            "Authorization": "Bearer " + api_key.strip(),
            "User-Agent": "Signalpost-M38-consumed-development-only",
        },
    )
    transport = opener if opener is not None else urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect()
    )
    def fail(status: str) -> SearchResult:
        return SearchResult(status, 1, 2)

    try:
        with transport.open(request, timeout=timeout_seconds) as response:
            if response.geturl() != TAVILY_SEARCH_ENDPOINT:
                return fail("unexpected_response_origin")
            data = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            return fail("redirect_blocked")
        if exc.code in (401, 403):
            return fail("invalid_or_forbidden_key")
        if exc.code == 429:
            return fail("rate_limited_or_out_of_credits")
        return fail("provider_http_error")
    except (urllib.error.URLError, TimeoutError, OSError):
        return fail("transport_error")
    except Exception:
        return fail("transport_error")
    if len(data) > MAX_RESPONSE_BYTES:
        return fail("oversized_provider_response")
    try:
        payload = json.loads(data)
    except (UnicodeError, ValueError):
        return fail("invalid_json_response")
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        return fail("invalid_search_response")
    return SearchResult("ok_transient_candidates_only", 1, 2, payload)
