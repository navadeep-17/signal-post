from __future__ import annotations

import re
import urllib.parse
from typing import Any

from bs4 import BeautifulSoup

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
    "ledige-stillinger",
    "jobb",
    "jobber",
    "stillinger",
    "vacancies",
    "vacancy",
)


def _normalized_host(url: str) -> str:
    try:
        host = (urllib.parse.urlparse(url).hostname or "").casefold().rstrip(".")
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _same_company_host(left: str, right: str) -> bool:
    """Conservatively compare already-verified first-party hosts without PSL/network I/O.

    Exact root/www matches and direct parent/subdomain relationships are accepted. Sibling
    subdomains intentionally abstain rather than requiring a public-suffix lookup.
    """
    a = _normalized_host(left)
    b = _normalized_host(right)
    if not a or not b:
        return False
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def extract_careers_links(
    *,
    verified_url: str,
    final_url: str,
    soup: BeautifulSoup,
    homepage_content_sha256: str,
) -> list[dict[str, Any]]:
    """Return explicit same-company-host careers surfaces declared by a verified homepage.

    This is a narrow hiring-presence signal only. It never claims an active vacancy and
    never follows or fetches the careers link. External ATS/job-board links are excluded.
    """
    if not _same_company_host(final_url, verified_url):
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
        if normalized in seen or not _same_company_host(normalized, verified_url):
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
                    "Exact verified company homepage explicitly links to a same-company-host careers/hiring surface. "
                    "This is a hiring-presence signal only and does not assert an active vacancy."
                ),
            }
        )
    rows.sort(key=lambda item: (len(urllib.parse.urlparse(item["url"]).path), item["url"]))
    return rows[:4]
