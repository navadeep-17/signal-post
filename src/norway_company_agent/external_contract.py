from __future__ import annotations

import hashlib
from typing import Any

from .external_footprint import publishable_observation


def _observation_evidence_id(org: str, observation: dict[str, Any]) -> str:
    material = "|".join(
        [
            org,
            str(observation.get("id") or ""),
            str(observation.get("source_url") or ""),
            str(observation.get("content_sha256") or ""),
            str(observation.get("profile_url") or ""),
        ]
    )
    return "ev-external-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _confidence(observation: dict[str, Any]) -> float:
    try:
        score = float((observation.get("metrics") or {}).get("identity_score"))
    except (TypeError, ValueError):
        score = 0.95
    return max(0.0, min(1.0, score))


def _validated_profile_handles(profile: dict[str, Any]) -> list[dict[str, Any]]:
    org = str(profile.get("organisation_number") or "")
    accepted = []
    for observation in profile.get("external_observations") or []:
        if not isinstance(observation, dict):
            continue
        if observation.get("signal_type") != "profile_handle":
            continue
        if str(observation.get("organisation_number") or "") != org:
            continue
        if not publishable_observation(observation):
            continue
        profile_url = str(observation.get("profile_url") or "").strip()
        if not profile_url.startswith(("http://", "https://")):
            continue
        accepted.append(observation)
    return sorted(
        accepted,
        key=lambda row: (str(row.get("platform") or ""), str(row.get("profile_url") or ""), str(row.get("id") or "")),
    )


def project_profile_handle_observations(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Replace raw social-link metadata with exact H2a profile-handle claims.

    The base website adapter historically projected every normalized social link discovered
    on an exact company site. H2a is stricter: only observations that pass both the company
    website identity gate and the deterministic handle identity gate survive. The source
    evidence remains the exact company page that declared the URL; no social-platform page
    is represented as fetched evidence.
    """

    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]

    # Remove the legacy broad social_links claim before rebuilding it from validated handles.
    removed_evidence_ids = {
        evidence_id
        for claim in claims
        if claim.get("field") == "social_links"
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    claims = [claim for claim in claims if claim.get("field") != "social_links"]
    still_referenced = {
        evidence_id
        for claim in claims
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    evidence = [
        item
        for item in evidence
        if item.get("id") not in (removed_evidence_ids - still_referenced)
    ]

    observations = _validated_profile_handles(profile)
    if not observations:
        return {**contract, "claims": claims, "evidence": sorted(evidence, key=lambda item: str(item.get("id") or ""))}

    evidence_by_id = {str(item.get("id")): item for item in evidence if item.get("id")}
    handle_values: list[dict[str, str]] = []
    compatibility_evidence_ids: list[str] = []

    for observation in observations:
        evidence_id = _observation_evidence_id(org, observation)
        platform = str(observation.get("platform") or "")
        profile_url = str(observation.get("profile_url") or "")
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": observation.get("source_url"),
            "source_class": "company_owned",
            "retrieved_at": observation.get("retrieved_at"),
            "content_sha256": observation.get("content_sha256"),
            "claim_span": observation.get("evidence_span"),
        }
        claims.append(
            {
                "field": "external.profile_handle",
                "value": profile_url,
                "availability": "available",
                "confidence": _confidence(observation),
                "evidence_ids": [evidence_id],
                "platform": platform,
                "signal_type": "profile_handle",
                "observation_id": observation.get("id"),
                "claim_scope": (observation.get("metrics") or {}).get("claim_scope"),
            }
        )
        handle_values.append({"platform": platform, "url": profile_url})
        compatibility_evidence_ids.append(evidence_id)

    claims.append(
        {
            "field": "social_links",
            "value": handle_values,
            "availability": "available",
            "confidence": min(_confidence(item) for item in observations),
            "evidence_ids": compatibility_evidence_ids,
            "signal_type": "profile_handle",
            "claim_scope": "Only profile URLs that passed H2a exact company-page and handle identity gates.",
        }
    )

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
