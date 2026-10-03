from __future__ import annotations

import re
import urllib.parse
from typing import Any

from bs4 import BeautifulSoup

from .website import _registered_domain

CAREERS_TERMS = (
    "career",
    "careers",
    "join our team",
    "work with us",
    "job opportunities",
    "karriere",
    "jobb hos oss",
    "jobbe hos oss",
    "ledige stillinger",
    "stillinger",
    "vacancies",
    "vacancy",
)


def _same_registered_domain(left: str, right: str) -> bool:
    try:
        a = _registered_domain(left)
        b = _registered_domain(right)
    except Exception:
        return False
    return bool(a and b and a == b)


def extract_careers_links(
    *,
    verified_url: str,
    final_url: str,
    soup: BeautifulSoup,
    homepage_content_sha256: str,
) -> list[dict[str, Any]]:
    """Return explicit same-domain careers surfaces declared by a verified homepage.

    This is a narrow hiring-presence signal only. It never claims an active vacancy and
    never follows or fetches the careers link. External ATS/job-board links are excluded.
    """
    if not _same_registered_domain(final_url, verified_url):
        return []

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for anchor in soup.select("a[href]"):
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
        normalized = urllib.parse.urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, "")
        )
        if normalized in seen or not _same_registered_domain(normalized, verified_url):
            continue
        anchor_text = " ".join(anchor.get_text(" ", strip=True).split())
        haystack = urllib.parse.unquote(f"{parsed.path} {anchor_text}").casefold()
        marker = next(
            (term for term in CAREERS_TERMS if re.search(re.escape(term), haystack, re.IGNORECASE)),
            None,
        )
        if not marker:
            continue
        seen.add(normalized)
        rows.append(
            {
                "url": normalized,
                "anchor_text": anchor_text[:240],
                "marker": marker,
                "homepage_url": final_url,
                "homepage_content_sha256": homepage_content_sha256,
                "evidence_span": f"Homepage link: {anchor_text or normalized}"[:500],
                "claim_scope": (
                    "Exact verified company homepage explicitly links to a same-domain careers/hiring surface. "
                    "This is a hiring-presence signal only and does not assert an active vacancy."
                ),
            }
        )
    rows.sort(key=lambda item: (len(urllib.parse.urlparse(item["url"]).path), item["url"]))
    return rows[:4]
