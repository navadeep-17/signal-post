from __future__ import annotations

import hashlib
import re
import unicodedata
import urllib.parse
from copy import deepcopy
from typing import Any

from .discovery import choose_search_candidate
from .domain_discovery import distinctive_legal_name_tokens
from .final_site_discovery import fetch_bounded_homepage
from .identity import apply_website_identity_gate
from .zero_cost_registry_guard import registry_risk_reasons


# Search is discovery only. These hosts can repeat exact registry facts while not being
# the company's own website, so they are never eligible for an independent site probe.
SEARCH_BLOCKED_HOSTS = frozenset(
    {
        "1881.no",
        "allabolag.no",
        "brreg.no",
        "companywall.no",
        "cylex.no",
        "dnb.com",
        "facebook.com",
        "finn.no",
        "firmadatabasen.no",
        "firmalisten.no",
        "forvalt.no",
        "gulesider.no",
        "hitta.no",
        "infobel.com",
        "instagram.com",
        "kompass.com",
        "kununu.com",
        "linkedin.com",
        "nav.no",
        "nor47business.com",
        "northdata.com",
        "opencorporates.com",
        "proff.no",
        "purehelp.no",
        "regnskap.no",
        "regnskapstall.no",
        "sokfirma.no",
        "tiktok.com",
        "trustpilot.com",
        "wikipedia.org",
        "x.com",
        "yelp.com",
        "youtube.com",
        "yra.no",
    }
)

LEGAL_FORM_TOKENS = frozenset(
    {
        "as",
        "asa",
        "ans",
        "da",
        "enk",
        "iks",
        "sa",
        "sam",
        "sti",
        "stiftelsen",
        "nuf",
        "ab",
        "limited",
        "ltd",
        "inc",
        "plc",
    }
)

# Labelled identifiers are used for conflict detection. A search-nominated page that
# identifies another legal entity is never published, even if it also mentions ours.
EXPLICIT_ORG_NUMBER_RE = re.compile(
    r"(?i)\b(?:organisasjonsnummer|org(?:anisasjons)?\.?\s*(?:nr|nummer)\.?)"
    r"\s*[:#-]?\s*((?:\d[\s.\-]?){8}\d)\b"
)


def _fold(value: Any) -> str:
    text = str(value or "").translate(
        str.maketrans({"ø": "o", "Ø": "O", "å": "a", "Å": "A", "æ": "ae", "Æ": "AE"})
    )
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _host(url: Any) -> str:
    try:
        return (urllib.parse.urlparse(str(url or "")).hostname or "").casefold().removeprefix("www.").strip(".")
    except ValueError:
        return ""


def _blocked_host(host: str) -> bool:
    return any(host == blocked or host.endswith("." + blocked) for blocked in SEARCH_BLOCKED_HOSTS)


def _page_parts(website: dict[str, Any]) -> list[str]:
    value = website.get("value") or {}
    parts: list[Any] = [
        value.get("title"),
        value.get("description"),
        value.get("identity_text_excerpt"),
        value.get("main_text_excerpt"),
    ]
    for item in value.get("structured_organisations") or []:
        if isinstance(item, dict):
            parts.extend(item.get(key) for key in ("name", "legalName", "alternateName"))
    for page in value.get("pages") or []:
        if isinstance(page, dict):
            parts.extend(
                [
                    page.get("title"),
                    page.get("identity_text_excerpt"),
                    page.get("main_text_excerpt"),
                ]
            )
    return [str(part) for part in parts if str(part or "").strip()]


def _identity_parts(website: dict[str, Any]) -> list[str]:
    """Page positions that plausibly identify the site owner, excluding ordinary body prose."""
    value = website.get("value") or {}
    parts: list[Any] = [value.get("title"), value.get("identity_text_excerpt")]
    for item in value.get("structured_organisations") or []:
        if isinstance(item, dict):
            parts.extend(item.get(key) for key in ("name", "legalName", "alternateName"))
    for page in value.get("pages") or []:
        if isinstance(page, dict):
            parts.extend([page.get("title"), page.get("identity_text_excerpt")])
    return [str(part) for part in parts if str(part or "").strip()]


def _target_org(profile: dict[str, Any]) -> str:
    return re.sub(r"\D", "", str(profile.get("organisation_number") or ""))


def _contains_target_org(profile: dict[str, Any], website: dict[str, Any]) -> bool:
    org = _target_org(profile)
    if len(org) != 9:
        return False
    pattern = re.compile(
        r"(?<!\d)" + r"[\s.\-]?".join(re.escape(digit) for digit in org) + r"(?!\d)"
    )
    return any(pattern.search(part) for part in _page_parts(website))


def _explicit_org_numbers(website: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for part in _page_parts(website):
        for match in EXPLICIT_ORG_NUMBER_RE.finditer(part):
            digits = re.sub(r"\D", "", match.group(1))
            if len(digits) == 9:
                found.add(digits)
    return found


def _has_conflicting_org(profile: dict[str, Any], website: dict[str, Any]) -> bool:
    target = _target_org(profile)
    return any(org != target for org in _explicit_org_numbers(website))


def _legal_name_phrases(profile: dict[str, Any]) -> list[str]:
    full_tokens = _fold(profile.get("name")).split()
    distinctive = [token for token in full_tokens if token not in LEGAL_FORM_TOKENS]
    phrases: list[str] = []
    if len(distinctive) >= 2:
        phrases.append(" ".join(distinctive))
    elif len(distinctive) == 1:
        # A single token is too collision-prone. Require the legal form with it.
        phrases.append(" ".join(full_tokens))
    full = " ".join(full_tokens)
    if full and full not in phrases:
        phrases.append(full)
    return phrases


def _legal_name_in_identity_position(profile: dict[str, Any], website: dict[str, Any]) -> bool:
    phrases = _legal_name_phrases(profile)
    if not phrases:
        return False
    identity = [_fold(part) for part in _identity_parts(website)]
    return any(re.search(r"\b" + re.escape(phrase) + r"\b", part) for phrase in phrases for part in identity)


def _strong_registry_location(profile: dict[str, Any], website: dict[str, Any]) -> bool:
    """Require a street+house-number or postcode+town pair from BRREG.

    A municipality/place alone, a bare four-digit postcode, or a street name without a
    house number is deliberately insufficient. This prevents the historical fjords.com-
    style false positive where a regional page happened to mention the same place.
    """
    raw = ((profile.get("evidence") or {}).get("registry") or {}).get("value") or {}
    corpus = " ".join(_fold(part) for part in _page_parts(website))
    if not corpus:
        return False

    postcode = re.sub(r"\D", "", str(raw.get("forretningsadresse.postnummer") or ""))
    town = _fold(raw.get("forretningsadresse.poststed"))
    if len(postcode) == 4 and town:
        pair = re.compile(r"\b" + re.escape(postcode) + r"\s+" + re.escape(town) + r"\b")
        reverse_pair = re.compile(r"\b" + re.escape(town) + r"\s+" + re.escape(postcode) + r"\b")
        if pair.search(corpus) or reverse_pair.search(corpus):
            return True

    street_raw = str(raw.get("forretningsadresse.adresse") or "").strip()
    street = _fold(street_raw)
    if street and re.search(r"\d", street_raw):
        # Require the filed street expression, including the house number, as one phrase.
        if re.search(r"\b" + re.escape(street) + r"\b", corpus):
            return True
    return False


def is_verified_website(profile: dict[str, Any]) -> bool:
    website = ((profile.get("evidence") or {}).get("website") or {})
    assessment = ((website.get("value") or {}).get("identity_assessment") or {})
    return website.get("status") == "available" and bool(assessment.get("publishable"))


def filter_search_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop hosts that can never be first-party websites before candidate scoring."""
    kept: list[dict[str, Any]] = []
    seen_hosts: set[str] = set()
    for result in results:
        host = _host(result.get("url"))
        if not host or _blocked_host(host) or host in seen_hosts:
            continue
        seen_hosts.add(host)
        kept.append(result)
    return kept


def choose_search_nomination(profile: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    """Choose at most one transient search result to fetch independently."""
    return choose_search_candidate(profile, filter_search_results(results))


def qualify_search_discovered_page(
    profile: dict[str, Any],
    website: dict[str, Any],
    base_assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Strict publication gate for a search-nominated domain.

    Search title/snippet/rank/hostname are not evidence here. The independent fetched page
    must prove the exact company by either:
      1. the target organisation number, with no explicitly labelled conflicting orgnr; or
      2. legal name in a site-owner identity position plus a strong BRREG address pair.
    """
    if website.get("status") != "available":
        return base_assessment

    assessment = dict(base_assessment or {})
    assessment.setdefault("reasons", [])
    assessment.setdefault("score", 0.0)
    assessment.setdefault("status", "review")
    assessment.setdefault("publishable", False)

    if _has_conflicting_org(profile, website):
        return {
            **assessment,
            "status": "review",
            "score": min(float(assessment.get("score") or 0.85), 0.85),
            "publishable": False,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "search-nominated page explicitly identifies another organisation number",
            ],
            "method": "search_discovered_exact_company_guard_v2",
        }

    if _contains_target_org(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "independently fetched page contains the exact target organisation number and no conflicting labelled organisation number",
            ],
            "method": "search_discovered_exact_company_guard_v2",
        }

    if _legal_name_in_identity_position(profile, website) and _strong_registry_location(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": max(float(assessment.get("score") or 0.0), 0.98),
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "independently fetched page identifies the legal company in an owner/identity position and matches a strong BRREG address pair",
            ],
            "method": "search_discovered_exact_company_guard_v2",
        }

    return {
        **assessment,
        "status": "review",
        "score": min(float(assessment.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [
            *list(assessment.get("reasons") or []),
            "search-nominated page lacks exact organisation-number proof or legal-name plus strong BRREG-address proof",
        ],
        "method": "search_discovered_exact_company_guard_v2",
    }


def evaluate_search_nomination(
    profile: dict[str, Any],
    candidate_url: str,
    *,
    timeout: float = 6.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch one nominated URL, verify it independently, and promote only exact identity."""
    row = deepcopy(profile)
    record, operations = fetch_bounded_homepage(
        candidate_url,
        source_type="search_nominated_company_website",
        timeout=timeout,
    )
    record["source_class"] = "company_owned_candidate"
    gated = apply_website_identity_gate(row, record)
    candidate = gated["website"]
    assessment = qualify_search_discovered_page(row, candidate, gated.get("assessment"))
    value = candidate.get("value") or {}
    if assessment is not None:
        value["identity_assessment"] = assessment
    candidate["value"] = value

    reasons = registry_risk_reasons(row, candidate) if assessment and assessment.get("publishable") else []
    if reasons and assessment is not None:
        assessment = {
            **assessment,
            "status": "review",
            "score": min(float(assessment.get("score") or 0.85), 0.85),
            "publishable": False,
            "reasons": [*list(assessment.get("reasons") or []), *reasons],
            "method": "search_discovered_registry_risk_guard_v1",
        }
        candidate["value"]["identity_assessment"] = assessment

    publishable = bool(
        candidate.get("status") == "available"
        and assessment
        and assessment.get("publishable")
    )
    evidence_map = row.setdefault("evidence", {})
    evidence_map["website_search_candidate"] = candidate
    if publishable:
        evidence_map["website"] = candidate
        row["website"] = str((candidate.get("value") or {}).get("final_url") or candidate.get("source_url") or "")

    return row, {
        "publishable": publishable,
        "selected_url": row.get("website") if publishable else None,
        "candidate_status": candidate.get("status"),
        "identity_status": (assessment or {}).get("status"),
        "identity_score": (assessment or {}).get("score"),
        "identity_method": (assessment or {}).get("method"),
        "registry_risk_reasons": reasons,
        "requests": int(operations.get("requests") or 0),
        "bytes": int(operations.get("bytes") or 0),
        "latencies_ms": [int(value) for value in operations.get("latencies_ms") or [] if value is not None],
    }


def query_hash(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()
