from __future__ import annotations

import hashlib
import re
from typing import Any


OWN_SIGNAL_TYPE = "official_registry_contact"
MANAGED_FIELD = "external.contact_email"
EMAIL_RE = re.compile(r"(?i)^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?\.[a-z]{2,63}$")


def _clean_email(value: Any) -> str:
    email = str(value or "").strip().strip("<>[](){}\"'").casefold()
    if not email or len(email) > 320 or email.count("@") != 1:
        return ""
    if any(ch.isspace() for ch in email):
        return ""
    if not EMAIL_RE.fullmatch(email):
        return ""
    return email


def registered_contact_email(profile: dict[str, Any]) -> str:
    """Return the literal public BRREG registered contact email when provenance is exact.

    The value is not interpreted as a company-owned website mailbox and is not used to
    establish website identity.  It is only an official registry contact point for the
    exact organisation-number row.
    """
    org = str(profile.get("organisation_number") or "")
    registry = ((profile.get("evidence") or {}).get("registry") or {})
    if registry.get("status") != "available":
        return ""
    if str(registry.get("source_row_key") or "") != org:
        return ""
    if not str(registry.get("source_url") or "").startswith("https://data.brreg.no/"):
        return ""
    if not str(registry.get("content_sha256") or "").strip():
        return ""
    values = registry.get("value") if isinstance(registry.get("value"), dict) else {}
    return _clean_email((values or {}).get("epostadresse"))


def _evidence_id(org: str, email: str, registry: dict[str, Any]) -> str:
    material = "|".join(
        (
            org,
            "v6i-registry-contact",
            email,
            str(registry.get("source_url") or ""),
            str(registry.get("content_sha256") or ""),
            str(registry.get("source_row_key") or ""),
        )
    )
    return "ev-v6i-registry-contact-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _is_own_claim(claim: dict[str, Any]) -> bool:
    return claim.get("field") == MANAGED_FIELD and claim.get("signal_type") == OWN_SIGNAL_TYPE


def _stronger_contact_exists(claims: list[dict[str, Any]]) -> bool:
    """Preserve an already-published first-party/site contact ahead of registry fallback."""
    return any(
        claim.get("field") == MANAGED_FIELD
        and claim.get("availability") == "available"
        and str(claim.get("value") or "").strip()
        and claim.get("signal_type") != OWN_SIGNAL_TYPE
        for claim in claims
    )


def project_registry_contact_email(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Publish BRREG's exact-org registered email only as a fallback contact point.

    Semantics are deliberately narrower than the existing H2c first-party contact claim:
    the email is the public contact address registered for the exact organisation in
    Brønnøysundregistrene. It does **not** prove website ownership, mailbox control,
    deliverability, or that the email domain is owned by the company.

    The projection is deterministic, zero-network, idempotent, and never replaces an
    already-published stronger first-party contact email.
    """
    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    if not org or str(profile.get("organisation_number") or "") != org:
        raise ValueError("Registry contact projection organisation number mismatch")

    original_claims = [dict(item) for item in (contract.get("claims") or [])]
    original_evidence = [dict(item) for item in (contract.get("evidence") or [])]

    removed_ids = {
        evidence_id
        for claim in original_claims
        if _is_own_claim(claim)
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    claims = [claim for claim in original_claims if not _is_own_claim(claim)]
    still_referenced = {
        evidence_id
        for claim in claims
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    evidence_by_id = {
        str(item.get("id")): item
        for item in original_evidence
        if item.get("id") and item.get("id") not in (removed_ids - still_referenced)
    }

    if _stronger_contact_exists(claims):
        return {
            **contract,
            "claims": claims,
            "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
        }

    email = registered_contact_email(profile)
    if not email:
        return {
            **contract,
            "claims": claims,
            "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
        }

    registry = ((profile.get("evidence") or {}).get("registry") or {})
    evidence_id = _evidence_id(org, email, registry)
    evidence_by_id[evidence_id] = {
        "id": evidence_id,
        "source_url": registry.get("source_url"),
        "source_class": "official",
        "retrieved_at": registry.get("retrieved_at"),
        "content_sha256": registry.get("content_sha256"),
        "claim_span": f"epostadresse={email}",
        "source_row_key": registry.get("source_row_key"),
    }
    claims.append(
        {
            "field": MANAGED_FIELD,
            "value": email,
            "availability": "available",
            "confidence": 1.0,
            "evidence_ids": [evidence_id],
            "platform": "brreg_registry",
            "signal_type": OWN_SIGNAL_TYPE,
            "claim_scope": (
                "Public contact email registered on the exact organisation-number BRREG row. "
                "This does not assert website-domain ownership, mailbox control, or deliverability."
            ),
        }
    )
    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
