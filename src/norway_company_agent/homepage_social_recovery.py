from __future__ import annotations

import hashlib
from typing import Any

from .company_site_social import _safe_profile_url
from .external_footprint import validate_observation
from .identity import assess_social_identity
from .website import structured_social_links


STRATEGY = "verified_homepage_social_recovery_v1"


def _primary_homepage_provenance(profile: dict[str, Any]) -> tuple[dict[str, Any], str, str, str] | None:
    """Return the already-fetched exact homepage and immutable provenance.

    V6e is deliberately zero-network. It only operates when the current website evidence
    is already publishable for the exact company and the first retained page matches the
    canonical website URL + content hash. Secondary identity pages may exist, but they do
    not become social-profile evidence here.
    """

    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return None

    source_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    digest = str(value.get("content_sha256") or website.get("content_sha256") or "").strip()
    retrieved_at = str(website.get("retrieved_at") or "").strip()
    if not source_url.startswith(("http://", "https://")) or len(digest) != 64 or not retrieved_at:
        return None

    pages = [page for page in (value.get("pages") or []) if isinstance(page, dict)]
    if not pages:
        return None
    primary = pages[0]
    if str(primary.get("url") or "").rstrip("/") != source_url.rstrip("/"):
        return None
    if str(primary.get("content_sha256") or "") != digest:
        return None

    return website, source_url, digest, retrieved_at


def _existing_handles(profile: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (str(item.get("platform") or ""), str(item.get("profile_url") or ""))
        for item in (profile.get("external_observations") or [])
        if isinstance(item, dict) and item.get("signal_type") == "profile_handle"
    }


def _candidate_rows(profile: dict[str, Any], value: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    """Recover only declarations retained from the exact homepage snapshot.

    Two sources are allowed:
    1. homepage HTML/social-link assessments already produced by the identity gate; and
    2. Organization JSON-LD ``sameAs`` retained in ``structured_organisations``.

    The first source must also be present in ``discovered_social_links``. This is important:
    secondary pages can be appended later for company-identity corroboration, while the
    discovered-social list is captured from the primary homepage before that merge.
    """

    discovered = {
        (str(item.get("platform") or ""), str(item.get("url") or ""))
        for item in (value.get("discovered_social_links") or [])
        if isinstance(item, dict)
    }
    candidates: dict[tuple[str, str], tuple[dict[str, Any], str]] = {}

    for item in value.get("social_link_assessments") or []:
        if not isinstance(item, dict) or not item.get("publishable"):
            continue
        key = (str(item.get("platform") or ""), str(item.get("url") or ""))
        if key not in discovered:
            continue
        candidates[key] = (dict(item), "retained_homepage_html_social_link")

    for link in structured_social_links(value.get("structured_organisations") or []):
        assessed = assess_social_identity(profile, link)
        if not assessed.get("publishable"):
            continue
        key = (str(assessed.get("platform") or ""), str(assessed.get("url") or ""))
        candidates.setdefault(key, (assessed, "retained_homepage_jsonld_same_as"))

    return [candidates[key] for key in sorted(candidates)]


def homepage_social_recovery_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Recover exact homepage-declared social profiles with zero new network requests."""

    provenance = _primary_homepage_provenance(profile)
    if provenance is None:
        return []
    website, source_url, digest, retrieved_at = provenance
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}

    org = str(profile.get("organisation_number") or "")
    if len(org) != 9 or not org.isdigit():
        return []

    existing = _existing_handles(profile)
    observations: list[dict[str, Any]] = []
    for item, declaration_mode in _candidate_rows(profile, value):
        platform = str(item.get("platform") or "").strip()
        profile_url = str(item.get("url") or "").strip()
        if not platform or not _safe_profile_url(platform, profile_url):
            continue
        if (platform, profile_url) in existing:
            continue

        observation_id = "homepage-social-recovery-" + hashlib.sha256(
            f"{org}|{platform}|{profile_url}|{source_url}|{digest}|{declaration_mode}".encode("utf-8")
        ).hexdigest()[:24]
        observation = {
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
                    "status": identity.get("status"),
                    "score": identity.get("score"),
                    "method": identity.get("method"),
                },
                {
                    "type": declaration_mode,
                    "platform": platform,
                    "profile_url": profile_url,
                    "source_url": source_url,
                    "content_sha256": digest,
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
            "evidence_span": (
                f"Retained exact company homepage declares {platform} profile {profile_url} "
                f"via {declaration_mode}"
            ),
            "profile_url": profile_url,
            "metrics": {
                "identity_score": item.get("identity_score"),
                "claim_scope": (
                    "Official social profile URL declared in the already-fetched exact company homepage; "
                    "no additional website or social-platform request was made."
                ),
                "network_requests_added": 0,
                "declaration_mode": declaration_mode,
            },
            "strategy": STRATEGY,
        }
        if validate_observation(observation):
            continue
        observations.append(observation)

    return sorted(observations, key=lambda row: (row["platform"], row["profile_url"], row["id"]))


def attach_homepage_social_recovery_observations(profile: dict[str, Any]) -> dict[str, Any]:
    """Attach V6e observations without changing or replacing incumbent observations."""

    existing = [item for item in (profile.get("external_observations") or []) if isinstance(item, dict)]
    recovered = homepage_social_recovery_observations(profile)
    by_id = {
        str(item.get("id")): item
        for item in [*existing, *recovered]
        if str(item.get("id") or "").strip()
    }
    profile["external_observations"] = sorted(
        by_id.values(),
        key=lambda row: (
            str(row.get("signal_type") or ""),
            str(row.get("platform") or ""),
            str(row.get("profile_url") or ""),
            str(row.get("id") or ""),
        ),
    )
    return profile
