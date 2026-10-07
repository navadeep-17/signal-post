from __future__ import annotations

import hashlib
from typing import Any


def _evidence_id(org: str, careers_url: str, content_sha256: str) -> str:
    material = f"{org}|{careers_url}|{content_sha256}"
    return "ev-careers-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _confidence(website: dict[str, Any]) -> float:
    try:
        score = float((((website.get("value") or {}).get("identity_assessment") or {}).get("score")))
    except (TypeError, ValueError):
        score = 0.95
    return max(0.0, min(1.0, score))


def project_careers_page_claims(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Project exact-homepage careers links without modifying the frozen V1 projector.

    The source is the already verified company homepage. A careers link is accepted only
    when it was captured from that same homepage snapshot and therefore carries the same
    content hash. This is a narrow careers-presence claim and never an active-job claim.
    Projection is deterministic and idempotent.
    """

    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]

    managed_field = "external.careers_page"
    removed_evidence_ids = {
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
    evidence = [
        item
        for item in evidence
        if item.get("id") not in (removed_evidence_ids - still_referenced)
    ]

    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    final_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    website_hash = str(website.get("content_sha256") or "").strip()
    retrieved_at = website.get("retrieved_at")

    if (
        website.get("status") != "available"
        or not assessment.get("publishable")
        or not final_url.startswith(("http://", "https://"))
        or len(website_hash) != 64
        or not retrieved_at
    ):
        return {
            **contract,
            "claims": claims,
            "evidence": sorted(evidence, key=lambda item: str(item.get("id") or "")),
        }

    evidence_by_id = {str(item.get("id")): item for item in evidence if item.get("id")}
    seen_urls: set[str] = set()
    for careers in value.get("careers_links") or []:
        if not isinstance(careers, dict):
            continue
        careers_url = str(careers.get("url") or "").strip()
        homepage_url = str(careers.get("homepage_url") or "").strip()
        homepage_hash = str(careers.get("homepage_content_sha256") or "").strip()
        if (
            not careers_url.startswith(("http://", "https://"))
            or careers_url in seen_urls
            or homepage_url != final_url
            or homepage_hash != website_hash
        ):
            continue

        evidence_id = _evidence_id(org, careers_url, website_hash)
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": final_url,
            "source_class": "company_owned",
            "retrieved_at": retrieved_at,
            "content_sha256": website_hash,
            "claim_span": str(careers.get("evidence_span") or f"Homepage careers link: {careers_url}"),
            "extraction_method": "verified_homepage_same_company_host_careers_link_v1",
            "identity_proof": {
                "method": assessment.get("method"),
                "status": assessment.get("status"),
                "score": assessment.get("score"),
                "publishable": bool(assessment.get("publishable")),
                "homepage_url": final_url,
                "homepage_content_sha256": website_hash,
                "careers_url": careers_url,
                "same_snapshot_homepage_declaration": True,
            },
        }
        claims.append(
            {
                "field": managed_field,
                "value": {
                    "url": careers_url,
                    "anchor_text": str(careers.get("anchor_text") or "").strip() or None,
                },
                "availability": "available",
                "confidence": _confidence(website),
                "evidence_ids": [evidence_id],
                "platform": "company_site",
                "signal_type": "careers_page",
                "claim_scope": str(careers.get("claim_scope") or ""),
            }
        )
        seen_urls.add(careers_url)

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
