from __future__ import annotations

import hashlib
from typing import Any

from .policy_support import POLICY_SUPPORT_RIGHTS, POLICY_SUPPORT_SOURCE_URL


def _evidence_id(org: str, event: dict[str, Any]) -> str:
    material = "|".join(
        (
            org,
            str(event.get("id") or ""),
            str(event.get("source_row_sha256") or ""),
            str(event.get("event_date") or ""),
        )
    )
    return "ev-policy-support-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def project_policy_support_events(
    contract: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Project exact-org historical government-support events into the final contract.

    This family is intentionally typed as official historical support. It must never be
    interpreted as company-authored news, hiring, social activity, review sentiment, or a
    claim that the support is current.
    """

    org = str(contract.get("organisation_number") or "")
    field = "official.support_policy_event"
    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]

    removed_ids = {
        evidence_id
        for claim in claims
        if claim.get("field") == field
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    claims = [claim for claim in claims if claim.get("field") != field]
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

    for event in sorted(
        [row for row in events if str(row.get("organisation_number") or "") == org],
        key=lambda row: (str(row.get("event_date") or ""), str(row.get("id") or "")),
        reverse=True,
    ):
        evidence_id = _evidence_id(org, event)
        event_date = str(event.get("event_date") or "")
        actor = str(event.get("actor") or "").strip() or None
        instrument = str(event.get("instrument") or "").strip() or None
        contribution_type = str(event.get("contribution_type") or "").strip() or None
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": POLICY_SUPPORT_SOURCE_URL,
            "source_class": "official_open_data",
            "retrieved_at": event.get("retrieved_at"),
            "effective_at": event_date,
            "content_sha256": event.get("source_row_sha256"),
            "source_snapshot_sha256": event.get("source_snapshot_sha256"),
            "source_row_number": event.get("source_row_number"),
            "claim_span": event.get("evidence_span"),
            "identity_proof": (
                f"Pinned NLOD policy-support row organisation number equals target {org}"
            ),
            "extraction_method": "pinned_policy_support_exact_org_row_v1",
        }
        claims.append(
            {
                "field": field,
                "value": {
                    "kind": "historical_policy_support",
                    "effective_at": event_date,
                    "actor": actor,
                    "instrument": instrument,
                    "contribution_type": contribution_type,
                    "awarded_amount": event.get("awarded_amount"),
                    "currency": event.get("currency"),
                },
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": [evidence_id],
                "platform": "government_open_data",
                "signal_type": "official_policy_support_event",
                "observation_id": event.get("id"),
                "claim_scope": (
                    "Historical government/business-policy support allocation recorded in the pinned open dataset; "
                    "does not imply current support, company-authored activity, hiring, social engagement, or sentiment."
                ),
            }
        )

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
