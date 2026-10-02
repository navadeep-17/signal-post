from __future__ import annotations

from typing import Any

from . import verified_site_depth_hardened as hardened


def _safe_detail_candidate(url: str, category: str) -> bool:
    """Only careers/news have detail semantics in V6d.

    The v1 hardened planner deliberately reuses the base detail helper, whose contract
    assumes a known CATEGORY_TERMS key. Homepage/about/contact pages are not detail
    candidates and must therefore short-circuit instead of reaching that helper.
    """
    if category not in {"careers", "news"}:
        return False
    return hardened._detail_candidate(url, category)


def crawl_verified_site_depth_hardened_v2(
    profile: dict[str, Any],
    **kwargs: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    original = hardened._detail_candidate
    hardened._detail_candidate = _safe_detail_candidate
    try:
        return hardened.crawl_verified_site_depth_hardened(profile, **kwargs)
    finally:
        hardened._detail_candidate = original


harden_updates = hardened.harden_updates
PAGE_PRIORITY = hardened.PAGE_PRIORITY
MAX_UPDATE_AGE_DAYS = hardened.MAX_UPDATE_AGE_DAYS
MAX_UPDATES_PER_COMPANY = hardened.MAX_UPDATES_PER_COMPANY
