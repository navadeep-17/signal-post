from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .domain_discovery import (
    _page_contains_org_number,
    _page_matches_registry_location,
    distinctive_legal_name_tokens,
)

FOREIGN_LEGAL_SUFFIXES = {
    "ab", "ag", "aps", "bv", "corp", "corporation", "gmbh", "inc", "limited",
    "llc", "ltd", "nv", "oy", "oyj", "plc",
}

HOLDING_PHRASES = (
    "forvalte aksjer",
    "eie og forvalte aksjer",
    "aksjer og andeler i andre selskaper",
    "andeler i andre selskaper",
    "holdingselskap",
    "investeringsselskap",
)

_TRANSLATION = str.maketrans({"ø": "o", "Ø": "O", "å": "a", "Å": "A", "æ": "ae", "Æ": "AE"})


def _normalise(value: Any) -> str:
    text = str(value or "").translate(_TRANSLATION).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _flatten_identity_text(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"name", "legalName", "alternateName"} and isinstance(child, str):
                found.append(child)
            else:
                found.extend(_flatten_identity_text(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_flatten_identity_text(child))
    return found


def _website_corpus(website: dict[str, Any]) -> str:
    value = website.get("value") or {}
    parts: list[Any] = [
        value.get("title"),
        value.get("description"),
        value.get("main_text_excerpt"),
        *_flatten_identity_text(value.get("structured_organisations") or []),
    ]
    for page in value.get("pages") or []:
        if isinstance(page, dict):
            parts.extend([page.get("title"), page.get("main_text_excerpt")])
    return _normalise(" ".join(str(part) for part in parts if str(part or "").strip()))


def _conflicting_legal_entity(profile: dict[str, Any], website: dict[str, Any]) -> str | None:
    core = distinctive_legal_name_tokens(profile.get("name"))
    if not core:
        return None
    corpus = _website_corpus(website)
    if not corpus:
        return None
    core_pattern = r"\b" + r"\s+".join(re.escape(token) for token in core)
    suffix_pattern = "|".join(sorted(FOREIGN_LEGAL_SUFFIXES, key=len, reverse=True))
    pattern = re.compile(core_pattern + rf"(?:\s+[a-z0-9]+){{0,3}}\s+({suffix_pattern})\b")
    match = pattern.search(corpus)
    return match.group(1) if match else None


def _registry_holding_risk(profile: dict[str, Any]) -> bool:
    raw = (profile.get("evidence") or {}).get("registry", {}).get("value") or {}
    if str(raw.get("naeringskode1.kode") or "").strip() == "00.000":
        return True
    purpose = _normalise(
        f"{raw.get('aktivitet') or ''} {raw.get('vedtektsfestetFormaal') or ''}"
    )
    return any(_normalise(phrase) in purpose for phrase in HOLDING_PHRASES)


def registry_risk_reasons(profile: dict[str, Any], website: dict[str, Any]) -> list[str]:
    """Return reasons a nominal H1c match must remain quarantined.

    Exact organisation-number proof wins. Otherwise we reject a page that explicitly names
    a same-core foreign legal entity, and we require location corroboration for registry
    entities whose official activity is unspecified/holding-oriented. These checks are
    intentionally conservative because a wrong-company publication is a hard competition risk.
    """
    if website.get("status") != "available":
        return []
    if _page_contains_org_number(profile, website):
        return []

    reasons: list[str] = []
    conflicting_suffix = _conflicting_legal_entity(profile, website)
    if conflicting_suffix:
        reasons.append(
            f"page identifies a same-core foreign legal entity with suffix {conflicting_suffix.upper()}"
        )

    if _registry_holding_risk(profile) and not _page_matches_registry_location(profile, website):
        reasons.append(
            "registry activity is unspecified/holding-oriented and the page lacks registry-location corroboration"
        )
    return reasons


def apply_registry_risk_guard(profile: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Downgrade an H1c promotion when registry/page evidence indicates identity collision risk."""
    row = deepcopy(profile)
    evidence_map = row.get("evidence") or {}
    discovery = evidence_map.get("website_discovery_zero_cost") or {}
    website = evidence_map.get("website") or {}
    assessment = (website.get("value") or {}).get("identity_assessment") or {}

    if discovery.get("status") != "available" or not assessment.get("publishable"):
        return row, []

    reasons = registry_risk_reasons(row, website)
    if not reasons:
        value = discovery.get("value") or {}
        value["registry_risk_guard"] = {"status": "passed", "reasons": []}
        discovery["value"] = value
        evidence_map["website_discovery_zero_cost"] = discovery
        row["evidence"] = evidence_map
        return row, []

    website_value = website.get("value") or {}
    website_value["identity_assessment"] = {
        **assessment,
        "status": "review",
        "score": min(float(assessment.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [*list(assessment.get("reasons") or []), *reasons],
        "method": "h1c_registry_risk_guard_v1",
    }
    website["value"] = website_value
    evidence_map["website"] = website

    discovery_value = discovery.get("value") or {}
    discovery_value["registry_risk_guard"] = {"status": "quarantined", "reasons": reasons}
    discovery["value"] = discovery_value
    evidence_map["website_discovery_zero_cost"] = discovery
    row["evidence"] = evidence_map
    return row, reasons
