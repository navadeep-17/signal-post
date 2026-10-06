from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from .job_surface_signal import same_company_host


ACTIVE_PATTERNS: tuple[tuple[str, re.Pattern[str], bool], ...] = (
    ("no_vi_soker", re.compile(r"\bvi\s+s[øo]ker(?:\s+etter)?\b", re.I), True),
    ("no_ledige_stillinger", re.compile(r"\bledige?\s+stillinger?\b", re.I), False),
    ("no_rekrutterer", re.compile(r"\bvi\s+rekrutterer\b", re.I), True),
    ("en_we_are_hiring", re.compile(r"\bwe(?:\s+are|'re|’re)\s+hiring\b", re.I), False),
    ("en_looking_for", re.compile(r"\bwe(?:\s+are|'re|’re)\s+looking\s+for\b", re.I), True),
    ("en_open_positions", re.compile(r"\bopen\s+positions?\b", re.I), False),
    ("en_vacancies", re.compile(r"\bvacanc(?:y|ies)\b", re.I), False),
)

PEOPLE_HINT_RE = re.compile(
    r"\b(?:"
    r"medarbeider(?:e|ne)?|kollega(?:er)?|ansatt(?:e)?|personell|kandidat(?:er)?|"
    r"talent(?:er|fulle)?|team(?:et)?|stilling(?:er)?|jobb(?:er)?|søknad|"
    r"tekniker(?:e)?|mekaniker(?:e)?|ingeniør(?:er)?|utvikler(?:e)?|"
    r"rådgiver(?:e)?|selger(?:e)?|leder(?:e)?|sjåfør(?:er)?|operatør(?:er)?|"
    r"employee(?:s)?|staff|candidate(?:s)?|talent|team|role(?:s)?|job(?:s)?|"
    r"engineer(?:s)?|developer(?:s)?|technician(?:s)?|mechanic(?:s)?|"
    r"manager(?:s)?|consultant(?:s)?|sales|operator(?:s)?"
    r")\b",
    re.I,
)

NEGATIVE_RE = re.compile(
    r"(?:"
    r"ingen\s+ledige?\s+stillinger?|"
    r"har\s+ikke\s+ledige?\s+stillinger?|"
    r"vi\s+s[øo]ker\s+ikke|"
    r"not\s+hiring|"
    r"no\s+open\s+positions?|"
    r"no\s+vacanc(?:y|ies)"
    r")",
    re.I,
)

GENERIC_ONLY_RE = re.compile(
    r"^\s*(?:jobb\s+hos\s+oss|karriere|career(?:s)?|join\s+our\s+team)\s*[.!?]?\s*$",
    re.I,
)


def hiring_intent_match(text: str) -> dict[str, str] | None:
    """Return explicit company-authored recruitment intent or abstain.

    This deliberately does not prove that a specific vacancy is currently open.
    Generic careers/navigation language is insufficient.
    """
    if not text or GENERIC_ONLY_RE.fullmatch(text):
        return None
    for kind, pattern, needs_people_hint in ACTIVE_PATTERNS:
        for match in pattern.finditer(text):
            start = max(0, match.start() - 140)
            end = min(len(text), match.end() + 260)
            span = " ".join(text[start:end].split())
            if NEGATIVE_RE.search(span):
                continue
            if needs_people_hint and not PEOPLE_HINT_RE.search(span):
                continue
            return {
                "match_type": kind,
                "evidence_span": span[:500],
            }
    return None


def _verified_website(profile: dict[str, Any]) -> dict[str, Any] | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") if isinstance(website.get("value"), dict) else {}
    assessment = value.get("identity_assessment") if isinstance(value.get("identity_assessment"), dict) else {}
    if website.get("status") != "available" or not assessment.get("publishable"):
        return None
    if not str(website.get("retrieved_at") or "").strip():
        return None
    return website


def _page_row(
    *,
    url: Any,
    text: Any,
    digest: Any,
    retrieved_at: Any,
    provenance: str,
) -> dict[str, str] | None:
    page_url = str(url or "").strip()
    page_text = str(text or "").strip()
    page_hash = str(digest or "").strip()
    retrieved = str(retrieved_at or "").strip()
    if (
        not page_url.startswith(("http://", "https://"))
        or not page_text
        or len(page_hash) != 64
        or not retrieved
    ):
        return None
    return {
        "source_url": page_url,
        "text": page_text,
        "content_sha256": page_hash,
        "retrieved_at": retrieved,
        "provenance": provenance,
    }


def _homepage_pages(website: dict[str, Any]) -> list[dict[str, str]]:
    value = website.get("value") or {}
    final_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    retrieved_at = website.get("retrieved_at")
    rows: list[dict[str, str]] = []
    homepage = _page_row(
        url=final_url,
        text=value.get("main_text_excerpt"),
        digest=value.get("content_sha256") or website.get("content_sha256"),
        retrieved_at=retrieved_at,
        provenance="exact_verified_homepage",
    )
    if homepage:
        rows.append(homepage)

    for page in value.get("pages") or []:
        if not isinstance(page, dict):
            continue
        page_url = str(page.get("url") or "").strip()
        if not same_company_host(page_url, final_url):
            continue
        item = _page_row(
            url=page_url,
            text=page.get("main_text_excerpt"),
            digest=page.get("content_sha256"),
            retrieved_at=retrieved_at,
            provenance="retained_same_site_page",
        )
        if item:
            rows.append(item)
    return rows


def _retained_careers_surface(profile: dict[str, Any], website: dict[str, Any]) -> list[dict[str, str]]:
    surface = ((profile.get("evidence") or {}).get("website_careers_surface") or {})
    if surface.get("status") != "available" or surface.get("source_type") != "verified_company_careers_surface_candidate":
        return []

    website_value = website.get("value") or {}
    website_url = str(website_value.get("final_url") or website.get("source_url") or "").strip()
    surface_value = surface.get("value") or {}
    surface_url = str(surface_value.get("final_url") or surface.get("source_url") or "").strip()
    if not website_url or not surface_url or not same_company_host(website_url, surface_url):
        return []

    nominated = {
        str(item.get("url") or "").rstrip("/")
        for item in website_value.get("careers_links") or []
        if isinstance(item, dict) and item.get("url")
    }
    if surface_url.rstrip("/") not in nominated:
        return []

    item = _page_row(
        url=surface_url,
        text=surface_value.get("main_text_excerpt"),
        digest=surface_value.get("content_sha256") or surface.get("content_sha256"),
        retrieved_at=surface.get("retrieved_at") or website.get("retrieved_at"),
        provenance="homepage_nominated_careers_surface",
    )
    return [item] if item else []


def extract_company_authored_hiring_intent(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract at most one explicit first-party hiring-intent observation.

    The source must be an already-qualified exact company site or an already-retained,
    homepage-nominated same-site careers surface. No network request occurs here.
    """
    website = _verified_website(profile)
    if website is None:
        return []

    website_url = str((website.get("value") or {}).get("final_url") or website.get("source_url") or "")
    candidates = [*_homepage_pages(website), *_retained_careers_surface(profile, website)]
    seen: set[tuple[str, str]] = set()
    for page in candidates:
        key = (page["source_url"], page["content_sha256"])
        if key in seen:
            continue
        seen.add(key)
        if not same_company_host(page["source_url"], website_url):
            continue
        match = hiring_intent_match(page["text"])
        if not match:
            continue
        return [
            {
                "source_url": page["source_url"],
                "retrieved_at": page["retrieved_at"],
                "content_sha256": page["content_sha256"],
                "match_type": match["match_type"],
                "evidence_span": match["evidence_span"],
                "provenance": page["provenance"],
                "claim_scope": (
                    "Exact company-authored first-party text expresses recruitment intent. "
                    "This is not a claim that a specific vacancy is currently open."
                ),
                "network_requests_added": 0,
            }
        ]
    return []
