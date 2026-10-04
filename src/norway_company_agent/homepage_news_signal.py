from __future__ import annotations

import urllib.parse
from typing import Any

from bs4 import BeautifulSoup

from .website import _registered_domain

NEWS_PATH_TERMS = ("aktuelt", "nyheter", "news", "blog", "blogg", "press", "presse", "artikler", "articles")
GENERIC_NEWS_TITLES = {"aktuelt", "nyheter", "news", "blog", "blogg", "press", "presse", "artikler", "articles", "les mer", "read more"}


def _same_registered_domain(left: str, right: str) -> bool:
    try:
        a = _registered_domain(left)
        b = _registered_domain(right)
    except Exception:
        return False
    return bool(a and b and a.casefold() == b.casefold())


def _specific_news_path(url: str) -> tuple[bool, str | None]:
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False, None
    parts = [urllib.parse.unquote(part).strip().casefold() for part in parsed.path.split("/") if part.strip()]
    positions = [(index, term) for index, part in enumerate(parts) for term in NEWS_PATH_TERMS if part == term]
    if not positions:
        return False, None
    index, term = positions[-1]
    return index < len(parts) - 1, term


def extract_news_detail_links(
    *,
    verified_url: str,
    final_url: str,
    soup: BeautifulSoup,
    homepage_content_sha256: str,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Nominate specific same-domain first-party news/article detail links.

    This is discovery only. A returned URL is never itself a company-update fact. The
    destination must be independently fetched and later pass the strict dated-detail-page
    projector before publication.
    """
    if limit < 1 or not _same_registered_domain(verified_url, final_url):
        return []

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for position, anchor in enumerate(soup.select("a[href]")):
        href = str(anchor.get("href") or "").strip()
        if not href:
            continue
        absolute = urllib.parse.urljoin(final_url, href)
        try:
            parsed = urllib.parse.urlparse(absolute)
        except ValueError:
            continue
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        clean = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))
        if clean.rstrip("/") == final_url.rstrip("/") or clean in seen:
            continue
        if not _same_registered_domain(clean, verified_url):
            continue
        specific, marker = _specific_news_path(clean)
        if not specific or not marker:
            continue
        anchor_text = " ".join(anchor.get_text(" ", strip=True).split())
        if anchor_text.casefold().strip(" -|:") in GENERIC_NEWS_TITLES:
            continue
        seen.add(clean)
        rows.append(
            {
                "url": clean,
                "anchor_text": anchor_text[:300],
                "marker": marker,
                "homepage_url": final_url,
                "homepage_content_sha256": homepage_content_sha256,
                "document_order": position,
                "nomination_only": True,
            }
        )
        if len(rows) >= limit:
            break
    return rows
