from __future__ import annotations

import hashlib
from typing import Any

from .company_site_contact import EMAIL_RE, MAX_CONTACT_EMAILS, _safe_same_domain_email
from .website import _registered_domain

STRATEGY = "verified_secondary_identity_page_contact_email_v1"


def _secondary_page_provenance(profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str] | None:
    """Return the already-retained H1c secondary identity page with immutable provenance.

    This function performs no network access and never creates website identity. It only
    operates after the existing exact-company website publication gate has succeeded and
    requires the retained `secondary_identity_page` URL/hash marker to match one retained
    page exactly.
    """
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return None

    verified_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    retrieved_at = str(website.get("retrieved_at") or "").strip()
    marker = value.get("secondary_identity_page") or {}
    secondary_url = str(marker.get("url") or "").strip()
    secondary_hash = str(marker.get("content_sha256") or "").strip()
    if (
        not verified_url.startswith(("http://", "https://"))
        or not retrieved_at
        or not secondary_url.startswith(("http://", "https://"))
        or len(secondary_hash) != 64
        or _registered_domain(secondary_url) != _registered_domain(verified_url)
    ):
        return None

    for page in value.get("pages") or []:
        if not isinstance(page, dict):
            continue
        page_url = str(page.get("url") or "").strip()
        page_hash = str(page.get("content_sha256") or "").strip()
        if page_url.rstrip("/") == secondary_url.rstrip("/") and page_hash == secondary_hash:
            return website, page, retrieved_at
    return None


def recover_secondary_contact_email_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Recover same-domain emails from an already-fetched exact-company secondary page.

    Publication requires all of:
    - existing exact-company website publication;
    - exact URL/hash match to the retained H1c secondary identity page marker;
    - same registered domain as the verified company website;
    - same-domain email address under the existing H2c email gate;
    - page-specific source URL and content hash.

    No additional request is made. Existing contact-email observations are deduplicated.
    """
    provenance = _secondary_page_provenance(profile)
    if provenance is None:
        return []
    website, page, retrieved_at = provenance
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    verified_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    page_url = str(page.get("url") or "").strip()
    page_hash = str(page.get("content_sha256") or "").strip()

    org = str(profile.get("organisation_number") or "")
    if len(org) != 9 or not org.isdigit():
        return []

    existing = {
        str(item.get("contact_email") or "").strip().lower()
        for item in (profile.get("external_observations") or [])
        if isinstance(item, dict)
        and item.get("signal_type") == "company_profile"
        and item.get("contact_email")
    }

    text = "\n".join(
        part
        for part in (
            str(page.get("identity_text_excerpt") or "").strip(),
            str(page.get("main_text_excerpt") or "").strip(),
        )
        if part
    )
    if not text:
        return []

    emails = sorted(
        {
            match.group(1).strip().lower()
            for match in EMAIL_RE.finditer(text)
            if _safe_same_domain_email(match.group(1), verified_url)
        }
        - existing
    )[:MAX_CONTACT_EMAILS]

    observations: list[dict[str, Any]] = []
    for email in emails:
        observation_id = "company-site-email-v9m5-" + hashlib.sha256(
            f"{org}|{email}|{page_url}|{page_hash}".encode("utf-8")
        ).hexdigest()[:24]
        observations.append(
            {
                "id": observation_id,
                "organisation_number": org,
                "platform": "company_site",
                "signal_type": "company_profile",
                "source_url": page_url,
                "retrieved_at": retrieved_at,
                "content_sha256": page_hash,
                "exact_entity": True,
                "identity_proof": [
                    {
                        "type": "website_identity_gate",
                        "status": identity.get("status"),
                        "score": identity.get("score"),
                        "method": identity.get("method"),
                    },
                    {
                        "type": "retained_secondary_identity_page",
                        "source_url": page_url,
                        "content_sha256": page_hash,
                    },
                    {
                        "type": "same_registered_domain_contact_email",
                        "registered_domain": _registered_domain(verified_url),
                        "email_domain": email.split("@", 1)[1],
                    },
                ],
                "acquisition_mode": "permitted_public_page",
                "rights_status": "approved",
                "source_class": "company_site",
                "evidence_span": f"Verified company secondary identity/contact page publishes contact email {email}",
                "contact_email": email,
                "metrics": {
                    "identity_score": identity.get("score"),
                    "network_requests_added": 0,
                    "claim_scope": (
                        "Contact email explicitly present in an already-retained exact-company secondary identity/contact page; "
                        "email domain matches the verified website registered domain."
                    ),
                },
                "strategy": STRATEGY,
            }
        )
    return observations


def attach_zero_network_contact_recovery(profile: dict[str, Any]) -> dict[str, Any]:
    existing = [item for item in (profile.get("external_observations") or []) if isinstance(item, dict)]
    recovered = recover_secondary_contact_email_observations(profile)
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
