from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlparse

LEGAL_NAME_NOISE = {
    "as",
    "asa",
    "sa",
    "nuf",
    "gfs",
    "ba",
    "ans",
    "da",
    "enk",
    "konsern",
}
GENERIC_ROLE_TITLES = {
    "jobb",
    "jobber",
    "jobs",
    "karriere",
    "career",
    "careers",
    "ledige stillinger",
    "stillinger",
    "vacancies",
    "vacancy",
}
SHORT_DATE_RE = re.compile(r"\b([0-3]?\d)[./-]([01]?\d)[./-](\d{2})\b")
LONG_DATE_RE = re.compile(r"\b([0-3]?\d)[./-]([01]?\d)[./-](20\d{2})\b")
ISO_DATE_RE = re.compile(r"\b(20\d{2})-([01]?\d)-([0-3]?\d)\b")


def _fold(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _host(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").casefold().rstrip(".")
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _same_company_host(left: str, right: str) -> bool:
    a = _host(left)
    b = _host(right)
    if not a or not b:
        return False
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def _name_tokens(value: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9æøå]+", str(value or "").casefold(), flags=re.UNICODE)
    return [token for token in tokens if token not in LEGAL_NAME_NOISE and len(token) > 1]


def _employer_matches_target(target_name: str, candidate: dict[str, Any]) -> bool:
    target = _name_tokens(target_name)
    if not target:
        return False
    explicit = str(candidate.get("hiring_organisation") or "").strip()
    context = explicit or str(candidate.get("employer_context") or "")
    context_tokens = set(_name_tokens(context))
    return all(token in context_tokens for token in target)


def _specific_title(title: str) -> bool:
    folded = _fold(title).strip(" -|:")
    if not folded or folded in GENERIC_ROLE_TITLES:
        return False
    return len(re.findall(r"[\wæøåÆØÅ-]+", title, flags=re.UNICODE)) >= 2


def _parse_deadline(raw: Any) -> date | None:
    text = " ".join(str(raw or "").split())
    match = ISO_DATE_RE.search(text)
    if match:
        parts = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        try:
            return date(*parts)
        except ValueError:
            return None
    match = LONG_DATE_RE.search(text)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            return None
    match = SHORT_DATE_RE.search(text)
    if match:
        try:
            return date(2000 + int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            return None
    return None


def _retrieval_date(record: dict[str, Any], fallback: dict[str, Any]) -> date | None:
    raw = record.get("retrieved_at") or fallback.get("retrieved_at")
    if not raw:
        return None
    text = str(raw).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc).date()
    except (ValueError, TypeError):
        return None


def _surface_is_homepage_nominated(website: dict[str, Any], surface: dict[str, Any]) -> bool:
    if surface.get("status") != "available" or surface.get("source_type") != "verified_company_careers_surface_candidate":
        return False
    website_value = website.get("value") or {}
    surface_value = surface.get("value") or {}
    website_url = str(website_value.get("final_url") or website.get("source_url") or "").strip()
    surface_url = str(surface_value.get("final_url") or surface.get("source_url") or "").strip()
    if not website_url or not surface_url or not _same_company_host(website_url, surface_url):
        return False
    nominated = {
        str(item.get("url") or "").rstrip("/")
        for item in (website_value.get("careers_links") or [])
        if isinstance(item, dict) and item.get("url")
    }
    return surface_url.rstrip("/") in nominated


def extract_current_first_party_jobs(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Project current role-card/JobPosting observations from exact first-party pages.

    No network access occurs here. A role is eligible only when its source page belongs to
    an already exact website, has an explicit current/future deadline, and locally names
    the target employer. Group/subsidiary cards therefore abstain unless the target legal
    entity itself is identified in that role observation.
    """
    evidence_map = profile.get("evidence") or {}
    website = evidence_map.get("website") or {}
    website_value = website.get("value") or {}
    assessment = website_value.get("identity_assessment") or {}
    if website.get("status") != "available" or not assessment.get("publishable"):
        return []

    target_name = str(profile.get("name") or profile.get("legal_name") or "").strip()
    if not target_name:
        return []

    sources: list[tuple[dict[str, Any], str]] = [(website, "exact_verified_homepage")]
    surface = evidence_map.get("website_careers_surface") or {}
    if _surface_is_homepage_nominated(website, surface):
        sources.append((surface, "homepage_nominated_careers_surface"))

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record, provenance in sources:
        value = record.get("value") or {}
        source_url = str(value.get("final_url") or record.get("source_url") or "").strip()
        if not source_url:
            continue
        observed_on = _retrieval_date(record, website)
        if observed_on is None:
            continue
        content_hash = str(record.get("content_sha256") or value.get("content_sha256") or "").strip()
        for candidate in value.get("job_listing_candidates") or []:
            if not isinstance(candidate, dict):
                continue
            title = " ".join(str(candidate.get("title") or "").split())
            role_url = str(candidate.get("role_url") or candidate.get("application_url") or "").strip()
            deadline = _parse_deadline(candidate.get("deadline_raw"))
            if not (_specific_title(title) and role_url.startswith(("http://", "https://")) and deadline):
                continue
            if deadline < observed_on:
                continue
            if not _employer_matches_target(target_name, candidate):
                continue
            if role_url in seen:
                continue
            seen.add(role_url)
            application_url = str(candidate.get("application_url") or role_url).strip()
            evidence_span = (
                f"{title}; target employer identified on exact first-party hiring surface; "
                f"application deadline {deadline.isoformat()}; role/application URL {application_url}"
            )[:1000]
            rows.append(
                {
                    "title": title,
                    "url": role_url,
                    "application_url": application_url,
                    "deadline": deadline.isoformat(),
                    "content_sha256": content_hash,
                    "evidence_url": source_url,
                    "retrieved_at": record.get("retrieved_at") or website.get("retrieved_at"),
                    "evidence_span": evidence_span,
                    "claim_scope": (
                        "Current role explicitly listed by the exact verified employer on a first-party homepage/careers surface; "
                        "specific title, current deadline, employer match and role/application URL required."
                    ),
                    "provenance": provenance,
                }
            )

    rows.sort(key=lambda item: (item["deadline"], item["title"].casefold(), item["url"]))
    return rows
