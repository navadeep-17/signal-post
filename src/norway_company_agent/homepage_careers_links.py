from __future__ import annotations

import hashlib
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from typing import Any

from bs4 import BeautifulSoup

from .final_site_discovery import BOUNDED_SAFE_OPENER
from .website import USER_AGENT, _registered_domain, assert_public_url

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


def _verified_site(profile: dict[str, Any]) -> str | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return None
    value_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    return value_url or None


def _same_registered_domain(left: str, right: str) -> bool:
    try:
        a = _registered_domain(left)
        b = _registered_domain(right)
    except Exception:
        return False
    return bool(a and b and a == b)


def extract_careers_links(*, verified_url: str, final_url: str, raw: bytes, content_type: str) -> list[dict[str, Any]]:
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
        anchor_text = " ".join(anchor.get_text(" ", strip=True).split())
        haystack = urllib.parse.unquote(f"{parsed.path} {anchor_text}").casefold()
        marker = next((term for term in CAREERS_TERMS if re.search(re.escape(term), haystack, re.IGNORECASE)), None)
        if not marker:
            continue
        seen.add(normalized)
        rows.append(
            {
                "url": normalized,
                "anchor_text": anchor_text[:240],
                "marker": marker,
                "homepage_url": final_url,
                "homepage_content_sha256": digest,
                "evidence_span": f"Homepage link: {anchor_text or normalized}"[:500],
                "claim_scope": (
                    "Exact verified company homepage explicitly links to a same-domain careers/hiring surface. "
                    "This is a hiring-presence signal only and does not assert an active vacancy."
                ),
            }
        )
    rows.sort(key=lambda item: (len(urllib.parse.urlparse(item["url"]).path), item["url"]))
    return rows[:4]


def probe_verified_homepage_careers_links(
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
        return extract_careers_links(
            verified_url=verified_url,
            final_url=final_url,
            raw=raw,
            content_type=content_type,
        ), metrics
    except Exception as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["errors"].append(f"fetch:{type(exc).__name__}:{str(exc)[:140]}")
        return [], metrics
