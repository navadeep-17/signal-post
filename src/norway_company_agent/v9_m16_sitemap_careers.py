from __future__ import annotations

import hashlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from typing import Any

from .evidence import evidence
from .final_site_discovery import BOUNDED_SAFE_OPENER
from .website import USER_AGENT, assert_public_url

MAX_ROBOTS_BYTES = 256_000
MAX_SITEMAP_BYTES = 1_000_000

CAREERS_PATH_RE = re.compile(
    r"/(?:careers?|karriere|jobs?|jobber|stillinger|ledige-stillinger|"
    r"vacancies|vacancy|jobb-hos-oss|jobbe-hos-oss|work-with-us|join-us)/?$",
    re.I,
)


def _host(url: str) -> str:
    try:
        host = (urllib.parse.urlparse(url).hostname or "").casefold().rstrip(".")
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _same_verified_host(candidate: str, verified_url: str) -> bool:
    a = _host(candidate)
    b = _host(verified_url)
    return bool(a and b and a == b)


def _local_name(tag: str) -> str:
    return str(tag or "").rsplit("}", 1)[-1].casefold()


def _sitemap_directives(robots_text: str, *, robots_url: str, verified_url: str) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in robots_text.splitlines():
        match = re.match(r"^\s*sitemap\s*:\s*(\S+)\s*$", raw, flags=re.I)
        if not match:
            continue
        candidate = urllib.parse.urljoin(robots_url, match.group(1).strip())
        try:
            assert_public_url(candidate)
        except ValueError:
            continue
        if not _same_verified_host(candidate, verified_url) or candidate in seen:
            continue
        seen.add(candidate)
        rows.append(candidate)
    return sorted(rows)


def _careers_candidates_from_sitemap(
    raw: bytes,
    *,
    sitemap_url: str,
    verified_url: str,
) -> dict[str, Any]:
    """Extract generic same-host careers surfaces from one urlset.

    Sitemap indexes are deliberately not recursed. lastmod is deliberately ignored:
    sitemap/index timestamps are not publication-date evidence.
    """
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        return {
            "status": "invalid",
            "reason": f"xml_parse_error:{type(exc).__name__}",
            "candidates": [],
        }

    root_name = _local_name(root.tag)
    if root_name == "sitemapindex":
        return {
            "status": "not_found",
            "reason": "sitemap_index_not_recursed",
            "candidates": [],
        }
    if root_name != "urlset":
        return {
            "status": "invalid",
            "reason": f"unsupported_sitemap_root:{root_name}",
            "candidates": [],
        }

    found: dict[str, dict[str, str]] = {}
    for node in root.iter():
        if _local_name(node.tag) != "url":
            continue
        loc = ""
        for child in list(node):
            if _local_name(child.tag) == "loc":
                loc = " ".join("".join(child.itertext()).split())
                break
        if not loc:
            continue
        absolute = urllib.parse.urljoin(sitemap_url, loc)
        try:
            parsed = urllib.parse.urlparse(absolute)
            assert_public_url(absolute)
        except (ValueError, urllib.error.URLError):
            continue
        if not _same_verified_host(absolute, verified_url):
            continue
        normalized = urllib.parse.urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path or "/", "", "", "")
        )
        decoded_path = urllib.parse.unquote(parsed.path or "/")
        marker = CAREERS_PATH_RE.search(decoded_path)
        if not marker:
            continue
        found[normalized] = {
            "url": normalized,
            "marker": marker.group(0).strip("/").casefold(),
        }

    candidates = sorted(
        found.values(),
        key=lambda item: (
            len(urllib.parse.urlparse(item["url"]).path),
            item["url"],
        ),
    )
    return {
        "status": "available" if candidates else "not_found",
        "reason": None if candidates else "no_generic_same_host_careers_surface",
        "candidates": candidates[:4],
    }


def fetch_verified_sitemap_careers(
    verified_url: str,
    *,
    verified_website_content_sha256: str,
    identity_assessment: dict[str, Any],
    timeout: float = 6.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Spend the existing verified-site spare slot on robots plus one sitemap.

    This function is nomination/evidence for a careers-surface presence claim only.
    It never fetches the listed careers page and never creates hiring intent, a specific
    job, or dated activity. The exact website identity remains authoritative.
    """
    metrics: dict[str, Any] = {"requests": 0, "bytes": 0, "latencies_ms": []}
    verified = str(verified_url or "").strip()
    if not verified or not identity_assessment.get("publishable"):
        return (
            evidence(
                "website_sitemap_careers",
                "not_found",
                "verified_company_sitemap_careers",
                verified,
                note="Exact publishable verified website is required before sitemap discovery.",
            ),
            metrics,
        )

    try:
        assert_public_url(verified)
        parsed = urllib.parse.urlparse(verified)
    except ValueError as exc:
        return (
            evidence(
                "website_sitemap_careers",
                "blocked",
                "verified_company_sitemap_careers",
                verified,
                note=str(exc),
            ),
            metrics,
        )

    robots_url = urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, "/robots.txt", "", "", "")
    )
    started = time.monotonic()
    try:
        assert_public_url(robots_url)
        request = urllib.request.Request(
            robots_url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/plain,*/*;q=0.1"},
        )
        metrics["requests"] += 1
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            robots_raw = response.read(MAX_ROBOTS_BYTES + 1)
            robots_final_url = response.geturl()
            assert_public_url(robots_final_url)
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["bytes"] += len(robots_raw)
        if len(robots_raw) > MAX_ROBOTS_BYTES:
            return (
                evidence(
                    "website_sitemap_careers",
                    "blocked",
                    "verified_company_sitemap_careers",
                    robots_final_url,
                    note="robots.txt exceeds byte limit",
                ),
                metrics,
            )
        robots_text = robots_raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        return (
            evidence(
                "website_sitemap_careers",
                "not_found" if exc.code in {404, 410} else "source_error",
                "verified_company_sitemap_careers",
                robots_url,
                note=f"robots.txt HTTP {exc.code}; deeper sitemap crawl abstained",
            ),
            metrics,
        )
    except Exception as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        return (
            evidence(
                "website_sitemap_careers",
                "source_error",
                "verified_company_sitemap_careers",
                robots_url,
                note=f"{type(exc).__name__}: {str(exc)[:180]}; deeper sitemap crawl abstained",
            ),
            metrics,
        )

    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_final_url)
    parser.parse(robots_text.splitlines())

    directives = _sitemap_directives(
        robots_text,
        robots_url=robots_final_url,
        verified_url=verified,
    )
    if directives:
        sitemap_url = directives[0]
        nomination = "robots_sitemap_directive"
    else:
        origin = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/", "", "", ""))
        sitemap_url = urllib.parse.urljoin(origin, "sitemap.xml")
        nomination = "default_same_host_sitemap_xml"

    try:
        assert_public_url(sitemap_url)
    except ValueError as exc:
        return (
            evidence(
                "website_sitemap_careers",
                "blocked",
                "verified_company_sitemap_careers",
                sitemap_url,
                note=str(exc),
            ),
            metrics,
        )
    if not _same_verified_host(sitemap_url, verified):
        return (
            evidence(
                "website_sitemap_careers",
                "blocked",
                "verified_company_sitemap_careers",
                sitemap_url,
                note="Sitemap candidate is outside exact verified host.",
            ),
            metrics,
        )
    if not parser.can_fetch(USER_AGENT, sitemap_url):
        return (
            evidence(
                "website_sitemap_careers",
                "blocked",
                "verified_company_sitemap_careers",
                sitemap_url,
                note="robots.txt disallows sitemap request for this user agent",
            ),
            metrics,
        )

    request = urllib.request.Request(
        sitemap_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/xml,text/xml,text/plain;q=0.8,*/*;q=0.1",
        },
    )
    started = time.monotonic()
    metrics["requests"] += 1
    try:
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(MAX_SITEMAP_BYTES + 1)
            final_url = response.geturl()
            assert_public_url(final_url)
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["bytes"] += len(raw)
        if len(raw) > MAX_SITEMAP_BYTES:
            return (
                evidence(
                    "website_sitemap_careers",
                    "blocked",
                    "verified_company_sitemap_careers",
                    final_url,
                    note="Sitemap exceeds byte limit",
                ),
                metrics,
            )
        if not _same_verified_host(final_url, verified):
            return (
                evidence(
                    "website_sitemap_careers",
                    "blocked",
                    "verified_company_sitemap_careers",
                    final_url,
                    note="Sitemap redirect left exact verified host.",
                ),
                metrics,
            )

        parsed_sitemap = _careers_candidates_from_sitemap(
            raw,
            sitemap_url=final_url,
            verified_url=verified,
        )
        digest = hashlib.sha256(raw).hexdigest()
        candidates = list(parsed_sitemap.get("candidates") or [])
        if not candidates:
            return (
                evidence(
                    "website_sitemap_careers",
                    "not_found",
                    "verified_company_sitemap_careers",
                    final_url,
                    value={
                        "verified_website_url": verified,
                        "verified_website_content_sha256": verified_website_content_sha256,
                        "sitemap_url": final_url,
                        "sitemap_nomination": nomination,
                        "careers_candidates": [],
                        "lastmod_used_as_publication_date": False,
                    },
                    note=str(parsed_sitemap.get("reason") or "No generic same-host careers surface in sitemap."),
                    content_sha256=digest,
                ),
                metrics,
            )

        chosen = candidates[0]
        return (
            evidence(
                "website_sitemap_careers",
                "available",
                "verified_company_sitemap_careers",
                final_url,
                value={
                    "verified_website_url": verified,
                    "verified_website_content_sha256": verified_website_content_sha256,
                    "sitemap_url": final_url,
                    "sitemap_nomination": nomination,
                    "careers_url": chosen["url"],
                    "marker": chosen["marker"],
                    "careers_candidates": candidates,
                    "identity_assessment": dict(identity_assessment),
                    "lastmod_used_as_publication_date": False,
                    "claim_scope": (
                        "Exact verified company site's same-host sitemap lists a generic careers/hiring surface. "
                        "This proves careers-surface presence only; it does not assert recruitment intent, "
                        "an active vacancy, or a publication date."
                    ),
                },
                note="Bounded same-host sitemap snapshot from an exact-verified company website.",
                content_sha256=digest,
            ),
            metrics,
        )
    except urllib.error.HTTPError as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        return (
            evidence(
                "website_sitemap_careers",
                "not_found" if exc.code in {404, 410} else "source_error",
                "verified_company_sitemap_careers",
                sitemap_url,
                note=f"Sitemap HTTP {exc.code}",
            ),
            metrics,
        )
    except Exception as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        return (
            evidence(
                "website_sitemap_careers",
                "source_error",
                "verified_company_sitemap_careers",
                sitemap_url,
                note=f"{type(exc).__name__}: {str(exc)[:180]}",
            ),
            metrics,
        )
