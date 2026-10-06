from __future__ import annotations

import hashlib
import re
from typing import Any

from .job_surface_signal import same_company_host


MANAGED_FIELD = "external.hiring_intent"

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

    Generic careers/navigation wording is insufficient. Broad phrases such as "vi søker"
    or "looking for" require nearby people/role context, and explicit negative statements
    veto the candidate.
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
            return {"match_type": kind, "evidence_span": span[:500]}
    return None


def _confidence(website: dict[str, Any]) -> float:
    try:
        score = float((((website.get("value") or {}).get("identity_assessment") or {}).get("score")))
    except (TypeError, ValueError):
        score = 0.95
    return max(0.0, min(1.0, score))


def _qualified_website(profile: dict[str, Any]) -> dict[str, Any] | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") if isinstance(website.get("value"), dict) else {}
    assessment = value.get("identity_assessment") if isinstance(value.get("identity_assessment"), dict) else {}
    if website.get("status") != "available" or not assessment.get("publishable"):
        return None
    if not str(website.get("retrieved_at") or "").strip():
        return None
    return website


def _page(
    *,
    url: Any,
    text: Any,
    digest: Any,
    retrieved_at: Any,
    provenance: str,
) -> dict[str, str] | None:
    source_url = str(url or "").strip()
    page_text = str(text or "").strip()
    content_sha256 = str(digest or "").strip()
    retrieved = str(retrieved_at or "").strip()
    if (
        not source_url.startswith(("http://", "https://"))
        or not page_text
        or len(content_sha256) != 64
        or not retrieved
    ):
        return None
    return {
        "source_url": source_url,
        "text": page_text,
        "content_sha256": content_sha256,
        "retrieved_at": retrieved,
        "provenance": provenance,
    }


def _retained_exact_site_pages(
    profile: dict[str, Any],
    website: dict[str, Any],
) -> list[dict[str, str]]:
    """Return retained first-party pages only when each fact has page-local evidence."""
    value = website.get("value") or {}
    final_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    retrieved_at = website.get("retrieved_at")
    rows: list[dict[str, str]] = []

    homepage = _page(
        url=final_url,
        text=value.get("main_text_excerpt"),
        digest=website.get("content_sha256") or value.get("content_sha256"),
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
        item = _page(
            url=page_url,
            text=page.get("main_text_excerpt"),
            digest=page.get("content_sha256"),
            retrieved_at=page.get("retrieved_at") or retrieved_at,
            provenance="retained_same_site_page",
        )
        if item:
            rows.append(item)

    surface = ((profile.get("evidence") or {}).get("website_careers_surface") or {})
    if surface.get("status") == "available":
        surface_value = surface.get("value") if isinstance(surface.get("value"), dict) else {}
        surface_url = str(surface_value.get("final_url") or surface.get("source_url") or "").strip()
        nominated = {
            str(item.get("url") or "").rstrip("/")
            for item in value.get("careers_links") or []
            if isinstance(item, dict) and item.get("url")
        }
        if (
            surface_url
            and same_company_host(surface_url, final_url)
            and surface_url.rstrip("/") in nominated
        ):
            item = _page(
                url=surface_url,
                text=surface_value.get("main_text_excerpt"),
                digest=surface.get("content_sha256") or surface_value.get("content_sha256"),
                retrieved_at=surface.get("retrieved_at") or retrieved_at,
                provenance="homepage_nominated_careers_surface",
            )
            if item:
                rows.append(item)

    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for item in rows:
        key = (item["source_url"], item["content_sha256"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _qualified_hiring_intent(profile: dict[str, Any]) -> dict[str, Any] | None:
    website = _qualified_website(profile)
    if website is None:
        return None
    value = website.get("value") or {}
    final_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    for page in _retained_exact_site_pages(profile, website):
        if not same_company_host(page["source_url"], final_url):
            continue
        match = hiring_intent_match(page["text"])
        if match is None:
            continue
        return {
            **page,
            "match_type": match["match_type"],
            "evidence_span": match["evidence_span"],
            "identity_proof": dict(value.get("identity_assessment") or {}),
        }
    return None


def _evidence_id(org: str, source_url: str, content_sha256: str, match_type: str) -> str:
    material = f"{org}|{source_url}|{content_sha256}|{match_type}"
    return "ev-hiring-intent-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def project_company_authored_hiring_intent(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Project the middle hiring level from retained exact first-party evidence only.

    careers surface != company-authored hiring intent != specific active job.

    This manages only external.hiring_intent, performs zero network access, never creates
    external.job_posting, and never treats generic careers/navigation text as intent.
    """
    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]

    removed_ids = {
        str(evidence_id)
        for claim in claims
        if claim.get("field") == MANAGED_FIELD
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    claims = [claim for claim in claims if claim.get("field") != MANAGED_FIELD]
    still_referenced = {
        str(evidence_id)
        for claim in claims
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    evidence = [
        item
        for item in evidence
        if str(item.get("id") or "") not in (removed_ids - still_referenced)
    ]

    intent = _qualified_hiring_intent(profile)
    if intent is None:
        return {
            **contract,
            "claims": claims,
            "evidence": sorted(evidence, key=lambda item: str(item.get("id") or "")),
        }

    evidence_id = _evidence_id(
        org,
        str(intent["source_url"]),
        str(intent["content_sha256"]),
        str(intent["match_type"]),
    )
    evidence_by_id = {
        str(item.get("id")): item
        for item in evidence
        if str(item.get("id") or "")
    }
    evidence_by_id[evidence_id] = {
        "id": evidence_id,
        "source_url": intent["source_url"],
        "source_class": "company_owned",
        "retrieved_at": intent["retrieved_at"],
        "content_sha256": intent["content_sha256"],
        "claim_span": intent["evidence_span"],
        "identity_proof": intent["identity_proof"],
        "extraction_method": f"explicit_company_authored_recruitment_language:{intent['match_type']}",
        "page_provenance": intent["provenance"],
    }
    claims.append(
        {
            "field": MANAGED_FIELD,
            "value": {
                "match_type": intent["match_type"],
                "source_url": intent["source_url"],
            },
            "availability": "available",
            "confidence": _confidence(((profile.get("evidence") or {}).get("website") or {})),
            "evidence_ids": [evidence_id],
            "platform": "company_site",
            "signal_type": "hiring_intent",
            "claim_scope": (
                "Exact company-authored first-party text expresses recruitment intent. "
                "This is not proof that a specific vacancy is currently open. Specific active "
                "jobs require a separate external.job_posting claim."
            ),
        }
    )
    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
