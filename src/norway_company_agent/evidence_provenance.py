from __future__ import annotations

from typing import Any

WEBSITE_BACKED_FIELDS = {
    "official_website",
    "company_description",
    "social_links",
    "external.careers_page",
}


def _present(value: Any) -> bool:
    return value is not None and value != ""


def observation_provenance(observation: dict[str, Any]) -> dict[str, Any]:
    """Return evaluator-visible provenance already present on a qualified observation.

    No proof is synthesized here. `identity_proof` is copied verbatim from the retained
    observation. `strategy` is the collector/extractor strategy that produced that
    observation and is surfaced under the evaluator-facing `extraction_method` label.
    """

    result: dict[str, Any] = {}
    if _present(observation.get("identity_proof")):
        result["identity_proof"] = observation.get("identity_proof")
    method = observation.get("extraction_method") or observation.get("strategy")
    if _present(method):
        result["extraction_method"] = method
    return result


def website_provenance(website: dict[str, Any]) -> dict[str, Any]:
    """Expose the retained exact-company website identity assessment without changing it."""

    value = website.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    result: dict[str, Any] = {}
    if isinstance(assessment, dict) and assessment:
        result["identity_proof"] = dict(assessment)
        if _present(assessment.get("method")):
            result["extraction_method"] = assessment.get("method")
    return result


def _website_fingerprint(profile: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    final_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    content_hash = str(website.get("content_sha256") or "").strip()
    return final_url, content_hash, website


def project_evaluator_visible_provenance(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Attach already-retained identity/extraction provenance to final evidence rows.

    The pass is deterministic and zero-network. It never changes claim values, confidence,
    availability, identity thresholds, evidence IDs, request accounting, or source hashes.
    Provenance is added only when it can be joined back to the exact retained observation
    by `observation_id`, or to the exact verified website by URL + content hash.
    """

    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]
    evidence_by_id = {str(item.get("id")): item for item in evidence if item.get("id")}

    observations = {
        str(item.get("id")): item
        for item in (profile.get("external_observations") or [])
        if isinstance(item, dict) and item.get("id")
    }
    website_url, website_hash, website = _website_fingerprint(profile)
    website_trace = website_provenance(website)

    for claim in claims:
        evidence_ids = [str(value) for value in (claim.get("evidence_ids") or []) if value]
        if not evidence_ids:
            continue

        trace: dict[str, Any] = {}
        observation_id = str(claim.get("observation_id") or "")
        observation = observations.get(observation_id)
        if observation is not None:
            trace = observation_provenance(observation)
        elif str(claim.get("field") or "") in WEBSITE_BACKED_FIELDS and website_trace:
            matched_website_evidence = any(
                str((evidence_by_id.get(evidence_id) or {}).get("source_url") or "").strip() == website_url
                and str((evidence_by_id.get(evidence_id) or {}).get("content_sha256") or "").strip() == website_hash
                for evidence_id in evidence_ids
            )
            if matched_website_evidence:
                trace = website_trace

        if not trace:
            continue
        for evidence_id in evidence_ids:
            row = evidence_by_id.get(evidence_id)
            if row is None:
                continue
            for key, value in trace.items():
                if not _present(row.get(key)) and _present(value):
                    row[key] = value

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
