from __future__ import annotations

import hashlib
from typing import Any


def homepage_social_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert exact company-homepage social declarations into profile-handle observations.

    The current website snapshot model merges social links discovered across bounded pages but
    does not retain a per-link source page. To keep claim-level provenance exact, this first
    version only emits observations when the exact website snapshot contains one captured page.
    In that case the website source URL/content hash is the page that declared every retained
    social link. Multi-page snapshots abstain until per-link provenance is stored explicitly.
    """
    website = (profile.get("evidence") or {}).get("website") or {}
    value = website.get("value") or {}
    website_identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not website_identity.get("publishable"):
        return []

    source_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    digest = str(value.get("content_sha256") or website.get("content_sha256") or "").strip()
    retrieved_at = str(website.get("retrieved_at") or "").strip()
    pages = [page for page in (value.get("pages") or []) if isinstance(page, dict)]
    if not source_url or len(digest) != 64 or not retrieved_at or len(pages) != 1:
        return []

    page = pages[0]
    page_url = str(page.get("url") or "").rstrip("/")
    page_digest = str(page.get("content_sha256") or "")
    if page_url != source_url.rstrip("/") or page_digest != digest:
        return []

    assessments = value.get("social_link_assessments") or []
    rows: list[dict[str, Any]] = []
    org = str(profile.get("organisation_number") or "")
    if not org.isdigit():
        return []

    for item in assessments:
        if not isinstance(item, dict) or not item.get("publishable"):
            continue
        platform = str(item.get("platform") or "").strip()
        profile_url = str(item.get("url") or "").strip()
        if not platform or not profile_url.startswith(("http://", "https://")):
            continue
        observation_id = "company-site-handle-" + hashlib.sha256(
            f"{org}|{platform}|{profile_url}".encode("utf-8")
        ).hexdigest()[:24]
        rows.append({
            "id": observation_id,
            "organisation_number": org,
            "platform": platform,
            "signal_type": "profile_handle",
            "source_url": source_url,
            "retrieved_at": retrieved_at,
            "content_sha256": digest,
            "exact_entity": True,
            "identity_proof": [
                {
                    "type": "website_identity_gate",
                    "status": website_identity.get("status"),
                    "score": website_identity.get("score"),
                    "method": website_identity.get("method"),
                },
                {
                    "type": "company_homepage_declared_social_link",
                    "platform": platform,
                    "profile_url": profile_url,
                },
                {
                    "type": "social_handle_identity_gate",
                    "score": item.get("identity_score"),
                    "method": item.get("method"),
                    "matched_tokens": list(item.get("matched_tokens") or []),
                },
            ],
            "acquisition_mode": "permitted_public_page",
            "rights_status": "approved",
            "source_class": "company_site",
            "evidence_span": f"Exact company homepage declares {platform} profile {profile_url}",
            "profile_url": profile_url,
            "metrics": {
                "identity_score": item.get("identity_score"),
                "claim_scope": "official profile URL declared by the exact company homepage; no social-platform content was fetched",
            },
            "strategy": "verified_handle_extraction",
        })
    return sorted(rows, key=lambda row: (row["platform"], row["profile_url"]))
