from __future__ import annotations

import re
import unicodedata
import urllib.parse
from typing import Any

from .website import normalize_homepage


BLOCKED_DISCOVERY_HOSTS = {
    "proff.no", "purehelp.no", "1881.no", "gulesider.no", "firmalisten.no", "companywall.no",
    "firmadatabasen.no", "sokfirma.no", "yra.no", "northdata.com", "nor47business.com",
    "linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com", "youtube.com", "tiktok.com",
}
GENERIC_NAME_TOKENS = {"as", "asa", "ans", "da", "enk", "sa", "nuf", "company", "norge", "norway", "gruppen", "group"}


def build_company_search_query(profile: dict[str, Any]) -> str:
    name = " ".join(str(profile.get("name") or "").split())
    org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    municipality = " ".join(str(profile.get("municipality") or "").split())
    if not name or not org:
        raise ValueError("Company discovery requires a legal name and organisation number")
    location = f" {municipality}" if municipality else ""
    return f'"{name}" {org}{location}'


def _normalized_result(
    *,
    url: Any,
    title: Any,
    snippet: Any,
    rank: int,
    provider: str,
    query: str,
) -> dict[str, Any] | None:
    if not url:
        return None
    return {
        "url": str(url),
        "title": str(title or ""),
        "snippet": str(snippet or ""),
        "rank": rank,
        "provider": provider,
        "query": query,
    }


def parse_brave_web_results(payload: dict[str, Any], *, query: str) -> list[dict[str, Any]]:
    """Normalize Brave output for the shared transient candidate scorer.

    This parser remains for the starter's historical experiment. Standard Brave Search
    terms reviewed for this project do not currently qualify for our benchmark use.
    """
    results = (payload.get("web") or {}).get("results") or []
    parsed = []
    for rank, result in enumerate(results, start=1):
        if not isinstance(result, dict):
            continue
        item = _normalized_result(
            url=result.get("url"),
            title=result.get("title"),
            snippet=result.get("description"),
            rank=rank,
            provider="brave_search_api",
            query=query,
        )
        if item:
            parsed.append(item)
    return parsed


def parse_serpapi_web_results(payload: dict[str, Any], *, query: str) -> list[dict[str, Any]]:
    """Normalize SerpApi organic results for transient candidate selection.

    Only URL/title/snippet/rank are exposed to the in-memory scorer. Callers must not
    persist the provider title/snippet/query as company evidence; accepted candidates
    still require an independent fetch and the ordinary exact-company website gate.
    """
    results = payload.get("organic_results") or []
    parsed = []
    for fallback_rank, result in enumerate(results, start=1):
        if not isinstance(result, dict):
            continue
        try:
            rank = int(result.get("position") or fallback_rank)
        except (TypeError, ValueError):
            rank = fallback_rank
        item = _normalized_result(
            url=result.get("link"),
            title=result.get("title"),
            snippet=result.get("snippet"),
            rank=rank,
            provider="serpapi_google",
            query=query,
        )
        if item:
            parsed.append(item)
    return parsed


def _tokens(value: Any) -> list[str]:
    text = str(value or "").translate(str.maketrans({"ø": "o", "å": "a", "æ": "ae", "Ø": "O", "Å": "A", "Æ": "AE"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return [token for token in re.findall(r"[a-z0-9]+", text) if len(token) > 1]


def _distinctive_name_tokens(profile: dict[str, Any]) -> list[str]:
    return [token for token in _tokens(profile.get("name")) if token not in GENERIC_NAME_TOKENS]


def score_search_candidate(profile: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_homepage(result.get("url"))
    if not normalized:
        return {"status": "rejected", "score": 0.0, "publishable_candidate": False, "reasons": ["invalid HTTP(S) candidate URL"]}
    host = (urllib.parse.urlparse(normalized).hostname or "").casefold().removeprefix("www.")
    if any(host == blocked or host.endswith("." + blocked) for blocked in BLOCKED_DISCOVERY_HOSTS):
        return {"status": "rejected", "score": 0.0, "publishable_candidate": False, "url": normalized, "host": host, "reasons": ["directory, aggregator, or social host is not a company website candidate"]}

    name_tokens = _distinctive_name_tokens(profile)
    title_tokens = _tokens(result.get("title"))
    snippet_tokens = _tokens(result.get("snippet"))
    evidence_tokens = set(title_tokens + snippet_tokens + _tokens(host))
    host_compact = "".join(_tokens(host))
    name_compact = "".join(name_tokens)
    org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    evidence_digits = re.sub(r"\D", "", f"{result.get('title', '')} {result.get('snippet', '')}")
    municipality_tokens = set(_tokens(profile.get("municipality")))

    org_match = bool(org and org in evidence_digits)
    all_name_tokens = bool(name_tokens and set(name_tokens).issubset(evidence_tokens))
    all_name_tokens_in_title = bool(name_tokens and set(name_tokens).issubset(set(title_tokens)))
    name_in_host = bool(name_compact and name_compact in host_compact)
    municipality_match = bool(municipality_tokens and municipality_tokens <= set(snippet_tokens))
    score = 0.0
    reasons = []
    if org_match:
        score += 0.75
        reasons.append("exact organisation number appears in result evidence")
    if all_name_tokens_in_title:
        score += 0.45
        reasons.append("all distinctive legal-name tokens appear in the result title")
    elif all_name_tokens:
        score += 0.25
        reasons.append("all distinctive legal-name tokens appear across result evidence")
    if name_in_host:
        score += 0.3
        reasons.append("normalized legal name appears in candidate hostname")
    if municipality_match:
        score += 0.1
        reasons.append("registry municipality appears in result snippet")
    score = min(score, 1.0)

    # This is only a CRAWL gate, never a publication gate. Exact org-number + full
    # legal-name result evidence may nominate an acronym/brand domain for independent
    # crawling even when the legal name is not present in the hostname. Directories and
    # social hosts are blocked above; publication still requires independent page proof.
    strong_exact_result = org_match and all_name_tokens_in_title
    strong_name_domain_result = name_in_host and (org_match or all_name_tokens_in_title)
    publishable_candidate = score >= 0.75 and (strong_exact_result or strong_name_domain_result)
    return {
        "status": "accepted_for_crawl" if publishable_candidate else "review" if score >= 0.6 else "rejected",
        "score": score,
        "publishable_candidate": publishable_candidate,
        "url": normalized,
        "host": host,
        "rank": result.get("rank"),
        "provider": result.get("provider"),
        "query": result.get("query"),
        "org_match": org_match,
        "full_name_title_match": all_name_tokens_in_title,
        "host_name_match": name_in_host,
        "municipality_match": municipality_match,
        "reasons": reasons or ["insufficient exact-entity evidence"],
        "method": "deterministic_search_candidate_identity_v2",
    }


def choose_search_candidate(profile: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    assessed = [score_search_candidate(profile, result) for result in results]
    # Search rank is not an identity signal. When scores tie, prefer a legal-name-aligned
    # hostname before the provider's rank; acronym domains remain eligible when they are
    # the strongest exact-org/full-name result available.
    assessed.sort(
        key=lambda item: (
            -item.get("score", 0.0),
            -int(bool(item.get("host_name_match"))),
            item.get("rank") or 10_000,
            item.get("url") or "",
        )
    )
    accepted = [item for item in assessed if item.get("publishable_candidate")]
    return {
        "selected": accepted[0] if accepted else None,
        "candidates": assessed,
        "abstained": not accepted,
        "policy": "A search result is only a crawl candidate. Publication still requires fetched-page exact-entity verification.",
    }


def _website_page_parts(website: dict[str, Any]) -> list[str]:
    """Collect independently fetched page text while excluding URL/hostname strings."""
    value = website.get("value") or {}
    parts: list[Any] = [
        value.get("title"),
        value.get("description"),
        value.get("identity_text_excerpt"),
        value.get("main_text_excerpt"),
    ]
    for structured in value.get("structured_organisations") or []:
        if isinstance(structured, dict):
            parts.extend(structured.get(key) for key in ("name", "legalName", "alternateName"))
    rendered = value.get("js_fallback") or {}
    parts.extend([rendered.get("title"), rendered.get("main_text_excerpt")])
    for page in value.get("pages") or []:
        if isinstance(page, dict):
            parts.extend([page.get("title"), page.get("identity_text_excerpt"), page.get("main_text_excerpt")])
    return [str(part) for part in parts if str(part or "").strip()]


def qualify_search_discovered_website(
    profile: dict[str, Any],
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Harden publication of a search-discovered domain using page evidence only.

    Search-result snippets, ranking and hostname similarity are useful only for deciding
    what to crawl. Publication requires the independent destination page to prove the
    legal entity. The exact organisation number is strongest. Otherwise require the full
    distinctive legal name plus either registry municipality corroboration or an exact
    company-name hostname. This intentionally prefers false negatives to namesakes,
    parent-company pages and directories.
    """
    if not assessment or not assessment.get("publishable") or website.get("status") != "available":
        return assessment

    parts = _website_page_parts(website)
    org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    if len(org) == 9 and any(org in re.sub(r"\D", "", part) for part in parts):
        return {
            **assessment,
            "score": 1.0,
            "reasons": [*list(assessment.get("reasons") or []), "H1b independently fetched page contains exact organisation number"],
            "method": "search_discovered_page_identity_guard_v1",
        }

    name_tokens = _distinctive_name_tokens(profile)
    full_name_on_page = bool(name_tokens and any(set(name_tokens).issubset(set(_tokens(part))) for part in parts))
    municipality_tokens = set(_tokens(profile.get("municipality")))
    municipality_on_page = bool(municipality_tokens and any(municipality_tokens <= set(_tokens(part)) for part in parts))

    final_url = (website.get("value") or {}).get("final_url") or website.get("source_url") or ""
    host = (urllib.parse.urlparse(final_url).hostname or "").casefold().removeprefix("www.")
    first_label = host.split(".", 1)[0]
    host_name_compact = "".join(_tokens(first_label))
    legal_name_compact = "".join(name_tokens)
    exact_name_host = bool(legal_name_compact and host_name_compact == legal_name_compact)

    if full_name_on_page and (municipality_on_page or exact_name_host):
        return {
            **assessment,
            "score": min(0.98, max(float(assessment.get("score") or 0.9), 0.95)),
            "reasons": [
                *list(assessment.get("reasons") or []),
                "H1b independently fetched page contains complete legal name with registry-location or exact-domain corroboration",
            ],
            "method": "search_discovered_page_identity_guard_v1",
        }

    return {
        **assessment,
        "status": "review",
        "score": min(float(assessment.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [
            *list(assessment.get("reasons") or []),
            "H1b independent page lacks exact organisation number or complete legal-name corroboration",
        ],
        "method": "search_discovered_page_identity_guard_v1",
    }
