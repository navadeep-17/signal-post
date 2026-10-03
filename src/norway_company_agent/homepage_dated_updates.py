from __future__ import annotations

import hashlib
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup, Tag

from .final_site_discovery import BOUNDED_SAFE_OPENER
from .website import USER_AGENT, _registered_domain, assert_public_url

UPDATE_PATH_TERMS = (
    "news",
    "nyheter",
    "aktuelt",
    "press",
    "presse",
    "pressemelding",
    "press-release",
    "blog",
    "article",
    "articles",
    "insights",
    "media",
)
GENERIC_TITLES = {
    "news",
    "nyheter",
    "aktuelt",
    "press",
    "presse",
    "blog",
    "articles",
    "insights",
    "media",
    "read more",
    "les mer",
}
DATE_RE = re.compile(
    r"\b(20\d{2}-[01]\d-[0-3]\d|[0-3]?\d[./-][01]?\d[./-]20\d{2})\b"
)
MONTH_RE = re.compile(
    r"\b([0-3]?\d\s+(?:jan(?:uar)?|feb(?:ruar)?|mar(?:s|ch)?|apr(?:il)?|mai|may|jun(?:i|e)?|jul(?:i|y)?|aug(?:ust)?|sep(?:tember)?|okt(?:ober)?|oct(?:ober)?|nov(?:ember)?|des(?:ember)?|dec(?:ember)?)\s+20\d{2})\b",
    re.IGNORECASE,
)


def _verified_site(profile: dict[str, Any]) -> str | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return None
    url = str(value.get("final_url") or website.get("source_url") or "").strip()
    return url or None


def _same_registered_domain(left: str, right: str) -> bool:
    try:
        a = _registered_domain(left)
        b = _registered_domain(right)
    except Exception:
        return False
    return bool(a and b and a == b)


def _specific_title(text: str) -> bool:
    value = " ".join(text.split()).strip()
    if not value or value.casefold() in GENERIC_TITLES:
        return False
    words = re.findall(r"[\wæøåÆØÅ-]+", value, flags=re.UNICODE)
    return len(words) >= 3


def _normalize_date(value: str) -> str | None:
    value = " ".join(value.strip().split())
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return value or None


def _date_from_container(anchor: Tag) -> tuple[str | None, str | None]:
    nodes: list[Tag] = [anchor]
    current = anchor.parent
    for _ in range(4):
        if not isinstance(current, Tag):
            break
        nodes.append(current)
        if current.name in {"article", "li"}:
            break
        current = current.parent

    for node in nodes:
        time_node = node.find("time")
        if isinstance(time_node, Tag):
            raw = str(time_node.get("datetime") or time_node.get_text(" ", strip=True) or "").strip()
            if raw:
                candidate = raw[:10] if re.match(r"^20\d{2}-[01]\d-[0-3]\d", raw) else raw
                return _normalize_date(candidate), "time"
        text = " ".join(node.get_text(" ", strip=True).split())[:1200]
        match = DATE_RE.search(text) or MONTH_RE.search(text)
        if match:
            return _normalize_date(match.group(1)), "text"
    return None, None


def extract_dated_update_links(
    *,
    verified_url: str,
    final_url: str,
    raw: bytes,
    content_type: str,
) -> list[dict[str, Any]]:
    """Extract specific same-domain dated article/update links from a verified homepage."""
    if not _same_registered_domain(final_url, verified_url):
        return []
    if "html" not in str(content_type or "").casefold():
        return []
    html = raw.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    digest = hashlib.sha256(raw).hexdigest()
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
        normalized = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, ""))
        if normalized in seen or not _same_registered_domain(normalized, verified_url):
            continue
        path = urllib.parse.unquote(parsed.path).casefold()
        if not any(term in path for term in UPDATE_PATH_TERMS):
            continue
        title = " ".join(anchor.get_text(" ", strip=True).split())
        if not _specific_title(title):
            continue
        # Section roots such as /news or /aktuelt are not updates themselves.
        segments = [segment for segment in path.split("/") if segment]
        if len(segments) < 2 and segments and segments[0] in UPDATE_PATH_TERMS:
            continue
        published_date, date_source = _date_from_container(anchor)
        if not published_date:
            continue
        seen.add(normalized)
        rows.append(
            {
                "url": normalized,
                "title": title[:500],
                "published_date": published_date,
                "date_source": date_source,
                "homepage_url": final_url,
                "homepage_content_sha256": digest,
                "evidence_span": f"Homepage update card: {published_date} — {title}"[:700],
                "claim_scope": (
                    "Exact verified company homepage exposes a specific same-domain update link with an explicit date. "
                    "The claim is limited to the dated company-owned update shown on the homepage."
                ),
            }
        )
    rows.sort(key=lambda item: (item["published_date"], item["url"]), reverse=True)
    return rows[:8]


def probe_verified_homepage_dated_updates(
    profile: dict[str, Any],
    *,
    timeout: float = 6.0,
    max_bytes: int = 750_000,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metrics: dict[str, Any] = {
        "eligible": False,
        "requests": 0,
        "bytes": 0,
        "latencies_ms": [],
        "errors": [],
    }
    verified_url = _verified_site(profile)
    if not verified_url:
        return [], metrics
    metrics["eligible"] = True
    try:
        assert_public_url(verified_url)
    except ValueError as exc:
        metrics["errors"].append(f"blocked:{str(exc)[:120]}")
        return [], metrics

    parsed = urllib.parse.urlparse(verified_url)
    robots_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    robots = urllib.robotparser.RobotFileParser()
    robots.set_url(robots_url)
    started = time.monotonic()
    metrics["requests"] += 1
    try:
        request = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            raw_robots = response.read(250_000)
        metrics["bytes"] += len(raw_robots)
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        robots.parse(raw_robots.decode("utf-8", errors="replace").splitlines())
        if not robots.can_fetch(USER_AGENT, verified_url):
            metrics["errors"].append("robots_disallow")
            return [], metrics
    except Exception as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["errors"].append(f"robots:{type(exc).__name__}:{str(exc)[:120]}")

    started = time.monotonic()
    metrics["requests"] += 1
    request = urllib.request.Request(
        verified_url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    try:
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            final_url = response.geturl()
            content_type = str(response.headers.get("content-type") or "")
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["bytes"] += len(raw)
        if len(raw) > max_bytes:
            metrics["errors"].append("oversized")
            return [], metrics
        try:
            assert_public_url(final_url)
        except ValueError as exc:
            metrics["errors"].append(f"redirect_blocked:{str(exc)[:120]}")
            return [], metrics
        if not _same_registered_domain(final_url, verified_url):
            metrics["errors"].append(f"redirect_outside_verified_domain:{final_url}")
            return [], metrics
        return extract_dated_update_links(
            verified_url=verified_url,
            final_url=final_url,
            raw=raw,
            content_type=content_type,
        ), metrics
    except Exception as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["errors"].append(f"fetch:{type(exc).__name__}:{str(exc)[:140]}")
        return [], metrics
