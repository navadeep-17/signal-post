from __future__ import annotations

import re
import urllib.parse
from typing import Any

from bs4 import BeautifulSoup, Tag

from .website import _registered_domain

NEWS_PATH_TERMS = ("aktuelt", "nyheter", "news", "blog", "blogg", "press", "presse", "artikler", "articles")
GENERIC_NEWS_TITLES = {"aktuelt", "nyheter", "news", "blog", "blogg", "press", "presse", "artikler", "articles", "les mer", "read more"}
DATE_HINT_RE = re.compile(
    r"\b(?:20\d{2}-[01]\d-[0-3]\d|[0-3]?\d[./-][01]?\d[./-](?:20\d{2}|\d{2}))\b"
)


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


def _dated_local_context(anchor: Tag, *, max_chars: int = 1600) -> str | None:
    """Return bounded local card text when an explicit visible date surrounds a link.

    Some exact company homepages expose news cards whose detail URLs are root-level slugs
    rather than `/news/<slug>`. A visible date in the same local card is strong enough to
    *nominate* that link for one bounded detail fetch. It is never publication evidence by
    itself; the fetched destination must still pass the strict detail-page gate.
    """
    direct = " ".join(anchor.get_text(" ", strip=True).split())
    if DATE_HINT_RE.search(direct):
        return direct[:max_chars]

    depth = 0
    for parent in anchor.parents:
        if not isinstance(parent, Tag):
            continue
        if parent.name not in {"article", "li", "div", "section"}:
            continue
        depth += 1
        text = " ".join(parent.get_text(" ", strip=True).split())
        if 0 < len(text) <= max_chars and DATE_HINT_RE.search(text):
            return text
        if depth >= 4:
            break
    return None


def extract_news_detail_links(
    *,
    verified_url: str,
    final_url: str,
    soup: BeautifulSoup,
    homepage_content_sha256: str,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Nominate bounded same-domain first-party news/article detail links.

    Two nomination shapes are accepted: a specific URL below a known news path, or a
    same-domain link inside a small homepage card carrying an explicit visible date. The
    latter covers sites such as Lucerna whose news detail pages use root-level slugs.

    Nomination never becomes a fact. The destination must be independently fetched and
    later pass the strict page-level title/date/content publication gate.
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

        specific_path, path_marker = _specific_news_path(clean)
        dated_context = _dated_local_context(anchor)
        if not specific_path and not dated_context:
            continue

        anchor_text = " ".join(anchor.get_text(" ", strip=True).split())
        generic_anchor = anchor_text.casefold().strip(" -|:") in GENERIC_NEWS_TITLES
        if generic_anchor and not dated_context:
            continue

        marker = path_marker or "dated_homepage_card"
        seen.add(clean)
        rows.append(
            {
                "url": clean,
                "anchor_text": anchor_text[:300],
                "marker": marker,
                "homepage_url": final_url,
                "homepage_content_sha256": homepage_content_sha256,
                "document_order": position,
                "dated_context": dated_context[:500] if dated_context else None,
                "nomination_only": True,
            }
        )
        if len(rows) >= limit:
            break
    return rows
