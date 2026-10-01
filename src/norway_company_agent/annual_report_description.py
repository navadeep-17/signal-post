from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from .external_footprint import validate_observation


# Annual reports use several recurring headings for the legal entity's activity.
# Keep this extractor deliberately narrow: it only accepts explicit company-scope
# activity sections and refuses group-only or accounting-policy language.
HEADING_PATTERNS = (
    re.compile(r"(?im)^\s*(?:virksomhetens|verksemdas|selskapets|selskapets?)\s+(?:art|virksomhet|verksemd)\s*[:.-]?\s*$"),
    re.compile(r"(?im)^\s*(?:om\s+)?(?:selskapet|verksemda)\s*[:.-]?\s*$"),
)

STOP_HEADING = re.compile(
    r"(?im)^\s*(?:fortsatt\s+drift|going\s+concern|arsresultat|årsresultat|resultat|"
    r"balanse|egenkapital|styret|hendelser|risiko|arbeidsmiljo|arbeidsmiljø|likestilling|"
    r"miljo|miljø|redegjorelse|redegjørelse|noter?|note\s+\d+|salgsinntekter|"
    r"inntektsforing|inntektsføring|klassifisering\s+og\s+vurdering|anleggsmidler|"
    r"omlopsmidler|omløpsmidler|skatt|leieavtaler|fordringer|varelager|avskrivninger)\b.*$"
)

# OCR sometimes loses line breaks between the activity paragraph and the first
# accounting-policy heading. Cut at those headings even when they appear inline.
INLINE_ACCOUNTING_SECTION = re.compile(
    r"(?i)(?<!^)\s+(?:salgsinntekter|inntektsforing|inntektsføring|"
    r"klassifisering\s+og\s+vurdering(?:\s+av\s+balanseposter)?|anleggsmidler|"
    r"omlopsmidler|omløpsmidler|leieavtaler|fordringer|varelager|avskrivninger|"
    r"skatt(?:ekostnad(?:en)?)?)\b"
)

GROUP_ONLY = re.compile(r"(?i)\b(?:konsernet|konsernets|the\s+group|group\s+activities)\b")
COMPANY_SCOPE = re.compile(r"(?i)\b(?:selskapet|virksomheten|verksemda|foretaket|company)\b")
BOILERPLATE = re.compile(
    r"(?i)\b(?:arsregnskapet\s+er\s+avlagt|årsregnskapet\s+er\s+avlagt|"
    r"regnskapet\s+er\s+utarbeidet|accounting\s+principles)\b"
)
ACCOUNTING_POLICY_ONLY = re.compile(
    r"(?i)\b(?:har\s+(?:ikke\s+)?endret\s+regnskapsprinsipp|regnskapsprinsipp(?:er|ene)?|"
    r"accounting\s+polic(?:y|ies)|prinsippendring)\b"
)
LEGAL_ENTITY_AT_START = re.compile(
    r"^\s*([A-ZÆØÅ0-9][A-Za-zÆØÅæøå0-9&.'’()\-/ ]{1,80}?\s+"
    r"(?:ASA|AS|ANS|DA|NUF|SA|BA|KS|IKS|HF|KF|SF))\b"
)
LEGAL_SUFFIX = re.compile(r"(?i)\s+(?:ASA|AS|ANS|DA|NUF|SA|BA|KS|IKS|HF|KF|SF)\s*$")


def _compact(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_description(text: str) -> str:
    text = _compact(text)
    lines = [line.strip(" -•\t") for line in text.splitlines() if line.strip()]
    cleaned = " ".join(lines)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    inline_stop = INLINE_ACCOUNTING_SECTION.search(cleaned)
    if inline_stop and inline_stop.start() >= 40:
        cleaned = cleaned[: inline_stop.start()].rstrip(" .;:-") + "."
    return cleaned[:700]


def _normalize_company_name(value: str) -> str:
    text = LEGAL_SUFFIX.sub("", str(value or "").strip())
    text = text.casefold()
    text = re.sub(r"[^0-9a-zæøå]+", " ", text)
    return " ".join(text.split())


def _leading_named_entity_mismatch(description: str, target_name: str) -> str | None:
    """Return the explicit leading legal entity when it contradicts the target.

    Annual-account copies occasionally contain a narrative paragraph naming another
    legal entity even though the target org number appears elsewhere in the document.
    A leading `Other Company AS ...` statement is therefore accepted only when it
    normalizes to the target legal name. Generic `Selskapet ...` text is unaffected.
    """

    match = LEGAL_ENTITY_AT_START.match(description)
    if not match:
        return None
    named = match.group(1).strip()
    expected = _normalize_company_name(target_name)
    observed = _normalize_company_name(named)
    if not expected or not observed:
        return named
    if expected == observed or expected in observed or observed in expected:
        return None
    return named


def extract_business_description(text: str) -> tuple[str | None, str]:
    """Extract a conservative legal-entity business description from annual-report text.

    Returns ``(description, status)``. The extractor intentionally abstains when it
    cannot distinguish a company-scope activity statement from group/boilerplate text.
    """

    body = _compact(text)
    if not body:
        return None, "empty_text"

    candidates: list[str] = []
    for pattern in HEADING_PATTERNS:
        for match in pattern.finditer(body):
            start = match.end()
            tail = body[start : start + 2200]
            stop = STOP_HEADING.search(tail)
            if stop:
                tail = tail[: stop.start()]
            candidate = _clean_description(tail)
            if len(candidate) < 40:
                continue
            if ACCOUNTING_POLICY_ONLY.search(candidate):
                continue
            if BOILERPLATE.search(candidate):
                continue
            # Group-only sections are unsafe. A candidate may mention a group only when
            # the legal entity itself is also explicitly described.
            if GROUP_ONLY.search(candidate) and not COMPANY_SCOPE.search(candidate):
                continue
            candidates.append(candidate)

    if not candidates:
        return None, "no_company_activity_section"

    # Prefer the most concise sufficiently informative section. This reduces the chance
    # of swallowing subsequent unrelated report sections when OCR heading detection is weak.
    candidates.sort(key=lambda value: (len(value) > 450, len(value)))
    chosen = candidates[0]
    if len(chosen) < 40:
        return None, "description_too_short"
    return chosen, "accepted"


def build_annual_report_description_observation(
    profile: dict[str, Any],
    *,
    text: str,
    source_url: str,
    content_sha256: str,
    retrieved_at: str | None = None,
    effective_at: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Create an exact-entity BRREG company-description observation from report text.

    The target organisation number must occur in the supplied report text. The source is
    official BRREG annual-account evidence; the extracted description is never inferred
    from a company name or from a group-only passage.
    """

    org = str(profile.get("organisation_number") or "")
    digits = re.sub(r"\D", "", text)
    if len(org) != 9 or not org.isdigit():
        return None, {"status": "invalid_organisation_number"}
    if org not in digits:
        return None, {"status": "organisation_number_not_in_report_text"}
    if len(str(content_sha256 or "")) != 64:
        return None, {"status": "invalid_content_hash"}

    description, status = extract_business_description(text)
    if not description:
        return None, {"status": status}

    mismatched_entity = _leading_named_entity_mismatch(description, str(profile.get("name") or ""))
    if mismatched_entity:
        return None, {
            "status": "explicit_different_company_name",
            "named_entity": mismatched_entity,
            "target_name": profile.get("name"),
        }

    retrieved = retrieved_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    observation = {
        "id": "annual-description-" + hashlib.sha256(
            f"{org}|{effective_at or ''}|{description}|{content_sha256}".encode("utf-8")
        ).hexdigest()[:24],
        "organisation_number": org,
        "platform": "brreg",
        "signal_type": "company_profile",
        "source_url": source_url,
        "retrieved_at": retrieved,
        "content_sha256": content_sha256,
        "exact_entity": True,
        "identity_proof": [
            {"type": "official_brreg_annual_account_endpoint_organisation_number", "value": org},
            {"type": "organisation_number_in_report_text", "value": org},
        ],
        "acquisition_mode": "official_api",
        "rights_status": "approved",
        "source_class": "official_annual_account_copy",
        "evidence_span": description,
        "effective_at": effective_at,
        "company_description": description,
        "metrics": {
            "claim_scope": "Explicit legal-entity business/activity description extracted from the official BRREG annual-account copy.",
            "description_characters": len(description),
        },
        "strategy": "annual_report_company_description_exact_org_v2",
    }
    errors = validate_observation(observation)
    if errors:
        return None, {"status": "validation_error", "validation_errors": errors}
    return observation, {"status": "accepted", "description": description}
