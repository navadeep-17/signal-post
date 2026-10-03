from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from typing import Any
import urllib.parse

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .website import _registered_domain

ARTICLE_TYPES = {"Article", "NewsArticle", "BlogPosting"}
GENERIC_TITLES = {
    "aktuelt", "nyheter", "news", "blog", "blogg", "artikler", "articles", "media", "press", "latest news",
}
GENERIC_PATH_SEGMENTS = {"aktuelt", "nyheter", "news", "blog", "blogg", "artikler", "articles", "media", "press"}


def _same_registered_domain(left: str, right: str) -> bool:
    try:
        a = _registered_domain(left)
        b = _registered_domain(right)
        return bool(a and b and a.casefold() == b.casefold())
    except Exception:
        return False


def _clean_space(value: Any) -> str:
    return " ".join(str(value or "").split())


def _jsonld_nodes(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    roots: list[Any] = []
    for node in soup.select('script[type="application/ld+json"]'):
        raw = node.string or node.get_text("", strip=True)
        if not raw:
            continue
        try:
            roots.append(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            continue

    found: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            found.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for root in roots:
        walk(root)
    return found


def _types(node: dict[str, Any]) -> set[str]:
    raw = node.get("@type")
    values = raw if isinstance(raw, list) else [raw]
    return {str(value) for value in values if value}


def _parse_date(value: Any) -> date | None:
    raw = _clean_space(value)
    if not raw:
        return None
    try:
        parsed = date_parser.parse(raw, fuzzy=False)
    except (ValueError, TypeError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.date()


def _specific_article_path(page_url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(page_url)
    except ValueError:
        return False
    parts = [urllib.parse.unquote(part).strip().casefold() for part in parsed.path.split("/") if part.strip()]
    if not parts:
        return False
    # `/news` or `/aktuelt` is an archive/surface, not a specific update.
    if len(parts) == 1 and parts[0] in GENERIC_PATH_SEGMENTS:
        return False
    # A locale + generic archive (`/nb/aktuelt`) is still not an update page.
    if len(parts) == 2 and parts[-1] in GENERIC_PATH_SEGMENTS and len(parts[0]) <= 3:
        return False
    return True


def _title_is_specific(title: str) -> bool:
    normal = _clean_space(title)
    if len(normal) < 8:
        return False
    folded = normal.casefold().strip(" -|:")
    if folded in GENERIC_TITLES:
        return False
    return any(character.isalpha() for character in normal)


def _structured_article_candidates(html: str, page_url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in _jsonld_nodes(html):
        if not (_types(node) & ARTICLE_TYPES):
            continue
        raw_url: Any = node.get("url")
        if isinstance(raw_url, dict):
            raw_url = raw_url.get("@id") or raw_url.get("url")
        entity = node.get("mainEntityOfPage")
        if not raw_url and isinstance(entity, dict):
            raw_url = entity.get("@id") or entity.get("url")
        structured_url = urllib.parse.urljoin(page_url, str(raw_url or page_url))
        rows.append(
            {
                "url": structured_url,
                "title": _clean_space(node.get("headline") or node.get("name") or node.get("title")),
                "date_published_raw": _clean_space(node.get("datePublished")),
                "date_modified_raw": _clean_space(node.get("dateModified")),
                "method": "jsonld_article",
            }
        )
    return rows


def _page_title(soup: BeautifulSoup) -> str:
    meta = soup.select_one('meta[property="og:title"], meta[name="twitter:title"]')
    if meta and _clean_space(meta.get("content")):
        return _clean_space(meta.get("content"))
    heading = soup.select_one("main h1, article h1, h1")
    if heading:
        return _clean_space(heading.get_text(" ", strip=True))
    if soup.title:
        return _clean_space(soup.title.get_text(" ", strip=True))
    return ""


def _page_published_date(soup: BeautifulSoup) -> tuple[str, str] | tuple[None, None]:
    selectors = (
        ('meta[property="article:published_time"]', "content", "meta_article_published_time"),
        ('meta[itemprop="datePublished"]', "content", "meta_itemprop_date_published"),
        ('meta[name="date"]', "content", "meta_name_date"),
        ('time[itemprop="datePublished"][datetime]', "datetime", "time_itemprop_date_published"),
        ('article time[datetime]', "datetime", "article_time_datetime"),
        ('main time[datetime]', "datetime", "main_time_datetime"),
    )
    for selector, attribute, method in selectors:
        node = soup.select_one(selector)
        raw = _clean_space(node.get(attribute)) if node else ""
        if raw and _parse_date(raw):
            return raw, method
    return None, None


def _article_text(soup: BeautifulSoup, limit: int = 1200) -> str:
    node = soup.select_one("article") or soup.select_one("main")
    if not node:
        return ""
    text = _clean_space(node.get_text(" ", strip=True))
    return text[:limit]


def qualify_first_party_update(
    *,
    verified_company_url: str,
    page_url: str,
    html: str,
    content_sha256: str,
    as_of: date | None = None,
    max_age_days: int | None = None,
) -> dict[str, Any]:
    """Qualify one specific, dated, first-party company update page.

    Sitemap `lastmod`, feed dates, discovery labels and archive-page metadata are never
    publication evidence here. The destination page itself must expose a publication date.
    """
    today = as_of or datetime.now(timezone.utc).date()
    base = {
        "page_url": page_url,
        "status": "review",
        "publishable": False,
        "title": None,
        "date_published": None,
        "date_method": None,
        "content_sha256": content_sha256 if len(str(content_sha256 or "")) == 64 else None,
        "evidence_span": None,
        "reasons": [],
    }
    if not _same_registered_domain(verified_company_url, page_url):
        return {**base, "status": "rejected", "reasons": ["page leaves exact verified company registered domain"]}
    if len(str(content_sha256 or "")) != 64:
        return {**base, "status": "rejected", "reasons": ["missing bounded destination-page content hash"]}
    if not _specific_article_path(page_url):
        return {**base, "status": "rejected", "reasons": ["URL is a generic news/archive surface rather than a specific update"]}

    soup = BeautifulSoup(html, "lxml")
    structured = _structured_article_candidates(html, page_url)
    selected = next(
        (
            row
            for row in structured
            if _same_registered_domain(verified_company_url, row["url"])
            and urllib.parse.urlparse(row["url"]).path.rstrip("/") == urllib.parse.urlparse(page_url).path.rstrip("/")
        ),
        None,
    )

    title = _clean_space((selected or {}).get("title")) or _page_title(soup)
    date_raw = _clean_space((selected or {}).get("date_published_raw"))
    date_method = str((selected or {}).get("method") or "") or None
    published = _parse_date(date_raw)
    if published is None:
        fallback_raw, fallback_method = _page_published_date(soup)
        date_raw = fallback_raw or ""
        date_method = fallback_method
        published = _parse_date(date_raw)

    result = {**base, "title": title or None, "date_published": published.isoformat() if published else None, "date_method": date_method}
    if not _title_is_specific(title):
        return {**result, "status": "rejected", "reasons": ["page lacks a specific non-generic update title"]}
    if published is None:
        return {**result, "status": "review", "reasons": ["destination page lacks an explicit parseable publication date"]}
    if published > today:
        return {**result, "status": "rejected", "reasons": ["publication date is in the future"]}
    if max_age_days is not None and max_age_days >= 0 and (today - published).days > max_age_days:
        return {**result, "status": "stale", "reasons": [f"publication is older than {max_age_days} days"]}

    span = _article_text(soup)
    if not span:
        return {**result, "status": "review", "reasons": ["specific dated page lacks bounded article/main text evidence"]}

    return {
        **result,
        "status": "exact_dated_update",
        "publishable": True,
        "evidence_span": span,
        "reasons": ["specific first-party update page has explicit page-level publication date and bounded article text"],
        "claim_scope": "Company-authored first-party dated update. No sentiment, importance or intent is inferred.",
    }
