from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable

from .discovery import BLOCKED_DISCOVERY_HOSTS, score_search_candidate
from .website import _registered_domain, normalize_homepage

# Additional obvious non-first-party surfaces that should never be nominated as an
# official company website. This list is intentionally small and generic; it is not a
# substitute for independent page verification.
V9_BLOCKED_DISCOVERY_HOSTS = {
    *BLOCKED_DISCOVERY_HOSTS,
    "google.com",
    "google.no",
    "maps.google.com",
    "yelp.com",
    "tripadvisor.com",
    "finn.no",
    "facebook.net",
}

MAX_V9_CANDIDATES = 3
MIN_V9_NOMINATION_SCORE = 0.35


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _spaced_org_number(org: str) -> str:
    if len(org) != 9:
        return org
    return f"{org[:3]} {org[3:6]} {org[6:]}"


def build_v9_query_plan(profile: dict[str, Any]) -> list[dict[str, str]]:
    """Return the bounded transient query plan described by the V9 handoff.

    Query text is provider input only. Callers may hash/measure it operationally, but it
    must never become company publication evidence.
    """
    name = " ".join(str(profile.get("name") or "").split())
    org = _digits(profile.get("organisation_number"))
    if not name or len(org) != 9:
        raise ValueError("V9 discovery requires legal name and 9-digit organisation number")

    spaced = _spaced_org_number(org)
    queries = [
        f'"{org}"',
        f'"{spaced}"',
        f'"Org.nr. {spaced}"',
        f'"{name}" "{org}"',
        f'"{name}" "org nr"',
    ]
    return [
        {
            "query": query,
            "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        }
        for query in queries
    ]


def _host_is_blocked(url: str) -> bool:
    normalized = normalize_homepage(url)
    if not normalized:
        return True
    from urllib.parse import urlparse

    host = (urlparse(normalized).hostname or "").casefold().removeprefix("www.")
    return any(host == blocked or host.endswith("." + blocked) for blocked in V9_BLOCKED_DISCOVERY_HOSTS)


def _safe_registered_domain(url: str) -> str:
    normalized = normalize_homepage(url)
    if not normalized:
        return ""
    return str(_registered_domain(normalized) or "").casefold()


def _sanitize_result_for_scoring(result: dict[str, Any]) -> dict[str, Any]:
    """Keep only transient fields used by the existing crawl-candidate scorer."""
    return {
        "url": result.get("url"),
        "title": result.get("title"),
        "snippet": result.get("snippet"),
        "rank": result.get("rank"),
        "provider": result.get("provider"),
        "query": result.get("query"),
    }


def _v9_nomination_decision(scored: dict[str, Any]) -> tuple[bool, str]:
    """Widen *nomination* recall without widening publication identity.

    V8's older search scorer intentionally used a relatively strict crawl gate. V9 has a
    different contract: provider output is only an untrusted URL nomination and every
    candidate must still survive a fresh independent fetch plus the unchanged exact-company
    verifier. Therefore full legal-name result evidence, exact organisation-number evidence,
    or a modest combined transient score may justify spending one bounded verification fetch
    even when the provider result is not strong enough to resemble publication evidence.
    """
    if scored.get("publishable_candidate") and scored.get("status") == "accepted_for_crawl":
        return True, "legacy_strong_crawl_gate"
    if scored.get("org_match"):
        return True, "exact_org_in_transient_result"
    if scored.get("full_name_title_match"):
        return True, "full_legal_name_in_transient_title"
    if float(scored.get("score") or 0.0) >= MIN_V9_NOMINATION_SCORE:
        return True, "bounded_transient_score"
    return False, "insufficient_nomination_evidence"


def nominate_v9_candidate_urls(
    profile: dict[str, Any],
    results: Iterable[dict[str, Any]],
    *,
    max_candidates: int = MAX_V9_CANDIDATES,
) -> dict[str, Any]:
    """Return at most three untrusted URLs for independent fetch.

    Provider titles/snippets/query text may influence transient ranking, but none of that
    text is returned or allowed to authorize publication. V9 intentionally permits a
    broader *nomination* gate than the historical H1b crawl gate because independent
    fetched-page identity remains the only publication authority.

    Candidates are de-duplicated by registered domain. Social, directory, marketplace,
    review and other obvious non-first-party hosts are rejected before nomination.
    """
    if max_candidates < 1 or max_candidates > MAX_V9_CANDIDATES:
        raise ValueError(f"max_candidates must be between 1 and {MAX_V9_CANDIDATES}")

    assessed: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for raw in results:
        if not isinstance(raw, dict):
            continue
        raw_url = str(raw.get("url") or "").strip()
        normalized = normalize_homepage(raw_url)
        registered_domain = _safe_registered_domain(raw_url)
        if not normalized or not registered_domain:
            rejected.append(
                {
                    "url": raw_url,
                    "registered_domain": registered_domain,
                    "reason": "invalid_http_candidate",
                }
            )
            continue
        if _host_is_blocked(normalized):
            rejected.append(
                {
                    "url": normalized,
                    "registered_domain": registered_domain,
                    "reason": "blocked_non_first_party_host",
                }
            )
            continue

        scored = score_search_candidate(profile, _sanitize_result_for_scoring(raw))
        accepted_for_fetch, nomination_reason = _v9_nomination_decision(scored)
        item = {
            "url": normalized,
            "registered_domain": registered_domain,
            "score": float(scored.get("score") or 0.0),
            "host_name_match": bool(scored.get("host_name_match")),
            "rank": scored.get("rank"),
            "accepted_for_independent_fetch": accepted_for_fetch,
            "nomination_reason": nomination_reason,
        }
        assessed.append(item)

    assessed.sort(
        key=lambda item: (
            -float(item.get("score") or 0.0),
            -int(bool(item.get("host_name_match"))),
            item.get("rank") if isinstance(item.get("rank"), int) else 10_000,
            item.get("url") or "",
        )
    )

    candidate_urls: list[str] = []
    seen_domains: set[str] = set()
    decisions: list[dict[str, Any]] = []
    for item in assessed:
        domain = str(item.get("registered_domain") or "")
        if not item.get("accepted_for_independent_fetch"):
            decisions.append(
                {
                    "url": item["url"],
                    "registered_domain": domain,
                    "status": "rejected",
                    "reason": item["nomination_reason"],
                    "score": item["score"],
                }
            )
            continue
        if domain in seen_domains:
            decisions.append(
                {
                    "url": item["url"],
                    "registered_domain": domain,
                    "status": "rejected",
                    "reason": "duplicate_registered_domain",
                    "score": item["score"],
                }
            )
            continue
        if len(candidate_urls) >= max_candidates:
            decisions.append(
                {
                    "url": item["url"],
                    "registered_domain": domain,
                    "status": "rejected",
                    "reason": "candidate_limit_reached",
                    "score": item["score"],
                }
            )
            continue

        seen_domains.add(domain)
        candidate_urls.append(item["url"])
        decisions.append(
            {
                "url": item["url"],
                "registered_domain": domain,
                "status": "nominated_for_independent_fetch",
                "reason": item["nomination_reason"],
                "score": item["score"],
            }
        )

    decisions.extend(
        {
            "url": item["url"],
            "registered_domain": item["registered_domain"],
            "status": "rejected",
            "reason": item["reason"],
        }
        for item in rejected
    )

    return {
        "candidate_urls": candidate_urls,
        "candidate_count": len(candidate_urls),
        "max_candidates": max_candidates,
        "publication_authorized": False,
        "provider_result_text_retained": False,
        "contract": "untrusted_nomination_only",
        "decisions": decisions,
    }
