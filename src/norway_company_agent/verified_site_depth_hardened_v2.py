from __future__ import annotations

import urllib.parse
from typing import Any

from . import verified_site_depth as base
from . import verified_site_depth_hardened as hardened

_BASE_DETAIL_CANDIDATE = hardened._detail_candidate
_BASE_PAGE_CATEGORY = base._page_category


def _safe_page_category(url: str, anchor_text: str = "") -> str | None:
    """Classify scoring-relevant sections before broad about/company markers.

    The original generic classifier checked `about` before `news`, and its broad `company`
    token could therefore misclassify a URL such as `/news/company-announcement/`. V6d
    explicitly prioritizes hiring/activity/contact paths because those are the sparse
    scoring families this experiment is designed to measure.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return None
    haystack = urllib.parse.unquote(f"{parsed.path} {anchor_text}").casefold()
    for category in ("careers", "news", "contact", "team", "locations", "about"):
        if any(term in haystack for term in base.CATEGORY_TERMS[category]):
            return category
    return None


def _safe_detail_candidate(url: str, category: str) -> bool:
    if category not in {"careers", "news"}:
        return False
    return _BASE_DETAIL_CANDIDATE(url, category)


def harden_updates(
    updates: list[dict[str, Any]],
    *,
    retrieved_at: str,
    max_age_days: int = hardened.MAX_UPDATE_AGE_DAYS,
    max_updates: int = hardened.MAX_UPDATES_PER_COMPANY,
) -> list[dict[str, Any]]:
    """Harden updates with the V6d high-value classifier, URL dedupe and recency cap."""
    accepted: dict[str, dict[str, Any]] = {}
    for item in updates:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not hardened._specific_update_title(title):
            continue
        if _safe_page_category(url) != "news" or not _BASE_DETAIL_CANDIDATE(url, "news"):
            continue
        if not hardened._is_recent_update(item, retrieved_at=retrieved_at, max_age_days=max_age_days):
            continue
        key = url.rstrip("/")
        current = accepted.get(key)
        if current is None:
            accepted[key] = dict(item)
            continue
        current_is_feed = str(current.get("strategy") or "") == "first_party_feed_item"
        incoming_is_feed = str(item.get("strategy") or "") == "first_party_feed_item"
        if current_is_feed and not incoming_is_feed:
            accepted[key] = dict(item)

    ordered = sorted(
        accepted.values(),
        key=lambda item: (str(item.get("published_date") or ""), str(item.get("url") or "")),
        reverse=True,
    )
    return ordered[:max_updates]


def crawl_verified_site_depth_hardened_v2(
    profile: dict[str, Any],
    **kwargs: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    original_hardened_detail = hardened._detail_candidate
    original_hardened_category = hardened._page_category
    original_hardened_updates = hardened.harden_updates
    original_base_category = base._page_category
    hardened._detail_candidate = _safe_detail_candidate
    hardened._page_category = _safe_page_category
    hardened.harden_updates = harden_updates
    base._page_category = _safe_page_category
    try:
        return hardened.crawl_verified_site_depth_hardened(profile, **kwargs)
    finally:
        hardened._detail_candidate = original_hardened_detail
        hardened._page_category = original_hardened_category
        hardened.harden_updates = original_hardened_updates
        base._page_category = original_base_category


PAGE_PRIORITY = hardened.PAGE_PRIORITY
MAX_UPDATE_AGE_DAYS = hardened.MAX_UPDATE_AGE_DAYS
MAX_UPDATES_PER_COMPANY = hardened.MAX_UPDATES_PER_COMPANY
