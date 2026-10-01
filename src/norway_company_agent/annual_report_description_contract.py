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
            str(observation.get("company_description") or ""),
        ]
    )
    return "ev-annual-description-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _validated_descriptions(profile: dict[str, Any]) -> list[dict[str, Any]]:
    org = str(profile.get("organisation_number") or "")
    rows: list[dict[str, Any]] = []
    for observation in profile.get("external_observations") or []:
        if not isinstance(observation, dict):
            continue
        if observation.get("signal_type") != "company_profile":
            continue
        if observation.get("platform") != "brreg":
            continue
        if str(observation.get("organisation_number") or "") != org:
            continue
        description = str(observation.get("company_description") or "").strip()
        if len(description) < 40:
            continue
        if not publishable_observation(observation):
            continue
        rows.append(observation)
    return sorted(rows, key=lambda row: str(row.get("id") or ""))


def project_annual_report_company_description(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Fill a missing company description from exact official annual-report evidence.

    A verified company-site description remains preferred. This projector only adds a
    description when there is no already-available ``company_description`` claim.
    """

    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]

    if any(
        claim.get("field") == "company_description" and claim.get("availability") == "available"
        for claim in claims
    ):
        return {**contract, "claims": claims, "evidence": evidence}

    observations = _validated_descriptions(profile)
    if not observations:
        return {**contract, "claims": claims, "evidence": evidence}

    # One official annual report per target/effective period is expected. If multiple
    # candidate observations survive, publish only if they agree exactly; otherwise abstain.
    descriptions = {str(row.get("company_description") or "").strip() for row in observations}
    if len(descriptions) != 1:
        return {**contract, "claims": claims, "evidence": evidence}

    observation = observations[0]
    description = next(iter(descriptions))
    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    evidence_id = _evidence_id(org, observation)
    evidence_by_id = {str(item.get("id")): item for item in evidence if item.get("id")}
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
            "field": "company_description",
            "value": description,
            "availability": "available",
            "confidence": 1.0,
            "evidence_ids": [evidence_id],
            "platform": "brreg",
            "signal_type": "company_profile",
            "observation_id": observation.get("id"),
            "claim_scope": (observation.get("metrics") or {}).get("claim_scope"),
            "effective_at": observation.get("effective_at"),
        }
    )
    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
