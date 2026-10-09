"""M25 bounded Tavily transport building block — NOT connected to V8 or pilot CLI.

Permitted use was discussed by Tavily Support on 2026-10-08, but account/key,
remaining free credits, and the evaluator's execution environment are not yet
configured. Merely importing this module NEVER starts network traffic.

Transport function MUST be invoked by a separately reviewed, explicitly
activated pilot runner; none is supplied here. Search data is transient
nomination material, never publishable company evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import urllib.error
import urllib.request
from typing import Any, Protocol

from .tavily_offline_candidate import tavily_basic_search_body

TAVILY_SEARCH_ENDPOINT = "https://api.tavily.com/search"
MAX_RESPONSE_BYTES = 524_288
MAX_TIMEOUT_SECONDS = 8.0
MAX_SITE_LOGICAL_REQUESTS = 4
SEARCH_LOGICAL_REQUEST_COST = 1
HOMEPAGE_ROBOTS_PLUS_GET_LOGICAL_COST = 2
CHALLENGE_REDIRECT_CHARGE_MULTIPLIER = 2


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Fail on all redirects, including a cross-origin auth-header transfer."""
    def redirect_request(self, req: Any, fp: Any, code: int,
                         msg: str, headers: Any, newurl: str) -> None:
        return None


class Opener(Protocol):
    def open(self, req: urllib.request.Request, timeout: float) -> Any: ...


@dataclass(frozen=True)
class SearchResult:
    status: str
    logical_requests_charged: int
    conservative_challenge_charge: int
    payload: dict[str, Any] | None = None

    def audit(self) -> dict[str, Any]:
        """No provider result text, query, auth secret, or company identity."""
        return {
            "status": self.status,
            "logical_requests_charged": self.logical_requests_charged,
            "conservative_challenge_charge": self.conservative_challenge_charge,
            "payload_persisted": False,
            "published_company_claims": 0,
        }


class SiteSlotBudget:
    """Conservative accounting for REPLACEMENT (not added) website actions.

    Does not prove the production runner obeys this budget; production
    integration must wire every attempted HTTP request into exact accounting.
    """
    def __init__(self, capacity: int = MAX_SITE_LOGICAL_REQUESTS):
        if capacity != MAX_SITE_LOGICAL_REQUESTS:
            raise ValueError("Production site allocation must remain four")
        self.used = 0
        self.search_reserved = False

    def reserve_search(self) -> None:
        if self.search_reserved:
            raise ValueError("Exactly one provider search is allowed per eligible company")
        self._reserve(SEARCH_LOGICAL_REQUEST_COST)
        self.search_reserved = True

    def reserve_homepage(self) -> None:
        self._reserve(HOMEPAGE_ROBOTS_PLUS_GET_LOGICAL_COST)

    def _reserve(self, amount: int) -> None:
        if self.used + amount > MAX_SITE_LOGICAL_REQUESTS:
            raise ValueError("Search/site request would exceed V8 four-slot ceiling")
        self.used += amount

    @property
    def conservative_charge(self) -> int:
        return self.used * CHALLENGE_REDIRECT_CHARGE_MULTIPLIER


def _safe_search_body(profile: dict[str, Any]) -> dict[str, Any]:
    org = profile.get("organisation_number")
    if (not isinstance(org, str) or len(org) != 9 or
            not org.isascii() or not org.isdecimal() or
            not str(profile.get("name") or "").strip() or
            not str(profile.get("municipality") or "").strip()):
        raise ValueError("Search requires exact nine-digit orgnr, legal name and municipality")
    body = tavily_basic_search_body(profile)
    if (
        body.get("search_depth") != "basic"
        or body.get("auto_parameters") is not False
        or body.get("include_answer") is not False
        or body.get("include_raw_content") is not False
        or body.get("include_images") is not False
        or body.get("max_results", 0) > 10
    ):
        raise ValueError("Search must remain a one-credit basic result nomination")
    return body


def execute_bounded_search(
    profile: dict[str, Any],
    *,
    api_key: str,
    timeout_seconds: float = 6.0,
    opener: Opener | None = None,
) -> SearchResult:
    """Perform at most ONE HTTP POST, only if explicitly called with a key.

    Not used by production/CI. No environment auto-discovery, keyless fallback,
    external redirects, raw API errors, retries, LLM answer or raw page content.
    Consume a charge even for a 429, 5xx or timeout once network is attempted.
    """
    body = _safe_search_body(profile)
    if not isinstance(api_key, str) or not api_key.strip():
        return SearchResult("no_key_no_request", 0, 0)
    if not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise ValueError("Timeout must be positive and at most eight seconds")
    encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        TAVILY_SEARCH_ENDPOINT,
        data=encoded,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer " + api_key.strip(),
            "User-Agent": "Signalpost-M25-consumed-development-only",
        },
    )
    # Disallow implicit system proxies and redirect-following. The exact
    # endpoint is fixed; never use an untrusted search result as an API URL.
    transport = opener if opener is not None else urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect()
    )
    def fail(status: str) -> SearchResult:
        return SearchResult(status, 1, 2)

    try:
        with transport.open(request, timeout=timeout_seconds) as response:
            # A mock or unusual opener MUST NOT launder a redirected response.
            if response.geturl() != TAVILY_SEARCH_ENDPOINT:
                return fail("unexpected_response_origin")
            data = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        code = exc.code
        if code in (301, 302, 303, 307, 308):
            return fail("redirect_blocked")
        if code in (401, 403):
            return fail("invalid_or_forbidden_key")
        if code == 429:
            return fail("rate_limited_or_out_of_credits")
        return fail("provider_http_error")
    except (urllib.error.URLError, TimeoutError, OSError):
        return fail("transport_error")
    except Exception:
        # No provider error bodies or exception strings can leak into reports.
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
