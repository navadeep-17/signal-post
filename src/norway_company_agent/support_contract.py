from __future__ import annotations

import hashlib
from typing import Any

from .evidence_provenance import project_evaluator_visible_provenance
from .external_footprint import publishable_observation


SUPPORT_AWARD_SOURCE_URL = "https://stotte.brreg.no/nb/oppslag/stoettetildeling/totalbestand/csv"
SUPPORT_AWARD_EXTRACTION_METHOD = "official_support_registry_primary_recipient_exact_org_v1"


def _evidence_id(org: str, observation: dict[str, Any]) -> str:
    material = "|".join(
        [
            org,
            str(observation.get("id") or ""),
            str(observation.get("source_url") or ""),
            str(observation.get("content_sha256") or ""),
        ]
    )
    return "ev-support-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _validated_support_awards(profile: dict[str, Any]) -> list[dict[str, Any]]:
    org = str(profile.get("organisation_number") or "")
    rows: list[dict[str, Any]] = []
    for observation in profile.get("external_observations") or []:
        if not isinstance(observation, dict):
            continue
        if observation.get("signal_type") != "official_support_award":
            continue
        if str(observation.get("organisation_number") or "") != org:
            continue
        if not publishable_observation(observation):
            continue
        event = observation.get("event") or {}
        if event.get("kind") != "support_award" or not event.get("awarded_at"):
            continue
        rows.append(observation)
    return sorted(rows, key=lambda row: (str(row.get("effective_at") or ""), str(row.get("id") or "")), reverse=True)


def project_support_award_evidence_provenance(contract: dict[str, Any]) -> dict[str, Any]:
    """Expose the already-enforced support extraction method on final evidence rows.

    This is deliberately a final-contract projection as well as a collector-time helper.
    Older retained profiles can omit support observations even though their final contract
    already contains exact-recipient support claims and official source evidence. The
    method is therefore attached only when the final claim and evidence together prove the
    existing BRREG Støtteregisteret exact-primary-recipient path. No claim value, evidence
    id, source, hash, identity proof, or request accounting is changed.
    """

    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]
    evidence_by_id = {str(item.get("id")): item for item in evidence if item.get("id")}

    for claim in claims:
        if claim.get("field") != "official.support_award":
            continue
        if claim.get("availability") != "available":
            continue
        if claim.get("platform") != "brreg":
            continue
        if claim.get("signal_type") != "official_support_award":
            continue
        if claim.get("claim_scope") != "official_recipient_support_event":
            continue
        for evidence_id in claim.get("evidence_ids") or []:
            row = evidence_by_id.get(str(evidence_id))
            if row is None:
                continue
            if str(row.get("source_url") or "") != SUPPORT_AWARD_SOURCE_URL:
                continue
            if row.get("source_class") != "official":
                continue
            if len(str(row.get("content_sha256") or "")) != 64:
                continue
            if not row.get("source_row_key"):
                continue
            if not row.get("extraction_method"):
                row["extraction_method"] = SUPPORT_AWARD_EXTRACTION_METHOD

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }


def project_support_award_observations(contract: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Project exact-recipient BRREG support awards into explicit official event claims."""

    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]
    field = "official.support_award"

    removed_ids = {
        evidence_id
        for claim in claims
        if claim.get("field") == field
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    claims = [claim for claim in claims if claim.get("field") != field]
    still_referenced = {evidence_id for claim in claims for evidence_id in (claim.get("evidence_ids") or [])}
    evidence = [item for item in evidence if item.get("id") not in (removed_ids - still_referenced)]
    evidence_by_id = {str(item.get("id")): item for item in evidence if item.get("id")}

    for observation in _validated_support_awards(profile):
        event = observation.get("event") or {}
        evidence_id = _evidence_id(org, observation)
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": observation.get("source_url"),
            "source_class": "official",
            "retrieved_at": observation.get("retrieved_at"),
            "content_sha256": observation.get("content_sha256"),
            "source_snapshot_sha256": observation.get("source_snapshot_sha256"),
            "claim_span": observation.get("evidence_span"),
            "effective_at": observation.get("effective_at"),
            "source_row_number": observation.get("source_row_number"),
            "source_row_key": observation.get("source_row_key"),
            "extraction_method": SUPPORT_AWARD_EXTRACTION_METHOD,
        }
        claims.append(
            {
                "field": field,
                "value": dict(event),
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": [evidence_id],
                "platform": "brreg",
                "signal_type": "official_support_award",
                "observation_id": observation.get("id"),
                "claim_scope": "official_recipient_support_event",
            }
        )

    projected = project_evaluator_visible_provenance(
        {
            **contract,
            "claims": claims,
            "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
        },
        profile,
    )
    return project_support_award_evidence_provenance(projected)
