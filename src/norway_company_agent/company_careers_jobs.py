from __future__ import annotations

import hashlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup
import extruct
import trafilatura

from .evidence import utc_now
from .external_footprint import publishable_observation
from .final_site_discovery import BOUNDED_SAFE_OPENER, _robots_allowed
from .website import USER_AGENT, _registered_domain, assert_public_url

CAREER_TERMS = (
    "ledige stillinger",
    "ledige-stillinger",
    "ledig stilling",
    "jobb hos oss",
    "jobbe hos oss",
    "karriere",
    "karrierer",
    "careers",
    "career",
    "vacancies",
    "open positions",
    "open-positions",
    "join us",
    "join-us",
    "jobs",
)
GENERIC_JOB_TITLES = {
    "career",
    "careers",
    "job",
    "jobs",
    "jobb",
    "jobber",
    "karriere",
    "karrierer",
    "ledige stillinger",
    "vacancies",
    "open positions",
    "join us",
    "jobb hos oss",
    "jobbe hos oss",
}


def _verified_company_site(profile: dict[str, Any]) -> dict[str, Any] | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not assessment.get("publishable"):
        return None
    final_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    if not final_url or not _registered_domain(final_url):
        return None
    return website


def discover_career_links(base_url: str, html: str, *, limit: int = 3) -> list[str]:
    """Return strong, same-registered-domain careers/vacancy links from a verified homepage.

    Weak standalone words such as Norwegian ``jobber`` are intentionally excluded because
    they commonly mean "works" rather than a hiring page.
    """

    base_domain = _registered_domain(base_url)
    if not base_domain:
        return []
    soup = BeautifulSoup(html, "lxml")
    ranked: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "").strip()
        if not href:
            continue
        absolute = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(absolute)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        if _registered_domain(absolute) != base_domain:
            continue
        normalized = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))
        if normalized.rstrip("/") == base_url.rstrip("/") or normalized in seen:
            continue
        path_text = urllib.parse.unquote(parsed.path).replace("_", " ").casefold()
        anchor_text = " ".join(anchor.get_text(" ", strip=True).split()).casefold()
        haystack = f"{path_text} {anchor_text}"
        match = next((index for index, term in enumerate(CAREER_TERMS) if term in haystack), None)
        if match is None:
            continue
        seen.add(normalized)
        ranked.append((match, len(parsed.path), normalized))
    ranked.sort(key=lambda row: (row[0], row[1], row[2]))
    return [row[2] for row in ranked[:limit]]


def fetch_html(url: str, *, timeout: float = 6.0, max_bytes: int = 1_000_000) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Fetch robots + one bounded HTML page with the final evaluator's SSRF/redirect policy."""

    metrics: dict[str, Any] = {"requests": 0, "bytes": 0, "latencies_ms": []}
    try:
        assert_public_url(url)
        allowed, robots_requests = _robots_allowed(url, timeout)
        metrics["requests"] += robots_requests
        if not allowed:
            return None, {**metrics, "status": "robots_blocked"}
        started = time.monotonic()
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        )
        metrics["requests"] += 1
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            elapsed = int((time.monotonic() - started) * 1000)
            final_url = response.geturl()
            assert_public_url(final_url)
            content_type = response.headers.get("content-type", "")
        metrics["bytes"] += len(raw)
        metrics["latencies_ms"].append(elapsed)
        if len(raw) > max_bytes:
            return None, {**metrics, "status": "oversized"}
        if "html" not in content_type.casefold():
            return None, {**metrics, "status": "unsupported_content_type"}
        html = raw.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        text = trafilatura.extract(
            html,
            url=final_url,
            include_links=False,
            include_tables=False,
            favor_precision=True,
        ) or ""
        return {
            "url": final_url,
            "html": html,
            "title": soup.title.get_text(" ", strip=True)[:500] if soup.title else "",
            "main_text_excerpt": text[:10_000],
            "content_sha256": hashlib.sha256(raw).hexdigest(),
            "retrieved_at": utc_now(),
        }, {**metrics, "status": "available"}
    except urllib.error.HTTPError as exc:
        return None, {**metrics, "status": f"http_{exc.code}"}
    except Exception as exc:
        return None, {**metrics, "status": "error", "error": f"{type(exc).__name__}: {str(exc)[:160]}"}


def _jobposting_nodes(html: str, base_url: str) -> list[dict[str, Any]]:
    try:
        structured = extruct.extract(html, base_url=base_url, syntaxes=["json-ld", "microdata"])
    except Exception:
        return []
    found: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            kind = node.get("@type") or node.get("type")
            kinds = kind if isinstance(kind, list) else [kind]
            if any(str(value).casefold() == "jobposting" for value in kinds if value is not None):
                found.append(node)
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(structured)
    return found[:30]


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def _clean_text(value: Any, limit: int = 400) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = str(value)
    soup = BeautifulSoup(str(value), "lxml")
    return " ".join(soup.get_text(" ", strip=True).split())[:limit]


def _location_text(node: dict[str, Any]) -> str | None:
    location = node.get("jobLocation")
    values = location if isinstance(location, list) else [location]
    parts: list[str] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        address = item.get("address") or {}
        if isinstance(address, dict):
            for key in ("addressLocality", "addressRegion", "addressCountry"):
                value = address.get(key)
                if value:
                    parts.append(str(value))
    text = ", ".join(dict.fromkeys(parts))
    return text[:300] or None


def extract_structured_job_observations(
    profile: dict[str, Any],
    career_page: dict[str, Any],
    *,
    now: datetime | None = None,
    max_observations: int = 5,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Publish only concrete structured JobPosting records from a verified company domain."""

    website = _verified_company_site(profile)
    if website is None:
        return [], []
    org = str(profile.get("organisation_number") or "")
    website_value = website.get("value") or {}
    website_url = str(website_value.get("final_url") or website.get("source_url") or "")
    career_url = str(career_page.get("url") or "")
    if not career_url or _registered_domain(career_url) != _registered_domain(website_url):
        return [], []

    current = now or datetime.now(timezone.utc)
    observations: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for node in _jobposting_nodes(str(career_page.get("html") or ""), career_url):
        title = _clean_text(node.get("title") or node.get("name"), 240)
        if len(title) < 3 or title.casefold() in GENERIC_JOB_TITLES:
            rejected.append({"reason": "missing_or_generic_title", "title": title})
            continue
        valid_through = _parse_datetime(node.get("validThrough"))
        if valid_through and valid_through < current:
            rejected.append({"reason": "expired", "title": title, "valid_through": valid_through.isoformat()})
            continue
        date_posted = _parse_datetime(node.get("datePosted"))
        if date_posted and date_posted > current.replace(microsecond=0):
            rejected.append({"reason": "future_date_posted", "title": title})
            continue

        employment_type = node.get("employmentType")
        if isinstance(employment_type, list):
            employment_type = ", ".join(str(value) for value in employment_type if value)
        description = _clean_text(node.get("description"), 500)
        location = _location_text(node)
        evidence_bits = [f"Open role: {title}"]
        if date_posted:
            evidence_bits.append(f"datePosted={date_posted.date().isoformat()}")
        if valid_through:
            evidence_bits.append(f"validThrough={valid_through.date().isoformat()}")
        if location:
            evidence_bits.append(f"location={location}")
        if description:
            evidence_bits.append(description[:220])
        digest = str(career_page.get("content_sha256") or "")
        material = f"{org}|{career_url}|{title}|{date_posted}|{valid_through}|{digest}"
        observation = {
            "id": "company-job-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24],
            "organisation_number": org,
            "platform": "company_site",
            "signal_type": "job_posting",
            "source_url": career_url,
            "retrieved_at": career_page.get("retrieved_at"),
            "content_sha256": digest,
            "exact_entity": True,
            "identity_proof": [
                {
                    "type": "verified_company_website",
                    "url": website_url,
                    "identity_score": (website_value.get("identity_assessment") or {}).get("score"),
                },
                {
                    "type": "same_registered_domain_careers_page",
                    "registered_domain": _registered_domain(career_url),
                },
            ],
            "acquisition_mode": "permitted_public_page",
            "rights_status": "approved",
            "source_class": "company_owned_job_posting",
            "evidence_span": "; ".join(evidence_bits)[:1000],
            "effective_at": (date_posted or _parse_datetime(career_page.get("retrieved_at")) or current).isoformat(),
            "metrics": {
                "job_title": title,
                "date_posted": date_posted.date().isoformat() if date_posted else None,
                "valid_through": valid_through.date().isoformat() if valid_through else None,
                "employment_type": str(employment_type)[:200] if employment_type else None,
                "location": location,
                "scope": "company_owned_careers_page",
            },
            "strategy": "company_owned_structured_jobposting_v1",
        }
        if publishable_observation(observation):
            observations.append(observation)
        else:
            rejected.append({"reason": "observation_validation_failed", "title": title})
        if len(observations) >= max_observations:
            break
    return observations, rejected


def fallback_role_candidates(html: str, base_url: str, *, limit: int = 20) -> list[dict[str, str]]:
    """Diagnostic-only role-like links. These are never publication candidates in H2f-v1."""

    soup = BeautifulSoup(html, "lxml")
    generic = {value.casefold() for value in GENERIC_JOB_TITLES}
    found: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for anchor in soup.select("a[href]"):
        title = " ".join(anchor.get_text(" ", strip=True).split())
        if not 4 <= len(title) <= 160 or title.casefold() in generic:
            continue
        href = urllib.parse.urljoin(base_url, str(anchor.get("href") or "").strip())
        path = urllib.parse.urlparse(href).path.casefold()
        haystack = f"{title.casefold()} {path}"
        if not any(token in haystack for token in ("stilling", "vacan", "/job", "/career", "position")):
            continue
        key = (title.casefold(), href)
        if key in seen:
            continue
        seen.add(key)
        found.append({"title": title, "url": href})
        if len(found) >= limit:
            break
    return found
