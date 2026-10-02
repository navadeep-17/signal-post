from __future__ import annotations

import hashlib
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from bs4 import BeautifulSoup
import extruct
import trafilatura

from .company_site_contact import EMAIL_RE, _safe_same_domain_email
from .company_site_social import _safe_profile_url
from .evidence import utc_now
from .final_site_discovery import BOUNDED_SAFE_OPENER, _identity_text_excerpt
from .first_party_activity import extract_strict_first_party_facts
from .identity import assess_social_identity
from .website import USER_AGENT, _registered_domain, _social_links, assert_public_url, structured_social_links

V6D_SCHEMA = "signalpost.verified_site_depth.v1"
MAX_SITEMAP_URLS = 500
MAX_FEED_ENTRIES = 12

CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "contact": ("kontakt", "contact"),
    "about": ("om-oss", "om_oss", "om oss", "about", "company", "firma"),
    "team": ("team", "people", "ansatte", "medarbeidere", "ledelse", "management", "leadership", "styret"),
    "locations": ("locations", "lokasjoner", "avdelinger", "butikker", "kontor", "offices", "office"),
    "news": ("news", "nyheter", "aktuelt", "press", "presse", "blog"),
    "careers": ("career", "careers", "jobs", "jobb", "jobber", "stilling", "stillinger", "ledige-stillinger", "vacanc"),
}
LEADERSHIP_MARKERS = (
    "ceo", "chief executive", "managing director", "daglig leder", "administrerende direktør",
    "administrerende direktor", "chief financial", "cfo", "chief technology", "cto", "chief operating",
    "coo", "chair", "chairman", "chairwoman", "styreleder", "founder", "grunnlegger", "partner",
)
JOB_DETAIL_QUERY_KEYS = {"job", "jobid", "job_id", "position", "positionid", "vacancy", "opening", "gh_jid"}
GENERIC_UPDATE_TITLES = {"news", "nyheter", "aktuelt", "blog", "press", "presse"}


def _clean_url(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, ""))


def _same_registered_domain(url: str, verified_url: str) -> bool:
    try:
        return bool(_registered_domain(url) and _registered_domain(url) == _registered_domain(verified_url))
    except Exception:
        return False


def _page_category(url: str, anchor_text: str = "") -> str | None:
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return None
    haystack = urllib.parse.unquote(f"{parsed.path} {anchor_text}").casefold()
    for category, terms in CATEGORY_TERMS.items():
        if any(term in haystack for term in terms):
            return category
    return None


def _detail_candidate(url: str, category: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False
    segments = [urllib.parse.unquote(part).casefold() for part in parsed.path.split("/") if part]
    if not segments:
        return False
    terms = CATEGORY_TERMS[category]
    positions = [index for index, segment in enumerate(segments) if any(term.strip("/-_ ") in segment for term in terms)]
    if positions and positions[-1] < len(segments) - 1:
        return True
    if category == "careers":
        keys = {key.casefold() for key in urllib.parse.parse_qs(parsed.query, keep_blank_values=False)}
        return bool(keys & JOB_DETAIL_QUERY_KEYS)
    return False


def discover_same_domain_candidates(base_url: str, soup: BeautifulSoup) -> list[dict[str, str]]:
    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for anchor in soup.select("a[href]"):
        absolute = _clean_url(urllib.parse.urljoin(base_url, str(anchor.get("href") or "").strip()))
        if not absolute or absolute in seen or not _same_registered_domain(absolute, base_url):
            continue
        if absolute.rstrip("/") == _clean_url(base_url).rstrip("/"):
            continue
        category = _page_category(absolute, anchor.get_text(" ", strip=True))
        if not category:
            continue
        seen.add(absolute)
        rows.append({"url": absolute, "category": category, "anchor": anchor.get_text(" ", strip=True)[:240], "source": "page_link"})
    order = list(CATEGORY_TERMS)
    rows.sort(key=lambda item: (order.index(item["category"]), len(urllib.parse.urlparse(item["url"]).path), item["url"]))
    return rows


def _structured_nodes(structured: dict[str, Any], wanted: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            kind = node.get("@type")
            kinds = set(kind if isinstance(kind, list) else [kind])
            if kinds & wanted:
                rows.append(node)
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(structured.get("json-ld", []))
    return rows


def _first_isoish_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"\b(20\d{2}-[01]\d-[0-3]\d)(?:[T ][^\s]+)?\b", text)
    if match:
        return match.group(1)
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except Exception:
            pass
    try:
        return parsedate_to_datetime(text).date().isoformat()
    except Exception:
        return None


def _page_published_date(soup: BeautifulSoup, structured: dict[str, Any]) -> str | None:
    for selector, attr in (
        ('meta[property="article:published_time"]', "content"),
        ('meta[name="date"]', "content"),
        ('meta[name="publish-date"]', "content"),
        ('time[datetime]', "datetime"),
    ):
        node = soup.select_one(selector)
        if node:
            value = _first_isoish_date(node.get(attr))
            if value:
                return value
    for node in _structured_nodes(structured, {"Article", "NewsArticle", "BlogPosting"}):
        for key in ("datePublished", "dateCreated"):
            value = _first_isoish_date(node.get(key))
            if value:
                return value
    return None


def _feed_links(base_url: str, soup: BeautifulSoup) -> list[str]:
    found: list[str] = []
    for node in soup.select('link[rel~="alternate"][href]'):
        content_type = str(node.get("type") or "").casefold()
        if "rss" not in content_type and "atom" not in content_type:
            continue
        url = _clean_url(urllib.parse.urljoin(base_url, str(node.get("href") or "")))
        if url and _same_registered_domain(url, base_url) and url not in found:
            found.append(url)
    return found[:2]


def parse_page(url: str, raw: bytes, content_type: str) -> dict[str, Any] | None:
    if "html" not in str(content_type or "").casefold():
        return None
    html = raw.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    structured = extruct.extract(html, base_url=url, syntaxes=["json-ld", "microdata", "opengraph"])
    text = trafilatura.extract(html, url=url, include_links=False, include_tables=False, favor_precision=True) or ""
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    digest = hashlib.sha256(raw).hexdigest()
    identity_text = _identity_text_excerpt(soup)
    social_links = _social_links(url, soup)
    social_links.extend(structured_social_links(structured))
    socials = list({(item["platform"], item["url"]): item for item in social_links}.values())
    emails = sorted({
        match.group(1).strip().casefold()
        for match in EMAIL_RE.finditer("\n".join([identity_text, text]))
        if _safe_same_domain_email(match.group(1), url)
    })[:6]
    return {
        "url": url,
        "category": _page_category(url) or "other",
        "title": title[:500],
        "main_text_excerpt": text[:6000],
        "identity_text_excerpt": identity_text[:5000],
        "content_sha256": digest,
        "social_links": sorted(socials, key=lambda item: (item["platform"], item["url"])),
        "contact_emails": emails,
        "structured_organisations": _structured_nodes(structured, {"Organization", "Corporation", "LocalBusiness", "Store", "Restaurant"})[:20],
        "structured_people": _structured_nodes(structured, {"Person"})[:30],
        "structured_jobs": _structured_nodes(structured, {"JobPosting"})[:30],
        "published_date": _page_published_date(soup, structured),
        "feed_links": _feed_links(url, soup),
        "link_candidates": discover_same_domain_candidates(url, soup)[:80],
    }


def _fetch_robots(verified_url: str, timeout: float) -> tuple[urllib.robotparser.RobotFileParser, dict[str, Any]]:
    parsed = urllib.parse.urlparse(verified_url)
    robots_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    metrics = {"requests": 1, "bytes": 0, "latencies_ms": [], "errors": []}
    started = time.monotonic()
    try:
        assert_public_url(robots_url)
        request = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(250_000)
        metrics["bytes"] += len(raw)
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        parser.parse(raw.decode("utf-8", errors="replace").splitlines())
    except Exception as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["errors"].append(f"robots:{type(exc).__name__}:{str(exc)[:120]}")
        # Match the current final collector: an unavailable robots file permits ordinary GETs,
        # but V6d still records the failure and never leaves the verified registered domain.
        parser.parse([])
    return parser, metrics


def _fetch_bytes(
    url: str,
    *,
    verified_url: str,
    robots: urllib.robotparser.RobotFileParser,
    timeout: float,
    max_bytes: int,
    accept: str,
) -> tuple[bytes | None, str, str, dict[str, Any]]:
    metrics = {"requests": 0, "bytes": 0, "latencies_ms": [], "errors": [], "outside_domain_rejections": 0}
    clean = _clean_url(url)
    if not clean or not _same_registered_domain(clean, verified_url):
        metrics["outside_domain_rejections"] += 1
        return None, clean or url, "", metrics
    try:
        assert_public_url(clean)
    except ValueError as exc:
        metrics["errors"].append(f"blocked:{str(exc)[:120]}")
        return None, clean, "", metrics
    if not robots.can_fetch(USER_AGENT, clean):
        metrics["errors"].append(f"robots_disallow:{clean}")
        return None, clean, "", metrics

    started = time.monotonic()
    metrics["requests"] = 1
    request = urllib.request.Request(clean, headers={"User-Agent": USER_AGENT, "Accept": accept})
    try:
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            final_url = response.geturl()
            content_type = str(response.headers.get("content-type") or "")
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["bytes"] += len(raw)
        if len(raw) > max_bytes:
            metrics["errors"].append(f"oversized:{clean}")
            return None, final_url, content_type, metrics
        if not _same_registered_domain(final_url, verified_url):
            metrics["outside_domain_rejections"] += 1
            metrics["errors"].append(f"redirect_outside_verified_domain:{final_url}")
            return None, final_url, content_type, metrics
        assert_public_url(final_url)
        return raw, final_url, content_type, metrics
    except Exception as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["errors"].append(f"fetch:{type(exc).__name__}:{str(exc)[:140]}")
        return None, clean, "", metrics


def parse_sitemap(raw: bytes, *, sitemap_url: str, verified_url: str) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1].casefold() != "loc":
            continue
        url = _clean_url(str(node.text or "").strip())
        if not url or url in seen or not _same_registered_domain(url, verified_url):
            continue
        category = _page_category(url)
        if not category:
            continue
        seen.add(url)
        rows.append({"url": url, "category": category, "anchor": "", "source": "sitemap"})
        if len(rows) >= MAX_SITEMAP_URLS:
            break
    order = list(CATEGORY_TERMS)
    rows.sort(key=lambda item: (order.index(item["category"]), len(urllib.parse.urlparse(item["url"]).path), item["url"]))
    return rows


def parse_feed(raw: bytes, *, feed_url: str, verified_url: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    entries: list[dict[str, Any]] = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1].casefold() not in {"item", "entry"}:
            continue
        title = ""
        link = ""
        published = None
        for child in list(node):
            tag = child.tag.rsplit("}", 1)[-1].casefold()
            if tag == "title" and not title:
                title = " ".join(str(child.text or "").split())
            elif tag == "link" and not link:
                link = str(child.get("href") or child.text or "").strip()
            elif tag in {"pubdate", "published", "updated", "date"} and not published:
                published = _first_isoish_date(child.text)
        absolute = _clean_url(urllib.parse.urljoin(feed_url, link)) if link else ""
        if not title or not published or not absolute or not _same_registered_domain(absolute, verified_url):
            continue
        entries.append({"title": title[:500], "url": absolute, "published_date": published})
        if len(entries) >= MAX_FEED_ENTRIES:
            break
    return entries


def _location_facts(page: dict[str, Any]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for org in page.get("structured_organisations") or []:
        address = org.get("address") if isinstance(org, dict) else None
        for item in address if isinstance(address, list) else [address]:
            if not isinstance(item, dict):
                continue
            street = str(item.get("streetAddress") or "").strip()
            postal = str(item.get("postalCode") or "").strip()
            locality = str(item.get("addressLocality") or "").strip()
            if not locality or not (street or postal):
                continue
            facts.append({
                "street_address": street or None,
                "postal_code": postal or None,
                "locality": locality,
                "source_url": page["url"],
                "content_sha256": page["content_sha256"],
                "retrieved_at": page.get("retrieved_at"),
            })
    return facts


def _leadership_facts(page: dict[str, Any]) -> list[dict[str, Any]]:
    if page.get("category") not in {"about", "team"}:
        return []
    facts: list[dict[str, Any]] = []
    for person in page.get("structured_people") or []:
        if not isinstance(person, dict):
            continue
        name = " ".join(str(person.get("name") or "").split())
        title = " ".join(str(person.get("jobTitle") or "").split())
        if name and title and any(marker in title.casefold() for marker in LEADERSHIP_MARKERS):
            facts.append({
                "name": name[:300],
                "job_title": title[:300],
                "source_url": page["url"],
                "content_sha256": page["content_sha256"],
                "retrieved_at": page.get("retrieved_at"),
            })
    return facts


def _structured_job_facts(page: dict[str, Any], verified_url: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for job in page.get("structured_jobs") or []:
        if not isinstance(job, dict):
            continue
        title = " ".join(str(job.get("title") or job.get("name") or "").split())
        detail_fields = sum(bool(job.get(key)) for key in ("datePosted", "validThrough", "employmentType", "jobLocation", "description", "hiringOrganization"))
        raw_url = str(job.get("url") or page.get("url") or "").strip()
        url = _clean_url(urllib.parse.urljoin(page["url"], raw_url))
        if len(title.split()) < 2 or detail_fields < 2 or not url or not _same_registered_domain(url, verified_url):
            continue
        facts.append({
            "title": title[:500],
            "url": url,
            "date_posted": _first_isoish_date(job.get("datePosted")),
            "valid_through": _first_isoish_date(job.get("validThrough")),
            "source_url": page["url"],
            "content_sha256": page["content_sha256"],
            "retrieved_at": page.get("retrieved_at"),
            "strategy": "jsonld_jobposting",
        })
    return facts


def _metadata_update_facts(page: dict[str, Any]) -> list[dict[str, Any]]:
    url = str(page.get("url") or "")
    title = " ".join(str(page.get("title") or "").split())
    published = str(page.get("published_date") or "").strip()
    words = re.findall(r"[\wæøåÆØÅ-]+", title, flags=re.UNICODE)
    if page.get("category") != "news" or not published or not _detail_candidate(url, "news"):
        return []
    if not title or title.casefold() in GENERIC_UPDATE_TITLES or len(words) < 2:
        return []
    return [{
        "title": title[:500],
        "url": url,
        "published_date": published,
        "source_url": url,
        "content_sha256": page.get("content_sha256"),
        "retrieved_at": page.get("retrieved_at"),
        "strategy": "first_party_metadata_dated_update",
        "evidence_span": f"{title}; explicit publication date {published} on exact company-owned update detail page"[:1000],
    }]


def extract_depth_facts(
    profile: dict[str, Any],
    pages: list[dict[str, Any]],
    feed_entries: list[dict[str, Any]],
    *,
    retrieved_at: str,
) -> dict[str, list[dict[str, Any]]]:
    website = ((profile.get("evidence") or {}).get("website") or {})
    verified_url = str((website.get("value") or {}).get("final_url") or website.get("source_url") or "")
    contacts: list[dict[str, Any]] = []
    socials: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []
    leadership: list[dict[str, Any]] = []
    structured_jobs: list[dict[str, Any]] = []
    metadata_updates: list[dict[str, Any]] = []
    seen_contacts: set[str] = set()
    seen_socials: set[tuple[str, str]] = set()

    for page in pages:
        page_retrieved = page.get("retrieved_at") or retrieved_at
        for email in page.get("contact_emails") or []:
            if email not in seen_contacts:
                seen_contacts.add(email)
                contacts.append({"email": email, "source_url": page["url"], "content_sha256": page["content_sha256"], "retrieved_at": page_retrieved})
        for link in page.get("social_links") or []:
            assessed = assess_social_identity(profile, link)
            platform = str(assessed.get("platform") or "")
            url = str(assessed.get("url") or "")
            key = (platform, url)
            if key in seen_socials or not assessed.get("publishable") or not _safe_profile_url(platform, url):
                continue
            seen_socials.add(key)
            socials.append({
                "platform": platform,
                "url": url,
                "identity_score": assessed.get("identity_score"),
                "source_url": page["url"],
                "content_sha256": page["content_sha256"],
                "retrieved_at": page_retrieved,
            })
        locations.extend(_location_facts(page))
        leadership.extend(_leadership_facts(page))
        structured_jobs.extend(_structured_job_facts(page, verified_url))
        metadata_updates.extend(_metadata_update_facts(page))

    # Reuse the existing strict text gates on the exact same retained pages.
    temporary = deepcopy(profile)
    temp_website = deepcopy(website)
    temp_value = deepcopy(temp_website.get("value") or {})
    temp_value["pages"] = pages
    temp_website["value"] = temp_value
    temporary.setdefault("evidence", {})["website"] = temp_website
    strict = extract_strict_first_party_facts(temporary)

    jobs = list(structured_jobs)
    job_keys = {(str(item.get("title") or "").casefold(), str(item.get("url") or "")) for item in jobs}
    for item in strict.get("jobs") or []:
        key = (str(item.get("title") or "").casefold(), str(item.get("url") or ""))
        if key not in job_keys:
            job_keys.add(key)
            jobs.append({**item, "source_url": item.get("url"), "retrieved_at": retrieved_at, "strategy": "strict_text_job_detail"})

    updates: list[dict[str, Any]] = []
    update_keys: set[tuple[str, str]] = set()
    for item in [*metadata_updates, *(strict.get("updates") or [])]:
        key = (str(item.get("title") or "").casefold(), str(item.get("url") or ""))
        if key not in update_keys:
            update_keys.add(key)
            strategy = item.get("strategy") or "strict_text_dated_update"
            updates.append({**item, "source_url": item.get("source_url") or item.get("url"), "retrieved_at": item.get("retrieved_at") or retrieved_at, "strategy": strategy})
    for item in feed_entries:
        key = (str(item.get("title") or "").casefold(), str(item.get("url") or ""))
        if key not in update_keys:
            update_keys.add(key)
            updates.append({
                **item,
                "source_url": item.get("feed_url"),
                "content_sha256": item.get("content_sha256"),
                "retrieved_at": item.get("retrieved_at") or retrieved_at,
                "strategy": "first_party_feed_item",
            })

    return {
        "contact_emails": contacts,
        "social_profiles": socials,
        "locations": locations,
        "leadership": leadership,
        "jobs": jobs,
        "updates": updates,
    }


def _merge_metrics(total: dict[str, Any], item: dict[str, Any]) -> None:
    total["requests"] += int(item.get("requests") or 0)
    total["bytes"] += int(item.get("bytes") or 0)
    total["latencies_ms"].extend(int(value) for value in item.get("latencies_ms") or [])
    errors = [str(value) for value in item.get("errors") or []]
    total["errors"].extend(errors)
    total["outside_domain_rejections"] += int(item.get("outside_domain_rejections") or 0)
    total["robots_blocked"] += sum(error.startswith("robots_disallow:") for error in errors)


def crawl_verified_site_depth(
    profile: dict[str, Any],
    *,
    timeout: float = 6.0,
    max_section_pages: int = 4,
    max_detail_pages: int = 2,
    fetch_sitemap: bool = True,
    fetch_feed: bool = True,
    request_allowance: int = 12,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Deepen an already-publishable exact company website without creating identity."""
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    verified_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    verified_domain = _registered_domain(verified_url) if verified_url else ""
    total: dict[str, Any] = {"requests": 0, "bytes": 0, "latencies_ms": [], "errors": [], "outside_domain_rejections": 0, "robots_blocked": 0}
    if website.get("status") != "available" or not identity.get("publishable") or not verified_url or not verified_domain:
        return {"schema": V6D_SCHEMA, "eligible": False, "reason": "website_not_exact_verified", "pages": [], "facts": {}}, total
    if request_allowance < 2:
        return {"schema": V6D_SCHEMA, "eligible": True, "reason": "insufficient_request_allowance", "pages": [], "facts": {}}, total

    robots, robot_metrics = _fetch_robots(verified_url, timeout)
    _merge_metrics(total, robot_metrics)
    if total["requests"] >= request_allowance:
        return {"schema": V6D_SCHEMA, "eligible": True, "reason": "request_allowance_exhausted", "pages": [], "facts": {}}, total

    raw, final_url, content_type, metrics = _fetch_bytes(
        verified_url,
        verified_url=verified_url,
        robots=robots,
        timeout=timeout,
        max_bytes=750_000,
        accept="text/html,application/xhtml+xml",
    )
    _merge_metrics(total, metrics)
    pages: list[dict[str, Any]] = []
    if raw is None:
        return {"schema": V6D_SCHEMA, "eligible": True, "reason": "homepage_refetch_failed", "pages": [], "facts": {}}, total
    homepage = parse_page(final_url, raw, content_type)
    if homepage is None:
        return {"schema": V6D_SCHEMA, "eligible": True, "reason": "homepage_not_html", "pages": [], "facts": {}}, total
    homepage["category"] = "homepage"
    pages.append(homepage)

    candidates = list(homepage.get("link_candidates") or [])
    sitemap_rows: list[dict[str, str]] = []
    if fetch_sitemap and total["requests"] < request_allowance:
        parsed = urllib.parse.urlparse(final_url)
        sitemap_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/sitemap.xml", "", "", ""))
        sitemap_raw, sitemap_final, _, sitemap_metrics = _fetch_bytes(
            sitemap_url,
            verified_url=verified_url,
            robots=robots,
            timeout=timeout,
            max_bytes=1_000_000,
            accept="application/xml,text/xml,*/*;q=0.5",
        )
        _merge_metrics(total, sitemap_metrics)
        if sitemap_raw is not None:
            sitemap_rows = parse_sitemap(sitemap_raw, sitemap_url=sitemap_final, verified_url=verified_url)
            candidates.extend(sitemap_rows)

    chosen: list[dict[str, str]] = []
    chosen_categories: set[str] = set()
    seen_urls: set[str] = {homepage["url"]}
    for candidate in candidates:
        category = str(candidate.get("category") or "")
        url = str(candidate.get("url") or "")
        if category not in CATEGORY_TERMS or category in chosen_categories or url in seen_urls:
            continue
        chosen_categories.add(category)
        seen_urls.add(url)
        chosen.append(candidate)
        if len(chosen) >= max_section_pages:
            break

    section_pages: list[dict[str, Any]] = []
    for candidate in chosen:
        if total["requests"] >= request_allowance:
            break
        raw, page_url, page_type, page_metrics = _fetch_bytes(
            candidate["url"], verified_url=verified_url, robots=robots, timeout=timeout,
            max_bytes=650_000, accept="text/html,application/xhtml+xml",
        )
        _merge_metrics(total, page_metrics)
        page = parse_page(page_url, raw, page_type) if raw is not None else None
        if page is None:
            continue
        page["category"] = candidate["category"]
        page["candidate_source"] = candidate.get("source")
        pages.append(page)
        section_pages.append(page)

    # At most one specific news detail and one specific careers detail page.
    detail_candidates: list[dict[str, str]] = []
    for page in section_pages:
        category = str(page.get("category") or "")
        if category not in {"news", "careers"}:
            continue
        for candidate in page.get("link_candidates") or []:
            url = str(candidate.get("url") or "")
            if str(candidate.get("category") or "") == category and url not in seen_urls and _detail_candidate(url, category):
                detail_candidates.append({"url": url, "category": category, "source": "section_detail_link"})
                seen_urls.add(url)
                break
    detail_candidates.sort(key=lambda item: (0 if item["category"] == "news" else 1, item["url"]))
    for candidate in detail_candidates[:max_detail_pages]:
        if total["requests"] >= request_allowance:
            break
        raw, page_url, page_type, page_metrics = _fetch_bytes(
            candidate["url"], verified_url=verified_url, robots=robots, timeout=timeout,
            max_bytes=650_000, accept="text/html,application/xhtml+xml",
        )
        _merge_metrics(total, page_metrics)
        page = parse_page(page_url, raw, page_type) if raw is not None else None
        if page is not None:
            page["category"] = candidate["category"]
            page["candidate_source"] = candidate["source"]
            pages.append(page)

    feed_entries: list[dict[str, Any]] = []
    feed_candidates: list[str] = []
    for page in pages:
        for url in page.get("feed_links") or []:
            if url not in feed_candidates:
                feed_candidates.append(url)
    if fetch_feed and feed_candidates and total["requests"] < request_allowance:
        feed_raw, feed_final, _, feed_metrics = _fetch_bytes(
            feed_candidates[0], verified_url=verified_url, robots=robots, timeout=timeout,
            max_bytes=750_000, accept="application/rss+xml,application/atom+xml,application/xml,text/xml,*/*;q=0.5",
        )
        _merge_metrics(total, feed_metrics)
        if feed_raw is not None:
            digest = hashlib.sha256(feed_raw).hexdigest()
            feed_entries = [{**item, "feed_url": feed_final, "content_sha256": digest} for item in parse_feed(feed_raw, feed_url=feed_final, verified_url=verified_url)]

    retrieved_at = utc_now()
    for page in pages:
        page["retrieved_at"] = retrieved_at
    for item in feed_entries:
        item["retrieved_at"] = retrieved_at
    facts = extract_depth_facts(profile, pages, feed_entries, retrieved_at=retrieved_at)
    return {
        "schema": V6D_SCHEMA,
        "eligible": True,
        "verified_site_url": verified_url,
        "verified_registered_domain": verified_domain,
        "identity_created_by_v6d": False,
        "pages": pages,
        "sitemap_candidate_count": len(sitemap_rows),
        "feed_entries": feed_entries,
        "facts": facts,
    }, total
