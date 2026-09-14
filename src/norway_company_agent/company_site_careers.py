from __future__ import annotations

import hashlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from bs4 import BeautifulSoup
import trafilatura

from .website import SAFE_OPENER, USER_AGENT, _registered_domain, _robots_allowed, assert_public_url

CAREER_TERMS = (
    "ledige-stillinger",
    "ledige stillinger",
    "jobb-hos-oss",
    "jobb hos oss",
    "arbeid-hos-oss",
    "arbeid hos oss",
    "karriere",
    "career",
    "careers",
    "vacancies",
    "vacancy",
    "jobs",
    "jobber",
    "jobb",
    "join-us",
    "join us",
    "work-with-us",
    "work with us",
)

CAREER_PATH_MARKERS = {
    "career", "careers", "karriere", "jobb", "jobber", "jobs", "job",
    "stilling", "stillinger", "vacancy", "vacancies", "position", "positions",
    "ledige-stillinger", "jobb-hos-oss", "arbeid-hos-oss",
}

GENERIC_JOB_ANCHORS = {
    "career", "careers", "karriere", "jobb", "jobber", "jobs", "job",
    "ledige stillinger", "se ledige stillinger", "alle stillinger", "all jobs",
    "view jobs", "see jobs", "open positions", "vacancies", "vacancy",
    "join us", "work with us", "jobb hos oss", "arbeid hos oss", "les mer", "read more",
}


def _normalise_text(value: Any) -> str:
    text = str(value or "").translate(str.maketrans({"ø": "o", "Ø": "O", "å": "a", "Å": "A", "æ": "ae", "Æ": "AE"})).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def verified_company_site(profile: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    website = (profile.get("evidence") or {}).get("website") or {}
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    source_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    if website.get("status") != "available" or not identity.get("publishable") or not source_url:
        return None
    return source_url, identity


def career_links(base_url: str, html: str, *, limit: int = 2) -> list[dict[str, Any]]:
    """Return a tiny same-site careers candidate set ranked by path/anchor evidence."""
    if limit < 1:
        return []
    soup = BeautifulSoup(html, "lxml")
    base_domain = _registered_domain(base_url)
    candidates: dict[str, dict[str, Any]] = {}
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        url = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or _registered_domain(url) != base_domain:
            continue
        anchor_text = anchor.get_text(" ", strip=True)
        haystack = f"{parsed.path} {anchor_text}".casefold()
        rank = next((index for index, term in enumerate(CAREER_TERMS) if term in haystack), None)
        if rank is None:
            continue
        clean = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, ""))
        if clean.rstrip("/") == base_url.rstrip("/"):
            continue
        item = {"url": clean, "anchor_text": anchor_text[:240], "rank": rank}
        previous = candidates.get(clean)
        if previous is None or rank < previous["rank"]:
            candidates[clean] = item
    return sorted(candidates.values(), key=lambda item: (item["rank"], item["url"]))[:limit]


def _specific_job_link(page_url: str, href: str, anchor_text: str) -> dict[str, str] | None:
    url = urllib.parse.urljoin(page_url, href)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or _registered_domain(url) != _registered_domain(page_url):
        return None
    segments = [segment.casefold() for segment in parsed.path.split("/") if segment]
    marker_indexes = [index for index, segment in enumerate(segments) if segment in CAREER_PATH_MARKERS]
    if not marker_indexes:
        return None
    if not any(index < len(segments) - 1 for index in marker_indexes):
        return None
    title = " ".join(str(anchor_text or "").split()).strip()
    normalized_title = _normalise_text(title)
    if not normalized_title or normalized_title in GENERIC_JOB_ANCHORS or len(title) > 180:
        return None
    clean = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, ""))
    return {"url": clean, "title": title[:180]}


def specific_job_links(page_url: str, html: str, *, limit: int = 20) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    found: dict[str, dict[str, str]] = {}
    for anchor in soup.select("a[href]"):
        item = _specific_job_link(page_url, str(anchor.get("href") or ""), anchor.get_text(" ", strip=True))
        if item:
            found[item["url"]] = item
    return sorted(found.values(), key=lambda item: (item["title"].casefold(), item["url"]))[:limit]


def parse_career_page(url: str, raw: bytes) -> dict[str, Any]:
    html = raw.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    text = trafilatura.extract(html, url=url, include_links=False, include_tables=False, favor_precision=True) or ""
    digest = hashlib.sha256(raw).hexdigest()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    return {
        "url": url,
        "title": title[:500],
        "main_text_excerpt": text[:5000],
        "content_sha256": digest,
        "specific_job_links": specific_job_links(url, html),
    }


def _fetch_html(url: str, *, timeout: float, max_bytes: int) -> tuple[bytes | None, str | None, dict[str, Any]]:
    metrics = {"requests": 0, "bytes": 0, "latencies_ms": []}
    try:
        assert_public_url(url)
        if not _robots_allowed(url, timeout):
            metrics["requests"] += 1
            return None, None, {**metrics, "error": "robots.txt disallows page"}
        metrics["requests"] += 1
        started = time.monotonic()
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
        with SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            elapsed = int((time.monotonic() - started) * 1000)
            final_url = response.geturl()
            content_type = response.headers.get("content-type", "")
        metrics["requests"] += 1
        metrics["latencies_ms"].append(elapsed)
        metrics["bytes"] += len(raw)
        assert_public_url(final_url)
        if len(raw) > max_bytes:
            return None, final_url, {**metrics, "error": "page exceeds byte limit"}
        if "html" not in content_type.casefold():
            return None, final_url, {**metrics, "error": f"unsupported content type: {content_type}"}
        return raw, final_url, metrics
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as exc:
        return None, None, {**metrics, "error": f"{type(exc).__name__}: {str(exc)[:160]}"}
    except Exception as exc:
        return None, None, {**metrics, "error": f"{type(exc).__name__}: {str(exc)[:160]}"}


def fetch_career_pages(
    profile: dict[str, Any],
    *,
    timeout: float = 8.0,
    max_bytes: int = 750_000,
    max_pages: int = 2,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Bounded zero-cost careers fetch for an already exact verified company website."""
    verified = verified_company_site(profile)
    metrics: dict[str, Any] = {"requests": 0, "bytes": 0, "latencies_ms": [], "errors": []}
    if not verified:
        return [], metrics
    homepage_url, _identity = verified
    raw, final_homepage, ops = _fetch_html(homepage_url, timeout=timeout, max_bytes=max_bytes)
    for key in ("requests", "bytes"):
        metrics[key] += int(ops.get(key) or 0)
    metrics["latencies_ms"].extend(ops.get("latencies_ms") or [])
    if ops.get("error"):
        metrics["errors"].append({"url": homepage_url, "error": ops["error"]})
    if not raw or not final_homepage:
        return [], metrics

    links = career_links(final_homepage, raw.decode("utf-8", errors="replace"), limit=max_pages)
    pages: list[dict[str, Any]] = []
    for candidate in links:
        page_raw, final_url, page_ops = _fetch_html(candidate["url"], timeout=timeout, max_bytes=max_bytes)
        for key in ("requests", "bytes"):
            metrics[key] += int(page_ops.get(key) or 0)
        metrics["latencies_ms"].extend(page_ops.get("latencies_ms") or [])
        if page_ops.get("error"):
            metrics["errors"].append({"url": candidate["url"], "error": page_ops["error"]})
        if not page_raw or not final_url or _registered_domain(final_url) != _registered_domain(final_homepage):
            continue
        page = parse_career_page(final_url, page_raw)
        page["discovery_anchor"] = candidate.get("anchor_text")
        pages.append(page)
    return pages, metrics


def workforce_observation(profile: dict[str, Any], pages: list[dict[str, Any]]) -> dict[str, Any] | None:
    verified = verified_company_site(profile)
    if not verified or not pages:
        return None
    _site_url, identity = verified
    page = sorted(pages, key=lambda item: (-len(item.get("specific_job_links") or []), item.get("url") or ""))[0]
    url = str(page.get("url") or "")
    digest = str(page.get("content_sha256") or "")
    if not url.startswith(("http://", "https://")) or len(digest) != 64:
        return None
    job_links = []
    for item in pages:
        job_links.extend(item.get("specific_job_links") or [])
    unique_jobs = {item["url"]: item for item in job_links}
    org = str(profile.get("organisation_number") or "")
    title = str(page.get("title") or page.get("discovery_anchor") or "Company careers page").strip()
    return {
        "id": f"company-site-workforce-{org}-{digest[:16]}",
        "organisation_number": org,
        "platform": "company_site",
        "signal_type": "workforce_snapshot",
        "source_url": url,
        "retrieved_at": (profile.get("evidence") or {}).get("website", {}).get("retrieved_at"),
        "content_sha256": digest,
        "exact_entity": True,
        "identity_proof": [{"type": "website_identity_gate", "score": identity.get("score"), "method": identity.get("method")}],
        "acquisition_mode": "permitted_public_page",
        "rights_status": "approved",
        "source_class": "company_site",
        "evidence_span": title[:1200],
        "metrics": {
            "careers_pages_captured": len(pages),
            "specific_internal_job_links": len(unique_jobs),
            "sample_job_titles": [item["title"] for item in list(unique_jobs.values())[:5]],
            "interpretation": "Company-owned hiring surface; specific link count is not an independently verified vacancy total.",
        },
        "strategy": "jobs_feed_discovery",
    }
