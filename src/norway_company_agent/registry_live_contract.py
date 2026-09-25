from __future__ import annotations

import hashlib
from typing import Any


MANAGED_FIELDS = (
    "legal_name",
    "legal_form",
    "employee_count",
    "municipality",
    "industry",
    "business_address",
    "postal_address",
    "bankrupt",
    "liquidating",
    "latest_submitted_accounts",
)


def _evidence_id(org: str, field: str, record: dict[str, Any]) -> str:
    material = "|".join(
        [
            org,
            "registry_live",
            field,
            str(record.get("source_url") or ""),
            str(record.get("content_sha256") or ""),
        ]
    )
    return "ev-registry-live-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _value(record: dict[str, Any], key: str) -> Any:
    value = record.get("value") or {}
    if not isinstance(value, dict):
        return None
    if key == "legal_name":
        return value.get("name")
    if key == "legal_form":
        return value.get("legal_form")
    if key == "employee_count":
        return value.get("employees")
    if key == "industry":
        raw = value.get("industry")
        if not isinstance(raw, dict):
            return None
        code = raw.get("kode") or raw.get("code")
        label = raw.get("beskrivelse") or raw.get("description") or raw.get("label")
        if not code and not label:
            return None
        return {"code": code, "label": label}
    if key == "business_address":
        return value.get("business_address")
    if key == "postal_address":
        return value.get("postal_address")
    if key == "bankrupt":
        return value.get("bankrupt")
    if key == "liquidating":
        return value.get("liquidating")
    if key == "latest_submitted_accounts":
        return value.get("latest_submitted_accounts")
    if key == "municipality":
        address = value.get("business_address") or {}
        return address.get("kommune") if isinstance(address, dict) else None
    return None


def _claim_span(field: str, value: Any) -> str:
    if field == "industry" and isinstance(value, dict):
        return f"industry_code={value.get('code')}; industry_label={value.get('label')}"
    return f"{field}={value}"


def project_registry_live_claims(contract: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Publish normalized facts already fetched from the exact BRREG entity endpoint.

    Version 1 fetched `registry_live` for every company but did not expose its
    normalized values in the final contract. This projection is zero-network and
    fills only fields that are absent from existing claims; it never replaces a
    published bulk-registry value or weakens website identity validation.
    """
    record = (profile.get("evidence") or {}).get("registry_live") or {}
    record_value = record.get("value")
    if record.get("status") != "available" or not isinstance(record_value, dict):
        return contract

    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    if len(org) != 9 or not org.isdigit():
        return contract
    if str(record_value.get("organisation_number") or "") != org:
        return contract

    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]
    existing_available = {
        str(claim.get("field") or "")
        for claim in claims
        if claim.get("availability") == "available"
    }
    evidence_by_id = {str(item.get("id")): item for item in evidence if item.get("id")}

    for field in MANAGED_FIELDS:
        if field in existing_available:
            continue
        value = _value(record, field)
        if value is None or value == "":
            continue
        evidence_id = _evidence_id(org, field, record)
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": record.get("source_url"),
            "source_class": "official",
            "retrieved_at": record.get("retrieved_at"),
            "content_sha256": record.get("content_sha256"),
            "claim_span": _claim_span(field, value),
        }
        if record.get("effective_at") is not None:
            evidence_by_id[evidence_id]["effective_at"] = record.get("effective_at")
        claims.append(
            {
                "field": field,
                "value": value,
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": [evidence_id],
                "claim_scope": "Exact live BRREG entity record for this organisation number.",
            }
        )

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
