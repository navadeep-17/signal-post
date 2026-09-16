from __future__ import annotations

import hashlib
from typing import Any

from .external_footprint import publishable_observation


def _evidence_id(org: str, observation: dict[str, Any]) -> str:
    material = "|".join(
        [
            org,
            str(observation.get("id") or ""),
            str(observation.get("source_url") or ""),
            str(observation.get("content_sha256") or ""),
        ]
    )
    return "ev-workforce-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _validated_workforce(profile: dict[str, Any]) -> list[dict[str, Any]]:
    org = str(profile.get("organisation_number") or "")
    rows = []
    for observation in profile.get("external_observations") or []:
        if not isinstance(observation, dict):
            continue
        if observation.get("signal_type") != "workforce_snapshot":
            continue
        if str(observation.get("organisation_number") or "") != org:
            continue
        if not publishable_observation(observation):
            continue
        metrics = observation.get("metrics") or {}
        try:
            value = float(metrics.get("workforce_value"))
        except (TypeError, ValueError):
            continue
        if value < 0:
            continue
        rows.append(observation)
    return sorted(rows, key=lambda row: (str(row.get("platform") or ""), str(row.get("id") or "")))


def project_workforce_observations(contract: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Project qualified workforce observations as narrow external claims, idempotently."""

    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]

    managed_field = "external.workforce_snapshot"
    removed_ids = {
        evidence_id
        for claim in claims
        if claim.get("field") == managed_field
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    claims = [claim for claim in claims if claim.get("field") != managed_field]
    still_referenced = {
        evidence_id
        for claim in claims
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    evidence = [item for item in evidence if item.get("id") not in (removed_ids - still_referenced)]

    observations = _validated_workforce(profile)
    if not observations:
        return {
            **contract,
            "claims": claims,
            "evidence": sorted(evidence, key=lambda item: str(item.get("id") or "")),
        }

    evidence_by_id = {str(item.get("id")): item for item in evidence if item.get("id")}
    for observation in observations:
        metrics = observation.get("metrics") or {}
        evidence_id = _evidence_id(org, observation)
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": observation.get("source_url"),
            "source_class": "official",
            "retrieved_at": observation.get("retrieved_at"),
            "content_sha256": observation.get("content_sha256"),
            "claim_span": observation.get("evidence_span"),
            "effective_at": observation.get("effective_at"),
        }
        claims.append(
            {
                "field": managed_field,
                "value": {
                    "measure": metrics.get("measure"),
                    "value": metrics.get("workforce_value"),
                    "scope": metrics.get("scope"),
                },
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": [evidence_id],
                "platform": observation.get("platform"),
                "signal_type": "workforce_snapshot",
                "observation_id": observation.get("id"),
                "claim_scope": metrics.get("claim_scope"),
            }
        )

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
