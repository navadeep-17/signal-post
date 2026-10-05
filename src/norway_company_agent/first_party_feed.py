from __future__ import annotations

from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any


GENERIC_TITLES = {
    "news",
    "nyheter",
    "aktuelt",
    "blog",
    "press",
    "presse",
    "home",
    "forside",
    "hello world",
    "sample page",
    "sample post",
}
DATE_TAGS = {"pubdate", "published", "updated", "date"}
CURRENT_ACTIVITY_MAX_AGE_YEARS = 5


def _host(url: str) -> str:
    try:
        return (urllib.parse.urlparse(url).hostname or "").casefold().strip(".")
    except ValueError:
        return ""


def _same_verified_site(url: str, verified_url: str) -> bool:
    candidate = _host(url)
    verified = _host(verified_url)
    if not candidate or not verified:
        return False
    return candidate == verified or candidate.endswith("." + verified) or verified.endswith("." + candidate)


def feed_candidate_urls(verified_url: str, *, limit: int = 2) -> list[str]:
    """Return a tiny deterministic set of same-host feed candidates.

    This is nomination only. A caller must still fetch safely and parse a valid RSS/Atom
    document before retaining any activity fact.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    parsed = urllib.parse.urlparse(str(verified_url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return []
    origin = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/", "", "", ""))
    candidates = [
        urllib.parse.urljoin(origin, "feed/"),
        urllib.parse.urljoin(origin, "rss.xml"),
        urllib.parse.urljoin(origin, "feed.xml"),
        urllib.parse.urljoin(origin, "atom.xml"),
    ]
    out: list[str] = []
    seen: set[str] = set()
    for url in candidates:
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
        if len(out) >= limit:
            break
    return out


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _child_text(node: ET.Element, names: set[str]) -> str:
    for child in list(node):
        if _local_name(child.tag) in names:
            text = " ".join("".join(child.itertext()).split())
            if text:
                return text
    return ""


def _entry_link(node: ET.Element) -> str:
    for child in list(node):
        if _local_name(child.tag) != "link":
            continue
        href = str(child.attrib.get("href") or "").strip()
        rel = str(child.attrib.get("rel") or "alternate").casefold()
        if href and rel in {"", "alternate"}:
            return href
        text = " ".join("".join(child.itertext()).split())
        if text:
            return text
    return ""


def _parse_date(raw: str) -> str | None:
    value = " ".join(str(raw or "").split())
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        parsed = None
    if parsed is None:
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            parsed = None
    if parsed is None:
        match = re.fullmatch(r"(20\d{2})-(\d{2})-(\d{2})", value)
        if not match:
            return None
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.date().isoformat()


def _entry_date(node: ET.Element) -> tuple[str, str, str] | None:
    for child in list(node):
        name = _local_name(child.tag)
        if name not in DATE_TAGS:
            continue
        raw = " ".join("".join(child.itertext()).split())
        parsed = _parse_date(raw)
        if parsed:
            return parsed, f"feed_{name}", raw[:200]
    return None


def _specific_title(value: str) -> bool:
    folded = " ".join(value.casefold().split()).strip(" .!?:;-")
    if not folded or folded in GENERIC_TITLES:
        return False
    return len(re.findall(r"[\wæøåÆØÅ-]+", value, flags=re.UNICODE)) >= 2


def _five_year_cutoff(as_of: date) -> date:
    try:
        return as_of.replace(year=as_of.year - CURRENT_ACTIVITY_MAX_AGE_YEARS)
    except ValueError:
        # 29 February -> 28 February in a non-leap cutoff year.
        return as_of.replace(year=as_of.year - CURRENT_ACTIVITY_MAX_AGE_YEARS, day=28)


def _current_activity_date(value: str, *, as_of_date: date) -> bool:
    try:
        published = date.fromisoformat(value)
    except ValueError:
        return False
    return _five_year_cutoff(as_of_date) <= published <= as_of_date


def parse_company_feed(
    raw: bytes,
    *,
    feed_url: str,
    verified_url: str,
    max_entries: int = 5,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Parse current dated same-site RSS/Atom entries from a verified company domain.

    The feed itself is evidence. Feed discovery does not change company identity: callers
    may use this only after the website domain has independently passed the exact-company
    gate. Cross-domain entries, generic CMS placeholders, future dates and entries older
    than the repository's five-year current-activity window are discarded.
    """
    if max_entries < 1:
        raise ValueError("max_entries must be positive")
    if not _same_verified_site(feed_url, verified_url):
        return {"status": "rejected", "reason": "feed URL is outside verified company site", "entries": []}
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        return {"status": "invalid", "reason": f"xml_parse_error:{type(exc).__name__}", "entries": []}

    root_name = _local_name(root.tag)
    if root_name == "rss":
        candidates = [node for node in root.iter() if _local_name(node.tag) == "item"]
        feed_type = "rss"
    elif root_name == "feed":
        candidates = [node for node in root.iter() if _local_name(node.tag) == "entry"]
        feed_type = "atom"
    else:
        return {"status": "invalid", "reason": f"unsupported_feed_root:{root_name}", "entries": []}

    current_date = as_of_date or datetime.now(timezone.utc).date()
    entries: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for node in candidates:
        title = _child_text(node, {"title"})
        link = _entry_link(node)
        if not link:
            continue
        link = urllib.parse.urljoin(feed_url, link)
        if link in seen_urls or not _same_verified_site(link, verified_url):
            continue
        date_info = _entry_date(node)
        if not date_info or not _specific_title(title):
            continue
        published_date, method, raw_date = date_info
        if not _current_activity_date(published_date, as_of_date=current_date):
            continue
        seen_urls.add(link)
        entries.append(
            {
                "title": title[:500],
                "url": link,
                "published_date": published_date,
                "date_extraction_method": method,
                "date_evidence": raw_date,
                "evidence_span": (
                    f"{title}; published date {published_date}; feed date evidence {method}: {raw_date}"
                )[:1000],
            }
        )
        if len(entries) >= max_entries:
            break

    return {
        "status": "available" if entries else "empty",
        "feed_type": feed_type,
        "feed_url": feed_url,
        "entries": entries,
    }


def fetch_verified_activity_feed(
    verified_url: str,
    *,
    timeout: float = 6.0,
    max_bytes: int = 500_000,
    max_entries: int = 5,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Spend one two-request slot on `/feed/` for an already verified company site.

    Production deliberately tries only the consumed-screen winner (`/feed/`). Robots plus
    one feed GET therefore cost at most two logical site requests. Redirects remain under
    the same SSRF-safe bounded opener used by homepage discovery. The returned evidence
    stores only parsed current dated same-site entries and the feed snapshot hash, never raw XML.
    """
    # Local imports avoid coupling the pure parser to the website discovery module.
    from .evidence import evidence
    from .final_site_discovery import BOUNDED_SAFE_OPENER, _robots_allowed
    from .website import USER_AGENT, assert_public_url

    candidates = feed_candidate_urls(verified_url, limit=1)
    metrics: dict[str, Any] = {"requests": 0, "bytes": 0, "latencies_ms": []}
    if not candidates:
        return (
            evidence(
                "website_activity_feed",
                "not_found",
                "verified_company_activity_feed",
                str(verified_url or ""),
                note="Verified website URL cannot nominate a same-site feed candidate",
            ),
            metrics,
        )

    candidate_url = candidates[0]
    try:
        assert_public_url(candidate_url)
    except ValueError as exc:
        return (
            evidence(
                "website_activity_feed",
                "blocked",
                "verified_company_activity_feed",
                candidate_url,
                note=str(exc),
            ),
            metrics,
        )

    allowed, robots_requests = _robots_allowed(candidate_url, timeout)
    metrics["requests"] += robots_requests
    if not allowed:
        return (
            evidence(
                "website_activity_feed",
                "blocked",
                "verified_company_activity_feed",
                candidate_url,
                note="robots.txt disallows this user agent",
            ),
            metrics,
        )

    request = urllib.request.Request(
        candidate_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml;q=0.9,*/*;q=0.1",
        },
    )
    started = time.monotonic()
    metrics["requests"] += 1
    try:
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            final_url = response.geturl()
            assert_public_url(final_url)
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["bytes"] += len(raw)
        if len(raw) > max_bytes:
            return (
                evidence(
                    "website_activity_feed",
                    "blocked",
                    "verified_company_activity_feed",
                    final_url,
                    note="Activity feed exceeds byte limit",
                ),
                metrics,
            )

        parsed = parse_company_feed(
            raw,
            feed_url=final_url,
            verified_url=verified_url,
            max_entries=max_entries,
        )
        digest = hashlib.sha256(raw).hexdigest()
        if parsed.get("status") != "available" or not parsed.get("entries"):
            return (
                evidence(
                    "website_activity_feed",
                    "not_found",
                    "verified_company_activity_feed",
                    final_url,
                    value={
                        "verified_website_url": verified_url,
                        "feed_type": parsed.get("feed_type"),
                        "entries": [],
                    },
                    note=str(parsed.get("reason") or "Feed contains no qualified current dated same-site entries"),
                    content_sha256=digest,
                ),
                metrics,
            )

        return (
            evidence(
                "website_activity_feed",
                "available",
                "verified_company_activity_feed",
                final_url,
                value={
                    "verified_website_url": verified_url,
                    "feed_type": parsed.get("feed_type"),
                    "entries": list(parsed.get("entries") or []),
                },
                note="Bounded current first-party RSS/Atom snapshot from an exact-verified company website",
                content_sha256=digest,
            ),
            metrics,
        )
    except urllib.error.HTTPError as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        status = "not_found" if exc.code in {404, 410} else "source_error"
        return (
            evidence(
                "website_activity_feed",
                status,
                "verified_company_activity_feed",
                candidate_url,
                note=f"HTTP {exc.code}",
            ),
            metrics,
        )
    except Exception as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        return (
            evidence(
                "website_activity_feed",
                "source_error",
                "verified_company_activity_feed",
                candidate_url,
                note=f"{type(exc).__name__}: {str(exc)[:180]}",
            ),
            metrics,
        )
