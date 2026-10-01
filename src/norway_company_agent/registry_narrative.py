from __future__ import annotations

import hashlib
import re
from typing import Any


MANAGED_FIELDS = ("registered_activity", "registered_purpose")
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


def project_registry_narrative_claims(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Expose exact-org BRREG activity/purpose text already retained by the collector.

    This projector is deliberately zero-network and does not infer a description from an
    industry code. It publishes only the literal ``aktivitet`` and
    ``vedtektsfestetFormaal`` values from the exact organisation-number registry row.

    The facts are labelled as registered activity/purpose rather than website content, so
    they cannot make an unverified company website appear available. Existing claims from
    every other source remain untouched.
    """

    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    if not org or str(profile.get("organisation_number") or "") != org:
        raise ValueError("Registry narrative projection organisation number mismatch")

    registry, activity, purpose = _registry_values(profile)
    if registry.get("status") != "available":
        return contract
    source_url = str(registry.get("source_url") or "").strip()
    retrieved_at = str(registry.get("retrieved_at") or "").strip()
    if not source_url or not retrieved_at:
        return contract

    values = {
        "registered_activity": activity,
        "registered_purpose": purpose,
    }

    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]

    # Own only our two explicit field names so rerunning the projection is idempotent.
    removed_ids = {
        evidence_id
        for claim in claims
        if claim.get("field") in MANAGED_FIELDS
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    claims = [claim for claim in claims if claim.get("field") not in MANAGED_FIELDS]
    still_referenced = {
        evidence_id
        for claim in claims
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    evidence_by_id = {
        str(item.get("id")): item
        for item in evidence
        if item.get("id") and item.get("id") not in (removed_ids - still_referenced)
    }

    for field in MANAGED_FIELDS:
        value = values[field]
        if not value:
            continue
        evidence_id = _evidence_id(org, field, registry, value)
        source_key = REGISTRY_ACTIVITY_KEY if field == "registered_activity" else REGISTRY_PURPOSE_KEY
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": source_url,
            "source_class": "official",
            "retrieved_at": retrieved_at,
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
                "signal_type": "official_registry_narrative_projection",
                "claim_scope": (
                    "Literal exact-organisation-number BRREG registry text retained by the "
                    "base collector; zero-network projection with no semantic inference."
                ),
            }
        )

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
