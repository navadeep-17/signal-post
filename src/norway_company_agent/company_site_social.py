from __future__ import annotations

import hashlib
from typing import Any


def company_site_social_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Project exact company-page social declarations into profile-handle observations.

    This extractor performs no network access. It only reuses an already-qualified company
    website snapshot. Because the current website model can merge social links discovered
    across multiple bounded pages without retaining per-link page provenance, H2a abstains
    whenever more than one captured page contributed to the snapshot. A later model may
    relax this only after per-link source URL/hash provenance is stored explicitly.

    The narrow claim is: "this exact company page declared this social profile URL".
    No social-platform page, post, metric, currentness or sentiment is implied.
    """

    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    website_identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not website_identity.get("publishable"):
        return []

    org = str(profile.get("organisation_number") or "")
    if len(org) != 9 or not org.isdigit():
        return []

    source_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    content_sha256 = str(value.get("content_sha256") or website.get("content_sha256") or "").strip()
    retrieved_at = str(website.get("retrieved_at") or "").strip()
    if not source_url.startswith(("http://", "https://")) or len(content_sha256) != 64 or not retrieved_at:
        return []

    pages = [page for page in (value.get("pages") or []) if isinstance(page, dict)]
    if len(pages) != 1:
        return []
    page = pages[0]
    if str(page.get("url") or "").rstrip("/") != source_url.rstrip("/"):
        return []
    if str(page.get("content_sha256") or "") != content_sha256:
        return []

    observations: list[dict[str, Any]] = []
    for item in value.get("social_link_assessments") or []:
        if not isinstance(item, dict) or not item.get("publishable"):
            continue
        platform = str(item.get("platform") or "").strip()
        profile_url = str(item.get("url") or "").strip()
        if not platform or not profile_url.startswith(("http://", "https://")):
            continue

        observation_id = "company-site-handle-" + hashlib.sha256(
            f"{org}|{platform}|{profile_url}|{source_url}|{content_sha256}".encode("utf-8")
        ).hexdigest()[:24]
        observations.append(
            {
                "id": observation_id,
                "organisation_number": org,
                "platform": platform,
                "signal_type": "profile_handle",
                "source_url": source_url,
                "retrieved_at": retrieved_at,
                "content_sha256": content_sha256,
                "exact_entity": True,
                "identity_proof": [
                    {
                        "type": "website_identity_gate",
                        "status": website_identity.get("status"),
                        "score": website_identity.get("score"),
                        "method": website_identity.get("method"),
                    },
                    {
                        "type": "company_page_declared_social_link",
                        "platform": platform,
                        "profile_url": profile_url,
                        "source_url": source_url,
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
                "evidence_span": f"Exact company page declares {platform} profile {profile_url}",
                "profile_url": profile_url,
                "metrics": {
                    "identity_score": item.get("identity_score"),
                    "claim_scope": (
                        "Official profile URL declared by the exact company page; "
                        "the social-platform page/content was not fetched."
                    ),
                },
                "strategy": "verified_company_page_handle_extraction_v1",
            }
        )

    return sorted(observations, key=lambda row: (row["platform"], row["profile_url"], row["id"]))


def attach_company_site_social_observations(profile: dict[str, Any]) -> dict[str, Any]:
    """Attach H2a observations without overwriting other future external observations."""

    existing = [item for item in (profile.get("external_observations") or []) if isinstance(item, dict)]
    h2a = company_site_social_observations(profile)
    by_id = {
        str(item.get("id")): item
        for item in [*existing, *h2a]
        if str(item.get("id") or "").strip()
    }
    profile["external_observations"] = sorted(
        by_id.values(), key=lambda row: (str(row.get("signal_type") or ""), str(row.get("platform") or ""), str(row.get("id") or ""))
    )
    return profile
