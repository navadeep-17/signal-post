from __future__ import annotations

import hashlib
from typing import Any


MANAGED_FIELDS = ("industry", "municipality_number", "bankrupt", "liquidating")


def _evidence_id(org: str, field: str, record: dict[str, Any]) -> str:
    material = "|".join(
        (
            org,
            "v2-registry",
            field,
            str(record.get("source_url") or ""),
            str(record.get("content_sha256") or ""),
            str(record.get("source_row_key") or ""),
        )
    )
    return "ev-v2-registry-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _registry_value(profile: dict[str, Any], field: str) -> Any:
    if field == "industry":
        code = profile.get("industry_code")
        description = profile.get("industry_label")
        if code in (None, "") and description in (None, ""):
            # Some older/internal profile shapes already carry a normalized industry value.
            return profile.get("industry")
        return {"code": code or None, "description": description or None}
    if field == "municipality_number":
        return profile.get("municipality_number")
    if field == "bankrupt":
        return profile.get("bankrupt")
    if field == "liquidating":
        return profile.get("liquidating")
    raise KeyError(field)


def project_v2_registry_claims(contract: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Attach evaluator-facing BRREG registry claims without changing the V1 adapter.

    The base collector/output adapter remains the immutable V1 behavior. V2 reads the
    exact-org registry profile already retained by that collector and adds only fields that
    were present there but not reliably surfaced in the V1 claims envelope. No network
    access, identity relaxation, or value inference occurs here.
    """

    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    if str(profile.get("organisation_number") or "") != org:
        raise ValueError("V2 registry projection organisation number mismatch")

    registry = ((profile.get("evidence") or {}).get("registry") or {})
    if registry.get("status") != "available":
        return contract
    source_url = registry.get("source_url")
    retrieved_at = registry.get("retrieved_at")
    if not source_url or not retrieved_at:
        return contract

    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]

    # V2 owns these four field names. Remove an older/broader representation first so the
    # output is deterministic and idempotent.
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
        value = _registry_value(profile, field)
        # False is a meaningful official value; only None/empty strings are absent.
        if value is None or value == "":
            continue
        evidence_id = _evidence_id(org, field, registry)
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": source_url,
            "source_class": "official",
            "retrieved_at": retrieved_at,
            "content_sha256": registry.get("content_sha256"),
            "claim_span": f"{field}={value}"[:1000],
            **({"source_row_key": registry.get("source_row_key")} if registry.get("source_row_key") is not None else {}),
        }
        claims.append(
            {
                "field": field,
                "value": value,
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": [evidence_id],
                "signal_type": "official_registry_projection",
                "claim_scope": "Exact organisation-number BRREG registry profile retained by the base collector; V2 zero-network projection.",
            }
        )

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
