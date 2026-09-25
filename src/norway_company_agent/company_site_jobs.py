from __future__ import annotations

import hashlib
from typing import Any

from .structured_jobs import hiring_organisation_matches

MAX_STRUCTURED_JOBS = 8


def company_site_job_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Publish explicit structured JobPosting facts from an already-qualified company page.

    This path is zero-network. It requires the company website to have passed the
    exact-entity identity gate and the JobPosting's hiringOrganization to match
    the legal entity. Generic careers pages and keyword-only hiring language are
    intentionally ignored.
    """
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return []

    org = str(profile.get("organisation_number") or "")
    legal_name = str(profile.get("name") or "").strip()
    if len(org) != 9 or not org.isdigit() or not legal_name:
        return []

    page_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    retrieved_at = str(website.get("retrieved_at") or "").strip()
    content_sha256 = str(value.get("content_sha256") or website.get("content_sha256") or "").strip()
    if not page_url.startswith(("http://", "https://")) or not retrieved_at or len(content_sha256) != 64:
        return []

    rows = value.get("structured_job_postings") or []
    if not isinstance(rows, list):
        return []

    observations: list[dict[str, Any]] = []
    for job in rows[:MAX_STRUCTURED_JOBS]:
        if not isinstance(job, dict):
            continue
        title = str(job.get("title") or "").strip()
        job_url = str(job.get("url") or "").strip()
        hiring_organisation = str(job.get("hiring_organization") or "").strip() or None
        if not title or not job_url.startswith(("http://", "https://")):
            continue
        if not hiring_organisation_matches(legal_name, hiring_organisation):
            continue

        observation_id = "company-site-job-" + hashlib.sha256(
            f"{org}|{title}|{job_url}|{content_sha256}".encode("utf-8")
        ).hexdigest()[:24]
        observations.append(
            {
                "id": observation_id,
                "organisation_number": org,
                "platform": "company_site",
                "signal_type": "job_posting",
                "source_url": page_url,
                "retrieved_at": retrieved_at,
                "content_sha256": content_sha256,
                "exact_entity": True,
                "identity_proof": [
                    {
                        "type": "website_identity_gate",
                        "status": identity.get("status"),
                        "score": identity.get("score"),
                        "method": identity.get("method"),
                    },
                    {
                        "type": "structured_jobposting_hiring_organisation_match",
                        "legal_name": legal_name,
                        "hiring_organisation": hiring_organisation,
                    },
                ],
                "acquisition_mode": "permitted_public_page",
                "rights_status": "approved",
                "source_class": "company_site",
                "evidence_span": f"Verified company page publishes JobPosting: {title} -> {job_url}",
                "job": {
                    "title": title,
                    "url": job_url,
                    "hiring_organization": hiring_organisation,
                    "date_posted": job.get("date_posted"),
                    "valid_through": job.get("valid_through"),
                    "employment_type": job.get("employment_type"),
                    "description_excerpt": job.get("description_excerpt"),
                },
                "metrics": {
                    "identity_score": identity.get("score"),
                    "claim_scope": (
                        "Explicit schema.org JobPosting embedded in an exact verified company page; "
                        "hiringOrganization matches the legal entity. Generic careers text is excluded."
                    ),
                },
                "strategy": "structured_jobposting_verified_company_page_v1",
            }
        )
    return observations


def attach_company_site_job_observations(profile: dict[str, Any]) -> dict[str, Any]:
    existing = [item for item in (profile.get("external_observations") or []) if isinstance(item, dict)]
    jobs = company_site_job_observations(profile)
    by_id = {
        str(item.get("id")): item
        for item in [*existing, *jobs]
        if str(item.get("id") or "").strip()
    }
    profile["external_observations"] = sorted(
        by_id.values(),
        key=lambda row: (str(row.get("signal_type") or ""), str(row.get("platform") or ""), str(row.get("id") or "")),
    )
    return profile
