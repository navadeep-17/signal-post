from __future__ import annotations

import urllib.parse
from copy import deepcopy
from datetime import date, datetime, timezone
from typing import Any

from .evidence import utc_now
from .verified_site_depth import (
    CATEGORY_TERMS,
    V6D_SCHEMA,
    _detail_candidate,
    _fetch_bytes,
    _fetch_robots,
    _merge_metrics,
    _page_category,
    _same_registered_domain,
    extract_depth_facts,
    parse_feed,
    parse_page,
    parse_sitemap,
)
from .website import _registered_domain

V6D_HARDENED_SCHEMA = "signalpost.verified_site_depth.v2"
MAX_UPDATE_AGE_DAYS = 730
MAX_UPDATES_PER_COMPANY = 3
PAGE_PRIORITY = ("careers", "news", "contact", "about", "team", "locations")
BOILERPLATE_UPDATE_TITLES = {
    "hello world",
    "hello world!",
    "sample page",
    "test",
    "test post",
    "untitled",
    "uncategorized",
    "uncategorised",
    "welcome",
    "welcome!",
}


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _retrieval_date(value: Any) -> date:
    text = str(value or "").strip()
    if text:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            pass
    return datetime.now(timezone.utc).date()


def _is_recent_update(item: dict[str, Any], *, retrieved_at: str, max_age_days: int = MAX_UPDATE_AGE_DAYS) -> bool:
    published = _parse_date(item.get("published_date"))
    if published is None:
        return False
    age = (_retrieval_date(retrieved_at) - published).days
    return 0 <= age <= max_age_days


def _specific_update_title(value: Any) -> bool:
    title = " ".join(str(value or "").split()).strip()
    if not title:
        return False
    folded = title.casefold().strip(" .:-_–—")
    if folded in BOILERPLATE_UPDATE_TITLES:
        return False
    return len(title.split()) >= 2


def _activity_detail_url(url: str) -> bool:
    return _page_category(url) == "news" and _detail_candidate(url, "news")


def harden_updates(
    updates: list[dict[str, Any]],
    *,
    retrieved_at: str,
    max_age_days: int = MAX_UPDATE_AGE_DAYS,
    max_updates: int = MAX_UPDATES_PER_COMPANY,
) -> list[dict[str, Any]]:
    """Keep only recent, specific first-party update details and dedupe by URL.

    RSS/Atom is a discovery/evidence container, not a license to publish every feed item as
    company news. A feed item must itself point to a same-site news/blog/press-style detail
    URL. Metadata/detail-page evidence wins over feed evidence for the same URL.
    """
    accepted: dict[str, dict[str, Any]] = {}
    for item in updates:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not _specific_update_title(title) or not _activity_detail_url(url):
            continue
        if not _is_recent_update(item, retrieved_at=retrieved_at, max_age_days=max_age_days):
            continue
        clean_url = url.rstrip("/")
        existing = accepted.get(clean_url)
        if existing is None:
            accepted[clean_url] = dict(item)
            continue
        # Prefer the directly fetched article metadata over a feed row when both identify
        # the same detail URL. This keeps the evidence hash tied to the article when known.
        old_feed = str(existing.get("strategy") or "") == "first_party_feed_item"
        new_feed = str(item.get("strategy") or "") == "first_party_feed_item"
        if old_feed and not new_feed:
            accepted[clean_url] = dict(item)

    ordered = sorted(
        accepted.values(),
        key=lambda item: (str(item.get("published_date") or ""), str(item.get("url") or "")),
        reverse=True,
    )
    return ordered[:max_updates]


def _candidate_key(item: dict[str, Any]) -> tuple[int, int, str]:
    category = str(item.get("category") or "")
    try:
        priority = PAGE_PRIORITY.index(category)
    except ValueError:
        priority = len(PAGE_PRIORITY)
    url = str(item.get("url") or "")
    return (priority, len(urllib.parse.urlparse(url).path), url)


def _unique_candidates(rows: list[dict[str, str]], verified_url: str) -> list[dict[str, str]]:
    seen: set[str] = set()
    output: list[dict[str, str]] = []
    for row in sorted(rows, key=_candidate_key):
        url = str(row.get("url") or "")
        category = str(row.get("category") or "")
        if category not in PAGE_PRIORITY or not url or url in seen:
            continue
        if not _same_registered_domain(url, verified_url):
            continue
        seen.add(url)
        output.append(row)
    return output


def _preferred_sitemap_url(robots: Any, verified_url: str, categories: set[str]) -> str | None:
    # A declared same-domain sitemap is strongest and costs no discovery request beyond the
    # robots fetch already paid. If the homepage exposes neither careers nor news, one
    # conventional /sitemap.xml probe is allowed as a bounded fallback.
    for raw in robots.site_maps() or []:
        url = str(raw or "").strip()
        if url and _same_registered_domain(url, verified_url):
            return url
    if not ({"careers", "news"} & categories):
        parsed = urllib.parse.urlparse(verified_url)
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/sitemap.xml", "", "", ""))
    return None


def _fetch_html_candidate(
    candidate: dict[str, str],
    *,
    verified_url: str,
    robots: Any,
    timeout: float,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    raw, page_url, page_type, metrics = _fetch_bytes(
        candidate["url"],
        verified_url=verified_url,
        robots=robots,
        timeout=timeout,
        max_bytes=650_000,
        accept="text/html,application/xhtml+xml",
    )
    page = parse_page(page_url, raw, page_type) if raw is not None else None
    if page is not None:
        page["category"] = candidate["category"]
        page["candidate_source"] = candidate.get("source")
    return page, metrics


def crawl_verified_site_depth_hardened(
    profile: dict[str, Any],
    *,
    timeout: float = 6.0,
    max_section_pages: int = 4,
    max_detail_pages: int = 2,
    fetch_sitemap: bool = True,
    fetch_feed: bool = True,
    request_allowance: int = 12,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """V6d v2: maximize high-value exact-site facts under the same hard request ceiling."""
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    verified_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    verified_domain = _registered_domain(verified_url) if verified_url else ""
    total: dict[str, Any] = {
        "requests": 0,
        "bytes": 0,
        "latencies_ms": [],
        "errors": [],
        "outside_domain_rejections": 0,
        "robots_blocked": 0,
    }
    if website.get("status") != "available" or not identity.get("publishable") or not verified_url or not verified_domain:
        return {"schema": V6D_HARDENED_SCHEMA, "eligible": False, "reason": "website_not_exact_verified", "pages": [], "facts": {}}, total
    if request_allowance < 2:
        return {"schema": V6D_HARDENED_SCHEMA, "eligible": True, "reason": "insufficient_request_allowance", "pages": [], "facts": {}}, total

    robots, robot_metrics = _fetch_robots(verified_url, timeout)
    _merge_metrics(total, robot_metrics)
    if total["requests"] >= request_allowance:
        return {"schema": V6D_HARDENED_SCHEMA, "eligible": True, "reason": "request_allowance_exhausted", "pages": [], "facts": {}}, total

    raw, final_url, content_type, metrics = _fetch_bytes(
        verified_url,
        verified_url=verified_url,
        robots=robots,
        timeout=timeout,
        max_bytes=750_000,
        accept="text/html,application/xhtml+xml",
    )
    _merge_metrics(total, metrics)
    pages: list[dict[str, Any]] = []
    if raw is None:
        return {"schema": V6D_HARDENED_SCHEMA, "eligible": True, "reason": "homepage_refetch_failed", "pages": [], "facts": {}}, total
    homepage = parse_page(final_url, raw, content_type)
    if homepage is None:
        return {"schema": V6D_HARDENED_SCHEMA, "eligible": True, "reason": "homepage_not_html", "pages": [], "facts": {}}, total
    homepage["category"] = "homepage"
    pages.append(homepage)

    candidates = list(homepage.get("link_candidates") or [])
    homepage_categories = {str(item.get("category") or "") for item in candidates}
    sitemap_rows: list[dict[str, str]] = []
    sitemap_url = _preferred_sitemap_url(robots, verified_url, homepage_categories) if fetch_sitemap else None
    if sitemap_url and total["requests"] < request_allowance:
        sitemap_raw, sitemap_final, _, sitemap_metrics = _fetch_bytes(
            sitemap_url,
            verified_url=verified_url,
            robots=robots,
            timeout=timeout,
            max_bytes=1_000_000,
            accept="application/xml,text/xml,*/*;q=0.5",
        )
        _merge_metrics(total, sitemap_metrics)
        if sitemap_raw is not None:
            sitemap_rows = parse_sitemap(sitemap_raw, sitemap_url=sitemap_final, verified_url=verified_url)
            candidates.extend(sitemap_rows)

    candidates = _unique_candidates(candidates, verified_url)
    fetched_urls: set[str] = {str(homepage.get("url") or "").rstrip("/")}

    # Highest-scoring opportunity first: direct job/news detail links from homepage/sitemap.
    detail_plan: list[dict[str, str]] = []
    for category in ("careers", "news"):
        candidate = next(
            (
                item for item in candidates
                if item.get("category") == category and _detail_candidate(str(item.get("url") or ""), category)
            ),
            None,
        )
        if candidate:
            detail_plan.append(candidate)

    for candidate in detail_plan[:max_detail_pages]:
        if total["requests"] >= request_allowance:
            break
        page, item_metrics = _fetch_html_candidate(candidate, verified_url=verified_url, robots=robots, timeout=timeout)
        _merge_metrics(total, item_metrics)
        if page is not None:
            pages.append(page)
            fetched_urls.add(str(page.get("url") or "").rstrip("/"))

    # Then fetch one section page per category, prioritizing careers/news/contact over data
    # families already saturated by BRREG (roles/locations).
    chosen_categories: set[str] = set()
    sections = 0
    for candidate in candidates:
        if sections >= max_section_pages or total["requests"] >= request_allowance:
            break
        category = str(candidate.get("category") or "")
        url = str(candidate.get("url") or "")
        if category in chosen_categories or url.rstrip("/") in fetched_urls:
            continue
        if _detail_candidate(url, category) and category in {"careers", "news"}:
            continue
        page, item_metrics = _fetch_html_candidate(candidate, verified_url=verified_url, robots=robots, timeout=timeout)
        _merge_metrics(total, item_metrics)
        chosen_categories.add(category)
        sections += 1
        if page is not None:
            pages.append(page)
            fetched_urls.add(str(page.get("url") or "").rstrip("/"))

    # Section pages may reveal a better direct role/article URL that was absent from the
    # homepage/sitemap. Spend remaining detail slots only on categories not already fetched.
    fetched_detail_categories = {str(page.get("category") or "") for page in pages if _detail_candidate(str(page.get("url") or ""), str(page.get("category") or ""))}
    for category in ("careers", "news"):
        if category in fetched_detail_categories or len(fetched_detail_categories) >= max_detail_pages:
            continue
        found: dict[str, str] | None = None
        for source_page in pages:
            for item in source_page.get("link_candidates") or []:
                url = str(item.get("url") or "")
                if item.get("category") == category and url.rstrip("/") not in fetched_urls and _detail_candidate(url, category):
                    found = item
                    break
            if found:
                break
        if found is None or total["requests"] >= request_allowance:
            continue
        page, item_metrics = _fetch_html_candidate(found, verified_url=verified_url, robots=robots, timeout=timeout)
        _merge_metrics(total, item_metrics)
        if page is not None:
            pages.append(page)
            fetched_urls.add(str(page.get("url") or "").rstrip("/"))
            fetched_detail_categories.add(category)

    feed_entries: list[dict[str, Any]] = []
    feed_candidates: list[str] = []
    for page in pages:
        for url in page.get("feed_links") or []:
            if url not in feed_candidates:
                feed_candidates.append(url)
    if fetch_feed and feed_candidates and total["requests"] < request_allowance:
        import hashlib

        feed_raw, feed_final, _, feed_metrics = _fetch_bytes(
            feed_candidates[0],
            verified_url=verified_url,
            robots=robots,
            timeout=timeout,
            max_bytes=750_000,
            accept="application/rss+xml,application/atom+xml,application/xml,text/xml,*/*;q=0.5",
        )
        _merge_metrics(total, feed_metrics)
        if feed_raw is not None:
            digest = hashlib.sha256(feed_raw).hexdigest()
            feed_entries = [
                {**item, "feed_url": feed_final, "content_sha256": digest}
                for item in parse_feed(feed_raw, feed_url=feed_final, verified_url=verified_url)
            ]

    retrieved_at = utc_now()
    for page in pages:
        page["retrieved_at"] = retrieved_at
    for item in feed_entries:
        item["retrieved_at"] = retrieved_at

    facts = extract_depth_facts(profile, pages, feed_entries, retrieved_at=retrieved_at)
    facts["updates"] = harden_updates(list(facts.get("updates") or []), retrieved_at=retrieved_at)
    return {
        "schema": V6D_HARDENED_SCHEMA,
        "eligible": True,
        "verified_site_url": verified_url,
        "verified_registered_domain": verified_domain,
        "identity_created_by_v6d": False,
        "pages": pages,
        "sitemap_candidate_count": len(sitemap_rows),
        "feed_entries": feed_entries,
        "facts": facts,
        "hardened_update_policy": {
            "max_age_days": MAX_UPDATE_AGE_DAYS,
            "max_updates_per_company": MAX_UPDATES_PER_COMPANY,
            "requires_news_detail_url": True,
            "boilerplate_titles_rejected": True,
            "dedupe_key": "url",
        },
        "page_priority": list(PAGE_PRIORITY),
    }, total
