from __future__ import annotations

import json
import re
import urllib.parse
from datetime import date, datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

from .website import _registered_domain

ATS_PROVIDERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("teamtailor", re.compile(r"(?:^|\.)teamtailor\.com$", re.I)),
    ("greenhouse", re.compile(r"^(?:boards|job-boards|jobs)\.greenhouse\.io$", re.I)),
    ("lever", re.compile(r"^jobs\.lever\.co$", re.I)),
    ("workday", re.compile(r"(?:^|\.)(?:myworkdayjobs|myworkdaysite)\.com$", re.I)),
    ("jobbnorge", re.compile(r"(?:^|\.)jobbnorge\.no$", re.I)),
    ("smartrecruiters", re.compile(r"^jobs\.smartrecruiters\.com$", re.I)),
    ("recruitee", re.compile(r"(?:^|\.)recruitee\.com$", re.I)),
)

CORPORATE_SUFFIXES = {
    "as", "asa", "ans", "da", "sa", "enk", "nuf", "ba", "a/s", "a.s", "limited", "ltd", "inc", "corp", "corporation",
}
APPLY_TERMS = ("apply", "søk", "sok", "søk nå", "send søknad", "application")


def _host(url: str) -> str:
    try:
        return (urllib.parse.urlparse(url).hostname or "").casefold().rstrip(".")
    except ValueError:
        return ""


def _same_registered_domain(left: str, right: str) -> bool:
    try:
        a = _registered_domain(left)
        b = _registered_domain(right)
        return bool(a and b and a.casefold() == b.casefold())
    except Exception:
        return False


def ats_provider(url: str) -> str | None:
    host = _host(url)
    if not host:
        return None
    for provider, pattern in ATS_PROVIDERS:
        if pattern.search(host):
            return provider
    return None


def _clean_http_url(raw: str, *, base_url: str) -> str | None:
    absolute = urllib.parse.urljoin(base_url, str(raw or "").strip())
    try:
        parsed = urllib.parse.urlparse(absolute)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, ""))


def _provider_specific_enough(provider: str, url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").casefold()
    parts = [part for part in parsed.path.split("/") if part]

    if provider == "teamtailor":
        # Company-specific Teamtailor deployments commonly use a tenant subdomain.
        return host != "teamtailor.com" and host.count(".") >= 2
    if provider == "greenhouse":
        return len(parts) >= 1
    if provider == "lever":
        return len(parts) >= 1
    if provider == "workday":
        # Workday tenant is carried in a non-root host even when path is locale-only.
        return host.count(".") >= 2 and not host.startswith("www.")
    if provider == "jobbnorge":
        return len(parts) >= 1 or bool(parsed.query)
    if provider == "smartrecruiters":
        return len(parts) >= 1
    if provider == "recruitee":
        return host != "recruitee.com" and host.count(".") >= 2
    return False


def extract_linked_ats_candidates(
    *,
    verified_company_url: str,
    careers_url: str,
    careers_html: str,
    careers_content_sha256: str,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Extract ATS destinations only from an already verified first-party careers page.

    This function does not prove a vacancy. The trusted fact is only that the exact
    company-owned careers surface directly linked to a provider-specific ATS destination.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    if not _same_registered_domain(verified_company_url, careers_url):
        return []
    if len(str(careers_content_sha256 or "")) != 64:
        return []

    soup = BeautifulSoup(careers_html, "lxml")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        url = _clean_http_url(str(anchor.get("href") or ""), base_url=careers_url)
        if not url or url in seen:
            continue
        provider = ats_provider(url)
        if not provider or not _provider_specific_enough(provider, url):
            continue
        seen.add(url)
        anchor_text = " ".join(anchor.get_text(" ", strip=True).split())
        rows.append(
            {
                "url": url,
                "provider": provider,
                "anchor_text": anchor_text[:240],
                "careers_url": careers_url,
                "careers_content_sha256": careers_content_sha256,
                "trusted_link_chain": True,
                "claim_scope": (
                    "An exact verified company-owned careers page directly links to this ATS destination. "
                    "This establishes ATS provenance only; it does not establish an active vacancy."
                ),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _normalised_company_name(value: Any) -> str:
    text = str(value or "").casefold()
    text = text.translate(str.maketrans({"ø": "o", "å": "a", "æ": "ae"}))
    tokens = [token for token in re.findall(r"[a-z0-9]+", text) if token]
    while tokens and tokens[-1] in CORPORATE_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def company_identity_names(profile: dict[str, Any]) -> set[str]:
    values: list[Any] = [profile.get("name")]
    canonical = profile.get("canonical_profile") or {}
    company = canonical.get("company") or {}
    values.extend([company.get("name"), company.get("legal_name")])
    values.extend(profile.get("name_aliases") or [])
    return {name for value in values if (name := _normalised_company_name(value))}


def _hiring_name_matches(profile: dict[str, Any], hiring_name: str) -> bool:
    candidate = _normalised_company_name(hiring_name)
    return bool(candidate and candidate in company_identity_names(profile))


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


def _parse_iso_date(value: Any) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw).date()
    except ValueError:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None


def _application_link(html: str, *, page_url: str, provider: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    for anchor in soup.select("a[href]"):
        text = " ".join(anchor.get_text(" ", strip=True).split()).casefold()
        if not any(term in text for term in APPLY_TERMS):
            continue
        clean = _clean_http_url(str(anchor.get("href") or ""), base_url=page_url)
        if not clean:
            continue
        # A role can send the final application action to the same ATS provider or the
        # already loaded job page. Unknown third-party application redirects abstain.
        if clean.rstrip("/") == page_url.rstrip("/") or ats_provider(clean) == provider:
            return clean
    return None


def _job_url(node: dict[str, Any], page_url: str) -> str:
    raw: Any = node.get("url")
    if isinstance(raw, dict):
        raw = raw.get("@id") or raw.get("url")
    if not raw:
        raw = page_url
    return _clean_http_url(str(raw), base_url=page_url) or page_url


def _job_location(node: dict[str, Any]) -> dict[str, Any] | None:
    raw = node.get("jobLocation")
    locations = raw if isinstance(raw, list) else [raw]
    for location in locations:
        if not isinstance(location, dict):
            continue
        address = location.get("address")
        if not isinstance(address, dict):
            continue
        item = {
            "street_address": str(address.get("streetAddress") or "").strip() or None,
            "postal_code": str(address.get("postalCode") or "").strip() or None,
            "locality": str(address.get("addressLocality") or "").strip() or None,
            "region": str(address.get("addressRegion") or "").strip() or None,
            "country": str(address.get("addressCountry") or "").strip() or None,
        }
        if any(item.values()):
            return item
    return None


def qualify_job_postings(
    *,
    profile: dict[str, Any],
    ats_candidate: dict[str, Any],
    job_page_url: str,
    job_html: str,
    content_sha256: str,
    as_of: date | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Qualify specific structured jobs from a company-linked ATS page.

    Publication eligibility is deliberately stricter than ATS discovery. The company
    careers page must have established the ATS link, the role page must remain on the
    same ATS provider, the structured employer must match the exact company identity,
    and explicit currentness evidence is required for `publishable=True`.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    if not ats_candidate.get("trusted_link_chain"):
        return []
    provider = str(ats_candidate.get("provider") or "")
    if not provider or ats_provider(str(ats_candidate.get("url") or "")) != provider:
        return []
    if ats_provider(job_page_url) != provider:
        return []
    if len(str(content_sha256 or "")) != 64:
        return []

    today = as_of or datetime.now(timezone.utc).date()
    apply_link = _application_link(job_html, page_url=job_page_url, provider=provider)
    results: list[dict[str, Any]] = []

    for node in _jsonld_nodes(job_html):
        if "JobPosting" not in _types(node):
            continue
        title = " ".join(str(node.get("title") or node.get("name") or "").split())
        hiring = node.get("hiringOrganization")
        hiring_name = str(hiring.get("name") or "").strip() if isinstance(hiring, dict) else ""
        date_posted_raw = str(node.get("datePosted") or "").strip()
        valid_through_raw = str(node.get("validThrough") or "").strip()
        date_posted = _parse_iso_date(date_posted_raw)
        valid_through = _parse_iso_date(valid_through_raw)
        role_url = _job_url(node, job_page_url)

        reasons: list[str] = []
        status = "review"
        publishable = False
        if not title:
            reasons.append("missing specific job title")
            status = "rejected"
        elif not hiring_name or not _hiring_name_matches(profile, hiring_name):
            reasons.append("structured hiring organisation does not exactly match the target company")
            status = "rejected"
        elif ats_provider(role_url) != provider:
            reasons.append("structured role URL leaves the company-linked ATS provider")
            status = "rejected"
        elif valid_through is not None and valid_through < today:
            reasons.append("structured validThrough date is in the past")
            status = "expired"
        elif date_posted is None:
            reasons.append("missing or invalid datePosted; currentness not sufficiently evidenced")
        elif valid_through is None:
            reasons.append("validThrough absent; role remains a currentness-review candidate")
        else:
            status = "exact_active"
            publishable = True
            reasons.append("company-linked ATS JobPosting has matching employer, explicit datePosted and non-expired validThrough")

        results.append(
            {
                "status": status,
                "publishable": publishable,
                "provider": provider,
                "title": title or None,
                "job_url": role_url,
                "apply_url": apply_link,
                "hiring_organisation_name": hiring_name or None,
                "date_posted": date_posted_raw or None,
                "valid_through": valid_through_raw or None,
                "employment_type": node.get("employmentType"),
                "location": _job_location(node),
                "description": " ".join(BeautifulSoup(str(node.get("description") or ""), "lxml").get_text(" ", strip=True).split())[:1200] or None,
                "content_sha256": content_sha256,
                "careers_url": ats_candidate.get("careers_url"),
                "ats_entry_url": ats_candidate.get("url"),
                "trusted_link_chain": True,
                "reasons": reasons,
                "claim_scope": (
                    "A specific ATS JobPosting reached from an exact verified company-owned careers surface. "
                    "Only records marked publishable have explicit non-expired currentness and exact employer alignment."
                ),
            }
        )
        if len(results) >= limit:
            break
    return results
