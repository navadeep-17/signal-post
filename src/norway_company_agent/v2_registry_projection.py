from __future__ import annotations

import hashlib
import json
from typing import Any

from .registry_narrative import project_registry_narrative_claims


MANAGED_FIELDS = (
    "industry",
    "municipality_number",
    "bankrupt",
    "liquidating",
    "registration_date",
    "registered_address",
)
SOURCE_PATHS = {
    "industry": "/naeringskode1",
    "municipality_number": "/forretningsadresse/kommunenummer",
    "bankrupt": "/konkurs",
    "liquidating": "/underAvvikling",
    "registration_date": "/registreringsdatoEnhetsregisteret",
    "registered_address": "/forretningsadresse",
}
OWN_SIGNAL_TYPE = "official_registry_live_projection"


def _evidence_id(org: str, field: str, record: dict[str, Any]) -> str:
    material = "|".join(
        (
            org,
            "c12-registry-live",
            field,
            SOURCE_PATHS[field],
            str(record.get("source_url") or ""),
            str(record.get("content_sha256") or ""),
        )
    )
    return "ev-c12-registry-live-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _registry_live_record(profile: dict[str, Any]) -> dict[str, Any]:
    record = ((profile.get("evidence") or {}).get("registry_live") or {})
    return record if isinstance(record, dict) else {}


def _exact_live_value(record: dict[str, Any], field: str) -> Any:
    """Return only values present in the retained exact-org live BRREG response.

    ``official.normalize_entity`` preserves these values directly from the response body.
    A missing key normalizes to ``None``; importantly, explicit ``False`` remains
    distinguishable and is therefore publishable. Structured addresses are retained only
    when they contain at least one concrete address component.
    """

    if record.get("status") != "available":
        return None
    value = record.get("value") if isinstance(record.get("value"), dict) else {}

    if field == "industry":
        raw = value.get("industry")
        if not isinstance(raw, dict):
            return None
        code = raw.get("kode") if raw.get("kode") not in (None, "") else raw.get("code")
        description = (
            raw.get("beskrivelse") if raw.get("beskrivelse") not in (None, "") else raw.get("description")
        )
        if code in (None, "") and description in (None, ""):
            return None
        return {"code": code or None, "description": description or None}

    if field == "municipality_number":
        address = value.get("business_address")
        if not isinstance(address, dict):
            return None
        municipality_number = address.get("kommunenummer")
        if municipality_number in (None, ""):
            return None
        return str(municipality_number)

    if field == "bankrupt":
        raw = value.get("bankrupt")
        return raw if isinstance(raw, bool) else None

    if field == "liquidating":
        raw = value.get("liquidating")
        return raw if isinstance(raw, bool) else None

    if field == "registration_date":
        raw = str(value.get("registration_date") or "").strip()
        return raw or None

    if field == "registered_address":
        raw = value.get("business_address")
        if not isinstance(raw, dict):
            return None
        cleaned = {
            key: raw.get(key)
            for key in (
                "adresse",
                "postnummer",
                "poststed",
                "kommune",
                "kommunenummer",
                "land",
                "landkode",
            )
            if raw.get(key) not in (None, "", [])
        }
        return cleaned or None

    raise KeyError(field)


def _claim_span(field: str, value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{SOURCE_PATHS[field]}={encoded}"[:1000]


def _own_claim(claim: dict[str, Any]) -> bool:
    return claim.get("field") in MANAGED_FIELDS and claim.get("signal_type") in {
        OWN_SIGNAL_TYPE,
        "official_registry_projection",
    }


def project_v2_registry_claims(contract: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Project evaluator-facing BRREG fields from exact live evidence only.

    The projector fails closed: an ``available`` claim is emitted only when the value is
    present in the retained exact-organisation ``registry_live`` response whose URL/hash is
    attached as evidence. If the live response is available but a field is absent, the field
    is explicitly marked ``not_available``. Bulk/profile values never fill the gap.
    """

    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    if str(profile.get("organisation_number") or "") != org:
        raise ValueError("V2 registry projection organisation number mismatch")

    live = _registry_live_record(profile)
    source_url = str(live.get("source_url") or "").strip()
    retrieved_at = str(live.get("retrieved_at") or "").strip()
    content_sha256 = str(live.get("content_sha256") or "").strip()

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

    if live.get("status") != "available" or not source_url or not retrieved_at or len(content_sha256) != 64:
        projected = {
            **contract,
            "claims": claims,
            "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
        }
        return project_registry_narrative_claims(projected, profile)

    for field in MANAGED_FIELDS:
        value = _exact_live_value(live, field)
        evidence_id = _evidence_id(org, field, live)
        available = value is not None
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": source_url,
            "source_class": "official",
            "retrieved_at": retrieved_at,
            "content_sha256": content_sha256,
            "source_row_key": org,
            "source_field": SOURCE_PATHS[field],
            "claim_span": (
                _claim_span(field, value)
                if available
                else f"{SOURCE_PATHS[field]} not resolved in retained exact-org registry_live response"
            ),
        }
        claims.append(
            {
                "field": field,
                "value": value if available else None,
                "availability": "available" if available else "not_available",
                "confidence": 1.0,
                "evidence_ids": [evidence_id],
                "signal_type": OWN_SIGNAL_TYPE,
                "claim_scope": (
                    "Exact organisation-number BRREG live entity response; value must resolve "
                    f"from {SOURCE_PATHS[field]}. Bulk/profile fallback is prohibited."
                ),
            }
        )

    projected = {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
    return project_registry_narrative_claims(projected, profile)
