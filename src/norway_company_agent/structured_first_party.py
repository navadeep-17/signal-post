from __future__ import annotations

import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

from bs4 import BeautifulSoup

from .website import _registered_domain, normalize_homepage

NEWS_TERMS = {"news", "press", "aktuelt", "nyheter", "artikler", "article", "articles", "blog", "innsikt", "insights", "media"}
CAREERS_TERMS = {"career", "careers", "karriere", "jobb", "job", "jobs", "stillinger", "stilling", "ledige-stillinger"}
ARTICLE_TYPES = {"Article", "NewsArticle", "BlogPosting"}
JOB_TYPES = {"JobPosting"}


def verified_site_url(profile: dict[str, Any]) -> str | None:
    """Return the independently verified company site URL or None.

    M2 must never bootstrap identity. It operates only on a website record that already
    passed the existing exact-company publication gate.
    """
    website = (profile.get("evidence") or {}).get("website") or {}
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return None
    candidate = value.get("final_url") or website.get("source_url") or profile.get("website")
    normalized = normalize_homepage(str(candidate or ""))
    return normalized


def _same_registered_domain(candidate_url: str, verified_url: str) -> bool:
    try:
        candidate = normalize_homepage(candidate_url)
        verified = normalize_homepage(verified_url)
        if not candidate or not verified:
            return False
        return bool(_registered_domain(candidate)) and _registered_domain(candidate) == _registered_domain(verified)
    except Exception:
        return False


def _clean_same_domain_url(raw_url: str, *, base_url: str, verified_url: str) -> str | None:
    absolute = urllib.parse.urljoin(base_url, str(raw_url or "").strip())
    parsed = urllib.parse.urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    clean = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))
    if not _same_registered_domain(clean, verified_url):
        return None
    return clean


def classify_first_party_url(url: str) -> str | None:
    """Classify a URL only for bounded discovery prioritisation, never as a fact."""
    parsed = urllib.parse.urlparse(str(url or ""))
    tokens = [token for token in re.split(r"[^a-z0-9æøå]+", urllib.parse.unquote(parsed.path).casefold()) if token]
    token_set = set(tokens)
    if token_set & CAREERS_TERMS:
        return "careers_or_jobs"
    if token_set & NEWS_TERMS:
        return "news_or_article"
    return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _child_text(node: ET.Element, name: str) -> str:
    wanted = name.casefold()
    for child in list(node):
        if _local_name(child.tag) == wanted:
            return " ".join(str(child.text or "").split())
    return ""


def parse_sitemap_xml(xml_text: str, *, sitemap_url: str, verified_url: str, limit: int = 60) -> dict[str, Any]:
    """Parse a sitemap/index into same-domain discovery candidates.

    Sitemap entries are nomination metadata only. They do not establish publication,
    activity, hiring or article semantics until the destination page is fetched.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    if not _same_registered_domain(sitemap_url, verified_url):
        return {"kind": "invalid", "nested_sitemaps": [], "surface_candidates": []}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {"kind": "invalid", "nested_sitemaps": [], "surface_candidates": []}

    root_kind = _local_name(root.tag)
    nested: list[str] = []
    surfaces: list[dict[str, Any]] = []
    seen_nested: set[str] = set()
    seen_surfaces: set[str] = set()

    if root_kind == "sitemapindex":
        for node in list(root):
            if _local_name(node.tag) != "sitemap":
                continue
            loc = _child_text(node, "loc")
            clean = _clean_same_domain_url(loc, base_url=sitemap_url, verified_url=verified_url)
            if not clean or clean in seen_nested:
                continue
            seen_nested.add(clean)
            nested.append(clean)
            if len(nested) >= limit:
                break
        return {"kind": "sitemapindex", "nested_sitemaps": nested, "surface_candidates": []}

    if root_kind != "urlset":
        return {"kind": "invalid", "nested_sitemaps": [], "surface_candidates": []}

    for node in list(root):
        if _local_name(node.tag) != "url":
            continue
        loc = _child_text(node, "loc")
        clean = _clean_same_domain_url(loc, base_url=sitemap_url, verified_url=verified_url)
        if not clean or clean in seen_surfaces:
            continue
        surface_kind = classify_first_party_url(clean)
        if not surface_kind:
            continue
        seen_surfaces.add(clean)
        surfaces.append({
            "url": clean,
            "surface_kind": surface_kind,
            "lastmod": _child_text(node, "lastmod") or None,
            "discovered_via": "sitemap",
        })
        if len(surfaces) >= limit:
            break
    return {"kind": "urlset", "nested_sitemaps": [], "surface_candidates": surfaces}


def parse_feed_xml(xml_text: str, *, feed_url: str, verified_url: str, limit: int = 30) -> list[dict[str, Any]]:
    """Parse RSS/Atom entries as same-domain article/update candidates."""
    if limit < 1:
        raise ValueError("limit must be positive")
    if not _same_registered_domain(feed_url, verified_url):
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node in root.iter():
        node_kind = _local_name(node.tag)
        if node_kind not in {"item", "entry"}:
            continue

        title = _child_text(node, "title")
        published = (
            _child_text(node, "pubDate")
            or _child_text(node, "published")
            or _child_text(node, "updated")
            or _child_text(node, "date")
        )
        link_value = ""
        for child in list(node):
            if _local_name(child.tag) != "link":
                continue
            href = str(child.attrib.get("href") or "").strip()
            rel = str(child.attrib.get("rel") or "alternate").casefold()
            if href and rel in {"alternate", ""}:
                link_value = href
                break
            if not href and child.text:
                link_value = str(child.text).strip()
                break
        clean = _clean_same_domain_url(link_value, base_url=feed_url, verified_url=verified_url)
        if not clean or clean in seen:
            continue
        seen.add(clean)
        entries.append({
            "url": clean,
            "title": title[:500],
            "published": published or None,
            "surface_kind": "news_or_article",
            "discovered_via": "rss_or_atom",
        })
        if len(entries) >= limit:
            break
    return entries


def discover_feed_links(html: str, *, page_url: str, verified_url: str, limit: int = 4) -> list[str]:
    """Return same-domain RSS/Atom links declared by a verified first-party page."""
    if limit < 1:
        raise ValueError("limit must be positive")
    soup = BeautifulSoup(html, "lxml")
    feeds: list[str] = []
    seen: set[str] = set()
    for node in soup.select('link[rel~="alternate"][href]'):
        media_type = str(node.get("type") or "").casefold()
        if media_type not in {"application/rss+xml", "application/atom+xml", "application/feed+json"}:
            continue
        clean = _clean_same_domain_url(str(node.get("href") or ""), base_url=page_url, verified_url=verified_url)
        if not clean or clean in seen:
            continue
        seen.add(clean)
        feeds.append(clean)
        if len(feeds) >= limit:
            break
    return feeds


def _jsonld_nodes(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    roots: list[Any] = []
    for node in soup.select('script[type="application/ld+json"]'):
        raw = node.string or node.get_text("", strip=True)
        if not raw:
            continue
        try:
            roots.append(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            continue

    found: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            found.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for root in roots:
        walk(root)
    return found


def _types(node: dict[str, Any]) -> set[str]:
    raw = node.get("@type")
    values = raw if isinstance(raw, list) else [raw]
    return {str(value) for value in values if value}


def _structured_url(node: dict[str, Any], page_url: str) -> str:
    raw = node.get("url")
    if isinstance(raw, dict):
        raw = raw.get("@id")
    if not raw:
        entity = node.get("mainEntityOfPage")
        if isinstance(entity, dict):
            raw = entity.get("@id") or entity.get("url")
        elif isinstance(entity, str):
            raw = entity
    return str(raw or page_url)


def extract_structured_surfaces(html: str, *, page_url: str, verified_url: str, limit: int = 20) -> list[dict[str, Any]]:
    """Extract same-domain Article/NewsArticle/BlogPosting/JobPosting metadata.

    These records are structured discovery observations only. M3/M4 apply stricter
    publication requirements before any job or company update becomes a canonical fact.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    if not _same_registered_domain(page_url, verified_url):
        return []

    surfaces: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for node in _jsonld_nodes(html):
        kinds = _types(node)
        is_article = bool(kinds & ARTICLE_TYPES)
        is_job = bool(kinds & JOB_TYPES)
        if not is_article and not is_job:
            continue
        clean = _clean_same_domain_url(_structured_url(node, page_url), base_url=page_url, verified_url=verified_url)
        if not clean:
            continue
        surface_kind = "structured_job" if is_job else "structured_article"
        key = (surface_kind, clean)
        if key in seen:
            continue
        seen.add(key)
        headline = str(node.get("headline") or node.get("title") or node.get("name") or "").strip()
        item: dict[str, Any] = {
            "url": clean,
            "surface_kind": surface_kind,
            "title": headline[:500],
            "discovered_via": "jsonld",
        }
        if is_article:
            item["date_published"] = str(node.get("datePublished") or "").strip() or None
            item["date_modified"] = str(node.get("dateModified") or "").strip() or None
        else:
            item["date_posted"] = str(node.get("datePosted") or "").strip() or None
            item["valid_through"] = str(node.get("validThrough") or "").strip() or None
            hiring = node.get("hiringOrganization")
            if isinstance(hiring, dict):
                item["hiring_organisation_name"] = str(hiring.get("name") or "").strip()[:500] or None
        surfaces.append(item)
        if len(surfaces) >= limit:
            break
    return surfaces
