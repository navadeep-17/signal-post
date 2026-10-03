from __future__ import annotations

import hashlib
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from typing import Any

from bs4 import BeautifulSoup
import trafilatura

from .final_site_discovery import BOUNDED_SAFE_OPENER
from .website import USER_AGENT, _registered_domain, assert_public_url

CAREERS_PATH = "/careers"
CAREERS_MARKERS = (
    "careers",
    "career opportunities",
    "join our team",
    "work with us",
    "job opportunities",
    "karriere",
    "jobb hos oss",
    "jobbe hos oss",
    "ledige stillinger",
)


def _verified_site(profile: dict[str, Any]) -> str | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return None
    url = str(value.get("final_url") or website.get("source_url") or "").strip()
    return url or None


def _candidate_url(verified_url: str) -> str:
    parsed = urllib.parse.urlparse(verified_url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, CAREERS_PATH, "", "", ""))


def _same_registered_domain(left: str, right: str) -> bool:
    try:
        left_domain = _registered_domain(left)
        right_domain = _registered_domain(right)
    except Exception:
        return False
    return bool(left_domain and right_domain and left_domain == right_domain)


def _robots_allowed(candidate_url: str, *, timeout: float) -> tuple[bool, dict[str, Any]]:
    parsed = urllib.parse.urlparse(candidate_url)
    robots_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    metrics = {"requests": 1, "bytes": 0, "latencies_ms": [], "errors": []}
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    started = time.monotonic()
    try:
        assert_public_url(robots_url)
        request = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(250_000)
        metrics["bytes"] += len(raw)
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        parser.parse(raw.decode("utf-8", errors="replace").splitlines())
        return parser.can_fetch(USER_AGENT, candidate_url), metrics
    except Exception as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["errors"].append(f"robots:{type(exc).__name__}:{str(exc)[:120]}")
        return True, metrics


def _bounded_visible_text(soup: BeautifulSoup, *, limit: int = 20000) -> str:
    """Return bounded page-visible text for robust section qualification.

    Trafilatura is intentionally precision-biased and can omit navigation/hero text on
    modern corporate pages. Careers-page qualification is a coarse presence signal, so a
    bounded BeautifulSoup fallback is appropriate after the exact-site/domain gate has
    already succeeded.
    """
    for node in soup(["script", "style", "noscript", "svg"]):
        node.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())[:limit]


def qualify_careers_html(
    *,
    verified_url: str,
    final_url: str,
    raw: bytes,
    content_type: str,
) -> dict[str, Any] | None:
    """Qualify a careers-presence page without claiming any active vacancy."""
    if not _same_registered_domain(final_url, verified_url):
        return None
    if "html" not in str(content_type or "").casefold():
        return None
    html = raw.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    article_text = trafilatura.extract(
        html,
        url=final_url,
        include_links=False,
        include_tables=False,
        favor_precision=True,
    ) or ""
    visible_text = _bounded_visible_text(soup)
    searchable = " ".join((title, article_text[:12000], visible_text))
    marker = next((item for item in CAREERS_MARKERS if re.search(re.escape(item), searchable, re.IGNORECASE)), None)
    if not marker:
        return None
    match = re.search(re.escape(marker), searchable, re.IGNORECASE)
    assert match is not None
    start = max(0, match.start() - 140)
    end = min(len(searchable), match.end() + 180)
    span = " ".join(searchable[start:end].split())[:600]
    return {
        "url": final_url,
        "title": title[:500],
        "marker": marker,
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "evidence_span": span,
        "claim_scope": (
            "Exact verified company website exposes a dedicated careers page. "
            "This is a hiring-presence signal only; it does not assert any active vacancy."
        ),
    }


def probe_targeted_careers_page(
    profile: dict[str, Any],
    *,
    timeout: float = 6.0,
    max_bytes: int = 750_000,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Probe only `/careers` on an already exact-verified company website.

    The experiment adds at most two logical requests per verified site: robots.txt and one
    careers-page GET. No website identity is inferred here; the exact verified site must
    already exist in the profile.
    """
    metrics: dict[str, Any] = {
        "eligible": False,
        "candidate_url": None,
        "requests": 0,
        "bytes": 0,
        "latencies_ms": [],
        "errors": [],
    }
    verified_url = _verified_site(profile)
    if not verified_url:
        return None, metrics
    metrics["eligible"] = True
    candidate = _candidate_url(verified_url)
    metrics["candidate_url"] = candidate
    try:
        assert_public_url(candidate)
    except ValueError as exc:
        metrics["errors"].append(f"blocked:{str(exc)[:120]}")
        return None, metrics

    allowed, robots = _robots_allowed(candidate, timeout=timeout)
    metrics["requests"] += int(robots["requests"])
    metrics["bytes"] += int(robots["bytes"])
    metrics["latencies_ms"].extend(robots["latencies_ms"])
    metrics["errors"].extend(robots["errors"])
    if not allowed:
        metrics["errors"].append("robots_disallow")
        return None, metrics

    started = time.monotonic()
    metrics["requests"] += 1
    request = urllib.request.Request(
        candidate,
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
            return None, metrics
        try:
            assert_public_url(final_url)
        except ValueError as exc:
            metrics["errors"].append(f"redirect_blocked:{str(exc)[:120]}")
            return None, metrics
        if not _same_registered_domain(final_url, verified_url):
            metrics["errors"].append(f"redirect_outside_verified_domain:{final_url}")
            return None, metrics
        return qualify_careers_html(
            verified_url=verified_url,
            final_url=final_url,
            raw=raw,
            content_type=content_type,
        ), metrics
    except Exception as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["errors"].append(f"fetch:{type(exc).__name__}:{str(exc)[:140]}")
        return None, metrics
