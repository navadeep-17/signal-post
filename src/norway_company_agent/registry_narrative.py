from __future__ import annotations

import hashlib
import re
from typing import Any


OWN_SIGNAL_TYPE = "official_registry_narrative_projection"
REGISTRY_ACTIVITY_KEY = "aktivitet"
REGISTRY_PURPOSE_KEY = "vedtektsfestetFormaal"


def _clean_text(value: Any, *, max_chars: int = 4000) -> str:
    """Normalize transport whitespace without rewriting source meaning."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    return text[:max_chars]


def _evidence_id(org: str, field: str, record: dict[str, Any], value: str) -> str:
    material = "|".join(
        (
            org,
            "v4-registry-narrative",
            field,
            str(record.get("source_url") or ""),
            str(record.get("content_sha256") or ""),
            str(record.get("source_row_key") or ""),
            value,
        )
    )
    return "ev-v4-registry-narrative-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _registry_values(profile: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    registry = ((profile.get("evidence") or {}).get("registry") or {})
    values = registry.get("value") if isinstance(registry.get("value"), dict) else {}
    activity = _clean_text((values or {}).get(REGISTRY_ACTIVITY_KEY))
    purpose = _clean_text((values or {}).get(REGISTRY_PURPOSE_KEY))
    return registry, activity, purpose


def _own_claim(claim: dict[str, Any]) -> bool:
    return claim.get("signal_type") == OWN_SIGNAL_TYPE and claim.get("field") in {
        "company_description",
        "registered_purpose",
    }


def _append_claim(
    *,
    claims: list[dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
    org: str,
    field: str,
    value: str,
    source_key: str,
    registry: dict[str, Any],
) -> None:
    evidence_id = _evidence_id(org, field, registry, value)
    evidence_by_id[evidence_id] = {
        "id": evidence_id,
        "source_url": registry.get("source_url"),
        "source_class": "official",
        "retrieved_at": registry.get("retrieved_at"),
        "content_sha256": registry.get("content_sha256"),
        "claim_span": f"{source_key}={value}"[:4000],
        **(
            {"source_row_key": registry.get("source_row_key")}
            if registry.get("source_row_key") is not None
            else {}
        ),
    }
    claims.append(
        {
            "field": field,
            "value": value,
            "availability": "available",
            "confidence": 1.0,
            "evidence_ids": [evidence_id],
            "signal_type": OWN_SIGNAL_TYPE,
            "claim_scope": (
                "Literal exact-organisation-number BRREG registry text retained by the "
                "base collector; zero-network projection with no semantic inference."
            ),
        }
    )


def project_registry_narrative_claims(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Expose exact-org BRREG activity/purpose text already retained by the collector.

    ``aktivitet`` is used only as a fallback ``company_description`` when no stronger
    published description already exists. That preserves first-party website / filed
    annual-report descriptions while giving synthesis an official exact-entity description
    for companies where those richer sources are absent.

    ``vedtektsfestetFormaal`` is emitted as the explicitly labelled
    ``registered_purpose`` claim. It is never substituted for actual activity.

    The projector is zero-network, deterministic and idempotent. It removes only claims it
    created on a previous pass and never rewrites another source's claim.
    """

    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    if not org or str(profile.get("organisation_number") or "") != org:
        raise ValueError("Registry narrative projection organisation number mismatch")

    registry, activity, purpose = _registry_values(profile)
    if registry.get("status") != "available":
        return contract
    if not str(registry.get("source_url") or "").strip() or not str(registry.get("retrieved_at") or "").strip():
        return contract

    original_claims = [dict(item) for item in (contract.get("claims") or [])]
    original_evidence = [dict(item) for item in (contract.get("evidence") or [])]

    removed_ids = {
        evidence_id
        for claim in original_claims
        if _own_claim(claim)
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    claims = [claim for claim in original_claims if not _own_claim(claim)]
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

    stronger_description_exists = any(
        claim.get("field") == "company_description"
        and claim.get("availability") == "available"
        and str(claim.get("value") or "").strip()
        for claim in claims
    )

    if activity and not stronger_description_exists:
        _append_claim(
            claims=claims,
            evidence_by_id=evidence_by_id,
            org=org,
            field="company_description",
            value=activity,
            source_key=REGISTRY_ACTIVITY_KEY,
            registry=registry,
        )

    if purpose:
        _append_claim(
            claims=claims,
            evidence_by_id=evidence_by_id,
            org=org,
            field="registered_purpose",
            value=purpose,
            source_key=REGISTRY_PURPOSE_KEY,
            registry=registry,
        )

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
