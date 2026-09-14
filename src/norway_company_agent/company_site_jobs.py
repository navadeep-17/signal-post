from __future__ import annotations

import hashlib
import re
import urllib.parse
from typing import Any

from bs4 import BeautifulSoup
import extruct

from .domain_discovery import distinctive_legal_name_tokens
from .website import _registered_domain

CAREER_TERMS = (
    "ledige-stillinger",
    "ledige_stillinger",
    "stillinger",
    "jobb",
    "jobber",
    "karriere",
    "career",
    "careers",
    "jobs",
    "vacancies",
    "vacancy",
)


def career_link_candidates(base_url: str, html: str, *, limit: int = 2) -> list[str]:
    if limit < 1:
        return []
    soup = BeautifulSoup(html, "lxml")
    base = urllib.parse.urlparse(base_url)
    root_domain = _registered_domain(base_url)
    ranked: dict[str, int] = {}
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "").strip()
        if not href:
            continue
        url = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if _registered_domain(url) != root_domain:
            continue
        haystack = f"{parsed.path} {anchor.get_text(' ', strip=True)}".casefold()
        rank = next((index for index, term in enumerate(CAREER_TERMS) if term in haystack), None)
        if rank is None:
            continue
        clean = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))
        if clean.rstrip("/") == base_url.rstrip("/"):
            continue
        ranked[clean] = min(rank, ranked.get(clean, rank))
    return [url for url, _ in sorted(ranked.items(), key=lambda item: (item[1], item[0]))[:limit]]


def _walk_job_postings(value: Any, found: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        kind = value.get("@type")
        kinds = set(kind if isinstance(kind, list) else [kind])
        if "JobPosting" in kinds:
            found.append(value)
        for child in value.values():
            _walk_job_postings(child, found)
    elif isinstance(value, list):
        for child in value:
            _walk_job_postings(child, found)


def extract_structured_job_postings(html: str, *, base_url: str) -> list[dict[str, Any]]:
    metadata = extruct.extract(html, base_url=base_url, syntaxes=["json-ld"])
    raw: list[dict[str, Any]] = []
    _walk_job_postings(metadata.get("json-ld", []), raw)
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in raw:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        hiring = item.get("hiringOrganization") or {}
        hiring_name = str(hiring.get("name") or "").strip() if isinstance(hiring, dict) else ""
        date_posted = str(item.get("datePosted") or "").strip()
        valid_through = str(item.get("validThrough") or "").strip()
        key = (title.casefold(), hiring_name.casefold(), date_posted)
        if key in seen:
            continue
        seen.add(key)
        location = item.get("jobLocation")
        output.append(
            {
                "title": title[:500],
                "hiring_organization": hiring_name[:500],
                "date_posted": date_posted[:80] or None,
                "valid_through": valid_through[:80] or None,
                "employment_type": item.get("employmentType"),
                "job_location": location,
                "description": BeautifulSoup(str(item.get("description") or ""), "lxml").get_text(" ", strip=True)[:1000],
            }
        )
    return output[:50]


def _normalised_tokens(value: Any) -> set[str]:
    text = str(value or "").translate(
        str.maketrans({"ø": "o", "Ø": "O", "å": "a", "Å": "A", "æ": "ae", "Æ": "AE"})
    ).casefold()
    return set(re.findall(r"[a-z0-9]+", text))


def posting_matches_company(profile: dict[str, Any], posting: dict[str, Any]) -> bool:
    hiring_name = str(posting.get("hiring_organization") or "").strip()
    if not hiring_name:
        return False
    legal = set(distinctive_legal_name_tokens(profile.get("name")))
    hiring = _normalised_tokens(hiring_name)
    return bool(legal and legal.issubset(hiring))


def build_job_observation(
    profile: dict[str, Any],
    *,
    source_url: str,
    retrieved_at: str,
    content_sha256: str,
    posting: dict[str, Any],
    index: int,
) -> dict[str, Any] | None:
    website = (profile.get("evidence") or {}).get("website") or {}
    identity = (website.get("value") or {}).get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return None
    if len(str(content_sha256 or "")) != 64 or not posting_matches_company(profile, posting):
        return None
    org = str(profile.get("organisation_number") or "")
    digest = hashlib.sha256(
        f"{org}|{source_url}|{posting.get('title')}|{posting.get('date_posted')}|{index}".encode("utf-8")
    ).hexdigest()[:20]
    evidence_span = " | ".join(
        part
        for part in (
            str(posting.get("title") or "").strip(),
            str(posting.get("hiring_organization") or "").strip(),
            str(posting.get("date_posted") or "").strip(),
            str(posting.get("valid_through") or "").strip(),
        )
        if part
    )[:1000]
    return {
        "id": f"company-site-job-{org}-{digest}",
        "organisation_number": org,
        "platform": "company_site",
        "signal_type": "job_posting",
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "content_sha256": content_sha256,
        "exact_entity": True,
        "identity_proof": [
            {"type": "website_identity_gate", "status": identity.get("status"), "score": identity.get("score")},
            {"type": "structured_hiring_organization_match", "value": posting.get("hiring_organization")},
        ],
        "acquisition_mode": "permitted_public_page",
        "rights_status": "approved",
        "source_class": "company_site",
        "evidence_span": evidence_span,
        "metrics": {
            "job_title": posting.get("title"),
            "date_posted": posting.get("date_posted"),
            "valid_through": posting.get("valid_through"),
            "employment_type": posting.get("employment_type"),
            "job_location": posting.get("job_location"),
        },
        "strategy": "exact_company_site_structured_job_v1",
    }
