from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

from bs4 import BeautifulSoup

from .final_site_discovery import BOUNDED_SAFE_OPENER, _robots_allowed
from .website import USER_AGENT, _registered_domain, assert_public_url

ACTIVITY_TERMS = (
    "nyheter",
    "aktuelt",
    "pressemeldinger",
    "presse",
    "news",
    "blogg",
    "blog",
    "insights",
    "innsikt",
    "press",
    "media",
)
ARTICLE_TYPES = {"article", "newsarticle", "blogposting"}
MAX_ACTIVITY_ITEMS = 5
MAX_EXPERIMENT_LOGICAL_REQUESTS = 4


def _normalise_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat().replace("+00:00", "Z")
    except ValueError:
        pass
    if len(text) >= 10:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return parsed.isoformat().replace("+00:00", "Z")
        except ValueError:
            return None
    return None


def _same_registered_domain(url: str, expected_domain: str) -> bool:
    return bool(expected_domain and _registered_domain(url) == expected_domain)


def _canonical_same_domain_url(base_url: str, href: str, expected_domain: str) -> str | None:
    try:
        absolute = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(absolute)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if not _same_registered_domain(absolute, expected_domain):
        return None
    path = parsed.path or "/"
    lowered = path.casefold()
    if any(lowered.endswith(suffix) for suffix in (".pdf", ".jpg", ".jpeg", ".png", ".webp", ".zip")):
        return None
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def activity_navigation_links(base_url: str, soup: BeautifulSoup, *, limit: int = 8) -> list[str]:
    """Return deterministic same-domain activity/news navigation links.

    Only links explicitly declared by the fetched page are candidates. No guessed `/news`,
    `/blog`, or similar paths are synthesized.
    """

    expected_domain = _registered_domain(base_url)
    if not expected_domain:
        return []
    ranked: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for node in soup.select("a[href]"):
        href = str(node.get("href") or "").strip()
        if not href:
            continue
        candidate = _canonical_same_domain_url(base_url, href, expected_domain)
        if not candidate or candidate.rstrip("/") == base_url.rstrip("/") or candidate in seen:
            continue
        parsed = urllib.parse.urlparse(candidate)
        path_text = urllib.parse.unquote(parsed.path).casefold()
        anchor_text = " ".join(node.get_text(" ", strip=True).casefold().split())
        haystack = f"{path_text} {anchor_text}"
        matched_index = next((index for index, term in enumerate(ACTIVITY_TERMS) if term in haystack), None)
        if matched_index is None:
            continue
        seen.add(candidate)
        ranked.append((matched_index, len(parsed.path), candidate))
    ranked.sort()
    return [url for _, _, url in ranked[:limit]]


def _jsonld_nodes(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _jsonld_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _jsonld_nodes(child)


def _jsonld_type_matches(value: Any) -> bool:
    types = value if isinstance(value, list) else [value]
    return any(str(item or "").casefold() in ARTICLE_TYPES for item in types)


def _structured_activity_items(base_url: str, soup: BeautifulSoup, expected_domain: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        raw = str(script.string or script.get_text() or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        for node in _jsonld_nodes(payload):
            if not _jsonld_type_matches(node.get("@type")):
                continue
            title = " ".join(str(node.get("headline") or node.get("name") or "").split())
            published_at = _normalise_date(node.get("datePublished") or node.get("dateCreated"))
            if len(title) < 4 or not published_at:
                continue
            raw_url = node.get("url")
            if isinstance(raw_url, dict):
                raw_url = raw_url.get("@id")
            if not raw_url:
                main_entity = node.get("mainEntityOfPage")
                if isinstance(main_entity, dict):
                    raw_url = main_entity.get("@id") or main_entity.get("url")
                elif isinstance(main_entity, str):
                    raw_url = main_entity
            item_url = _canonical_same_domain_url(base_url, str(raw_url or ""), expected_domain) if raw_url else None
            items.append(
                {
                    "title": title[:500],
                    "published_at": published_at,
                    "item_url": item_url,
                    "extraction_method": "jsonld_article",
                }
            )
    return items


def _html_activity_items(base_url: str, soup: BeautifulSoup, expected_domain: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for article in soup.select("article"):
        time_node = article.select_one("time[datetime]")
        if time_node is None:
            continue
        published_at = _normalise_date(time_node.get("datetime"))
        if not published_at:
            continue
        heading = article.select_one("h1, h2, h3, h4")
        link = (heading.select_one("a[href]") if heading else None) or article.select_one("a[href]")
        title = " ".join((heading.get_text(" ", strip=True) if heading else (link.get_text(" ", strip=True) if link else "")).split())
        if len(title) < 4:
            continue
        item_url = None
        if link is not None:
            item_url = _canonical_same_domain_url(base_url, str(link.get("href") or ""), expected_domain)
        items.append(
            {
                "title": title[:500],
                "published_at": published_at,
                "item_url": item_url,
                "extraction_method": "html_article_time",
            }
        )
    return items


def dated_activity_items(base_url: str, soup: BeautifulSoup, *, limit: int = MAX_ACTIVITY_ITEMS) -> list[dict[str, Any]]:
    """Extract only explicitly dated first-party article/news/blog listing items."""

    expected_domain = _registered_domain(base_url)
    if not expected_domain:
        return []
    combined = [
        *_structured_activity_items(base_url, soup, expected_domain),
        *_html_activity_items(base_url, soup, expected_domain),
    ]
    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in combined:
        key = (
            str(item.get("title") or "").casefold(),
            str(item.get("published_at") or ""),
            str(item.get("item_url") or ""),
        )
        deduped[key] = item
    return sorted(
        deduped.values(),
        key=lambda item: (str(item.get("published_at") or ""), str(item.get("title") or "")),
        reverse=True,
    )[:limit]


def _fetch_html_page(
    url: str,
    *,
    timeout: float = 6.0,
    max_bytes: int = 750_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    metrics: dict[str, Any] = {"requests": 0, "bytes": 0, "latencies_ms": []}
    try:
        assert_public_url(url)
    except ValueError as exc:
        return {"status": "blocked", "source_url": url, "note": str(exc)}, metrics

    allowed, robots_requests = _robots_allowed(url, timeout)
    metrics["requests"] += robots_requests
    if not allowed:
        return {"status": "blocked", "source_url": url, "note": "robots.txt disallows this user agent"}, metrics

    started = time.monotonic()
    metrics["requests"] += 1
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    try:
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            final_url = response.geturl()
            assert_public_url(final_url)
            content_type = str(response.headers.get("content-type", ""))
        elapsed = int((time.monotonic() - started) * 1000)
        metrics["latencies_ms"].append(elapsed)
        metrics["bytes"] += len(raw)
        if len(raw) > max_bytes:
            return {"status": "blocked", "source_url": url, "note": "HTML page exceeds byte limit"}, metrics
        if "html" not in content_type.casefold():
            return {"status": "source_error", "source_url": url, "note": f"Unsupported content type: {content_type}"}, metrics
        html = raw.decode("utf-8", errors="replace")
        return {
            "status": "available",
            "source_url": final_url,
            "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "content_sha256": hashlib.sha256(raw).hexdigest(),
            "soup": BeautifulSoup(html, "lxml"),
        }, metrics
    except urllib.error.HTTPError as exc:
        elapsed = int((time.monotonic() - started) * 1000)
        metrics["latencies_ms"].append(elapsed)
        return {"status": "not_found" if exc.code in {404, 410} else "source_error", "source_url": url, "note": f"HTTP {exc.code}"}, metrics
    except Exception as exc:
        elapsed = int((time.monotonic() - started) * 1000)
        metrics["latencies_ms"].append(elapsed)
        return {"status": "source_error", "source_url": url, "note": f"{type(exc).__name__}: {str(exc)[:180]}"}, metrics


def _add_metrics(total: dict[str, Any], item: dict[str, Any]) -> None:
    total["requests"] += int(item.get("requests") or 0)
    total["bytes"] += int(item.get("bytes") or 0)
    total["latencies_ms"].extend(int(value) for value in item.get("latencies_ms") or [] if value is not None)


def _observation_rows(
    profile: dict[str, Any],
    *,
    website: dict[str, Any],
    homepage_url: str,
    homepage_sha256: str,
    activity_url: str,
    activity_page: dict[str, Any],
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    org = str(profile.get("organisation_number") or "")
    identity = (website.get("value") or {}).get("identity_assessment") or {}
    observations: list[dict[str, Any]] = []
    for item in items:
        title = str(item.get("title") or "")
        published_at = str(item.get("published_at") or "")
        item_url = str(item.get("item_url") or "") or None
        material = f"{org}|{activity_url}|{title}|{published_at}|{item_url or ''}|{activity_page.get('content_sha256')}"
        observations.append(
            {
                "id": "company-site-activity-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24],
                "organisation_number": org,
                "platform": "company_site",
                "signal_type": "public_post",
                "source_url": activity_page.get("source_url"),
                "retrieved_at": activity_page.get("retrieved_at"),
                "content_sha256": activity_page.get("content_sha256"),
                "exact_entity": True,
                "identity_proof": [
                    {
                        "type": "website_identity_gate",
                        "status": identity.get("status"),
                        "score": identity.get("score"),
                        "method": identity.get("method"),
                    },
                    {
                        "type": "verified_homepage_declared_activity_link",
                        "source_url": homepage_url,
                        "content_sha256": homepage_sha256,
                        "activity_url": activity_url,
                    },
                    {
                        "type": "same_registered_domain",
                        "registered_domain": _registered_domain(homepage_url),
                    },
                ],
                "acquisition_mode": "permitted_public_page",
                "rights_status": "approved",
                "source_class": "company_site",
                "evidence_span": f'Company-owned activity page lists "{title}" with published date {published_at}.',
                "published_at": published_at,
                "title": title,
                "item_url": item_url,
                "metrics": {
                    "identity_score": identity.get("score"),
                    "claim_scope": "Dated item explicitly listed on a verified company-owned activity page; article body was not fetched.",
                    "extraction_method": item.get("extraction_method"),
                },
                "strategy": "verified_company_activity_listing_v1",
            }
        )
    return observations


def probe_company_activity(
    profile: dict[str, Any],
    *,
    timeout: float = 6.0,
    fetcher: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = _fetch_html_page,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Experimental H2b probe over an already-qualified website.

    The experiment deliberately refetches the homepage to recover declared activity links.
    This costs up to four logical requests (homepage robots+GET, activity-page robots+GET)
    and is *not* the final production integration. Promotion is only viable for profiles
    whose existing production site path has two unused requests, allowing homepage link
    capture to move into the already-paid initial fetch later without raising the ceiling.
    """

    total: dict[str, Any] = {
        "requests": 0,
        "bytes": 0,
        "latencies_ms": [],
        "candidate_links": [],
        "selected_activity_url": None,
        "dated_items": 0,
        "status": "not_applicable",
    }
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    org = str(profile.get("organisation_number") or "")
    if website.get("status") != "available" or not identity.get("publishable") or len(org) != 9 or not org.isdigit():
        return [], total

    homepage_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    homepage_sha256 = str(value.get("content_sha256") or website.get("content_sha256") or "").strip()
    expected_domain = _registered_domain(homepage_url)
    if not homepage_url or not expected_domain or len(homepage_sha256) != 64:
        return [], total

    total["status"] = "attempted"
    homepage, metrics = fetcher(homepage_url, timeout=timeout)
    _add_metrics(total, metrics)
    if homepage.get("status") != "available" or not _same_registered_domain(str(homepage.get("source_url") or ""), expected_domain):
        total["status"] = "homepage_unavailable"
        return [], total

    links = activity_navigation_links(str(homepage.get("source_url") or homepage_url), homepage["soup"])
    total["candidate_links"] = links
    if not links:
        total["status"] = "no_activity_link"
        return [], total

    selected = links[0]
    total["selected_activity_url"] = selected
    activity_page, metrics = fetcher(selected, timeout=timeout)
    _add_metrics(total, metrics)
    if total["requests"] > MAX_EXPERIMENT_LOGICAL_REQUESTS:
        raise RuntimeError(f"H2b experimental activity probe exceeded logical request ceiling: {total['requests']}")
    if activity_page.get("status") != "available":
        total["status"] = "activity_page_unavailable"
        return [], total
    final_activity_url = str(activity_page.get("source_url") or "")
    if not _same_registered_domain(final_activity_url, expected_domain):
        total["status"] = "activity_page_cross_domain"
        return [], total

    items = dated_activity_items(final_activity_url, activity_page["soup"])
    total["dated_items"] = len(items)
    if not items:
        total["status"] = "no_dated_items"
        return [], total

    total["status"] = "qualified_items"
    observations = _observation_rows(
        profile,
        website=website,
        homepage_url=homepage_url,
        homepage_sha256=homepage_sha256,
        activity_url=selected,
        activity_page=activity_page,
        items=items,
    )
    return observations, total
