from __future__ import annotations

import hashlib
from typing import Any

from .company_site_social import _safe_profile_url
from .identity import assess_social_identity
from .website import structured_social_links

STRATEGY = "verified_company_homepage_social_recovery_v1"


def _primary_page_provenance(profile: dict[str, Any]) -> tuple[dict[str, Any], str, str, str] | None:
    """Return the already-fetched exact homepage and its immutable provenance.

    `final_site_discovery.fetch_bounded_homepage()` stores the homepage as pages[0] and
    `_merge_secondary_page()` only appends a secondary identity page. Top-level website
    URL/hash and structured organisations therefore continue to describe the primary
    homepage even when `pages` has length > 1.
    """
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return None

    source_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    content_sha256 = str(value.get("content_sha256") or website.get("content_sha256") or "").strip()
    retrieved_at = str(website.get("retrieved_at") or "").strip()
    pages = [item for item in (value.get("pages") or []) if isinstance(item, dict)]
    if not source_url.startswith(("http://", "https://")) or len(content_sha256) != 64 or not retrieved_at or not pages:
        return None

    primary = pages[0]
    if str(primary.get("url") or "").rstrip("/") != source_url.rstrip("/"):
        return None
    if str(primary.get("content_sha256") or "") != content_sha256:
        return None
    return website, source_url, content_sha256, retrieved_at


def _homepage_social_assessments(profile: dict[str, Any], website: dict[str, Any]) -> list[dict[str, Any]]:
    """Rebuild the primary-homepage social candidate set from retained zero-network data."""
    value = website.get("value") or {}
    candidates: dict[tuple[str, str], dict[str, Any]] = {}

    # These assessments were produced from top-level homepage `social_links` before any
    # optional secondary identity page was appended. Reusing them is therefore safe once
    # pages[0] is proven to match the top-level source URL/hash.
    for item in value.get("social_link_assessments") or []:
        if not isinstance(item, dict):
            continue
        platform = str(item.get("platform") or "").strip()
        url = str(item.get("url") or "").strip()
        if platform and url:
            candidates[(platform, url)] = dict(item)

    # `structured_organisations` is also retained from the primary homepage. Older V5
    # identity projection assessed HTML social links but did not consistently add JSON-LD
    # Organization.sameAs URLs to that candidate set. Recover those declarations locally.
    for link in structured_social_links(value.get("structured_organisations") or []):
        platform = str(link.get("platform") or "").strip()
        url = str(link.get("url") or "").strip()
        if not platform or not url:
            continue
        key = (platform, url)
        candidates.setdefault(key, assess_social_identity(profile, link))

    return [candidates[key] for key in sorted(candidates)]


def recover_company_site_social_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Recover strict homepage-declared social handles with zero additional requests.

    This function never creates website identity and never treats a social URL as evidence
    by itself. Publication still requires: (1) the existing exact-company website gate,
    (2) immutable primary-homepage URL/hash provenance, (3) the deterministic social-handle
    identity gate, and (4) the existing canonical social URL shape gate.
    """
    provenance = _primary_page_provenance(profile)
    if provenance is None:
        return []
    website, source_url, content_sha256, retrieved_at = provenance
    identity = (website.get("value") or {}).get("identity_assessment") or {}
    org = str(profile.get("organisation_number") or "")
    if len(org) != 9 or not org.isdigit():
        return []

    existing = {
        (str(item.get("platform") or ""), str(item.get("profile_url") or "").rstrip("/"))
        for item in (profile.get("external_observations") or [])
        if isinstance(item, dict) and item.get("signal_type") == "profile_handle"
    }

    observations: list[dict[str, Any]] = []
    for item in _homepage_social_assessments(profile, website):
        if not item.get("publishable"):
            continue
        platform = str(item.get("platform") or "").strip()
        profile_url = str(item.get("url") or "").strip()
        if not platform or not _safe_profile_url(platform, profile_url):
            continue
        if (platform, profile_url.rstrip("/")) in existing:
            continue

        observation_id = "company-site-handle-v6e-" + hashlib.sha256(
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
                        "status": identity.get("status"),
                        "score": identity.get("score"),
                        "method": identity.get("method"),
                    },
                    {
                        "type": "primary_homepage_provenance",
                        "source_url": source_url,
                        "content_sha256": content_sha256,
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
                    "claim_scope": (
                        "Official profile URL declared in already-retained exact company homepage evidence; "
                        "the social-platform page/content was not fetched."
                    ),
                    "network_requests_added": 0,
                },
                "strategy": STRATEGY,
            }
        )
    return sorted(observations, key=lambda row: (row["platform"], row["profile_url"], row["id"]))


def attach_zero_network_social_recovery(profile: dict[str, Any]) -> dict[str, Any]:
    existing = [item for item in (profile.get("external_observations") or []) if isinstance(item, dict)]
    recovered = recover_company_site_social_observations(profile)
    by_id = {
        str(item.get("id")): item
        for item in [*existing, *recovered]
        if str(item.get("id") or "").strip()
    }
    profile["external_observations"] = sorted(
        by_id.values(),
        key=lambda row: (str(row.get("signal_type") or ""), str(row.get("platform") or ""), str(row.get("id") or "")),
    )
    return profile
