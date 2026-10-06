from __future__ import annotations

import hashlib
from typing import Any

from .first_party_jobs import extract_current_first_party_jobs
from .hiring_intent import extract_company_authored_hiring_intent


MANAGED_FIELDS = {"external.hiring_intent", "external.job_posting"}


def _evidence_id(org: str, kind: str, source_url: str, content_sha256: str, material: str) -> str:
    raw = f"{org}|{kind}|{source_url}|{content_sha256}|{material}"
    return "ev-hiring-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _clean_managed(
    contract: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]
    removed_ids = {
        str(evidence_id)
        for claim in claims
        if claim.get("field") in MANAGED_FIELDS
        for evidence_id in claim.get("evidence_ids") or []
    }
    claims = [claim for claim in claims if claim.get("field") not in MANAGED_FIELDS]
    still_referenced = {
        str(evidence_id)
        for claim in claims
        for evidence_id in claim.get("evidence_ids") or []
    }
    evidence = [
        item
        for item in evidence
        if str(item.get("id") or "") not in (removed_ids - still_referenced)
    ]
    return claims, evidence


def project_hiring_semantics(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Project three-level hiring semantics without conflating them.

    Existing external.careers_page claims are left untouched and continue to mean only
    that the exact company has a careers/recruitment surface.

    This projector manages two stricter levels:
    - external.hiring_intent: explicit company-authored recruitment intent, but no
      assertion that a concrete vacancy is currently open.
    - external.job_posting: a specific current role satisfying the existing strict
      first-party title/deadline/employer/application checks.

    All extraction is over retained first-party evidence. This projector performs no
    network access.
    """
    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    claims, evidence = _clean_managed(contract)
    evidence_by_id = {
        str(item.get("id")): item
        for item in evidence
        if str(item.get("id") or "")
    }

    for item in extract_company_authored_hiring_intent(profile):
        source_url = str(item.get("source_url") or "")
        digest = str(item.get("content_sha256") or "")
        retrieved_at = str(item.get("retrieved_at") or "")
        span = str(item.get("evidence_span") or "")
        if (
            not source_url.startswith(("http://", "https://"))
            or len(digest) != 64
            or not retrieved_at
            or not span
        ):
            continue
        evidence_id = _evidence_id(
            org,
            "intent",
            source_url,
            digest,
            str(item.get("match_type") or ""),
        )
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": source_url,
            "source_class": "company_owned",
            "retrieved_at": retrieved_at,
            "content_sha256": digest,
            "claim_span": span[:1000],
        }
        claims.append(
            {
                "field": "external.hiring_intent",
                "value": {
                    "match_type": item.get("match_type"),
                    "source_url": source_url,
                },
                "availability": "available",
                "confidence": 0.97,
                "evidence_ids": [evidence_id],
                "platform": "company_site",
                "signal_type": "hiring_intent",
                "claim_scope": item.get("claim_scope"),
                "provenance": item.get("provenance"),
            }
        )

    for job in extract_current_first_party_jobs(profile):
        source_url = str(job.get("evidence_url") or "")
        digest = str(job.get("content_sha256") or "")
        retrieved_at = str(job.get("retrieved_at") or "")
        span = str(job.get("evidence_span") or "")
        role_url = str(job.get("url") or "")
        application_url = str(job.get("application_url") or role_url)
        title = str(job.get("title") or "").strip()
        deadline = str(job.get("deadline") or "").strip()
        if (
            not source_url.startswith(("http://", "https://"))
            or not role_url.startswith(("http://", "https://"))
            or not application_url.startswith(("http://", "https://"))
            or len(digest) != 64
            or not retrieved_at
            or not span
            or not title
            or not deadline
        ):
            continue
        evidence_id = _evidence_id(org, "job", source_url, digest, role_url)
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": source_url,
            "source_class": "company_owned",
            "retrieved_at": retrieved_at,
            "content_sha256": digest,
            "claim_span": span[:1000],
        }
        claims.append(
            {
                "field": "external.job_posting",
                "value": {
                    "title": title,
                    "url": role_url,
                    "application_url": application_url,
                    "deadline": deadline,
                },
                "availability": "available",
                "confidence": 0.98,
                "evidence_ids": [evidence_id],
                "platform": "company_site",
                "signal_type": "job_posting",
                "claim_scope": job.get("claim_scope"),
                "provenance": job.get("provenance"),
            }
        )

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
