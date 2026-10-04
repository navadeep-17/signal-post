from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse

from .website import _registered_domain

EMAIL_RE = re.compile(r"(?i)(?<![A-Z0-9._%+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![A-Z0-9._%+-])")
BLOCKED_LOCAL_PARTS = {
    "example",
    "name",
    "yourname",
    "email",
    "test",
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
}
MAX_CONTACT_EMAILS = 3


def _safe_same_domain_email(email: str, website_url: str) -> bool:
    value = str(email or "").strip().lower()
    if value.count("@") != 1:
        return False
    local, domain = value.split("@", 1)
    if not local or not domain or local in BLOCKED_LOCAL_PARTS:
        return False
    website_domain = _registered_domain(website_url)
    email_domain = _registered_domain("https://" + domain)
    return bool(website_domain and email_domain and website_domain == email_domain)


def company_site_contact_email_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract narrow first-party email claims from an already-qualified company page.

    H2c performs no network access. It only inspects the bounded identity/footer/contact text
    retained from the exact company website snapshot. Publication requires the email domain
    to match the verified website's registered domain. Cross-domain addresses abstain even
    when they may be legitimate brand/group contacts because H2c optimizes for precision.
    """

    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return []

    org = str(profile.get("organisation_number") or "")
    if len(org) != 9 or not org.isdigit():
        return []

    source_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    retrieved_at = str(website.get("retrieved_at") or "").strip()
    content_sha256 = str(value.get("content_sha256") or website.get("content_sha256") or "").strip()
    identity_text = str(value.get("identity_text_excerpt") or "")
    if not source_url.startswith(("http://", "https://")) or not retrieved_at or len(content_sha256) != 64:
        return []
    if not identity_text.strip():
        return []

    emails = sorted(
        {
            match.group(1).strip().lower()
            for match in EMAIL_RE.finditer(identity_text)
            if _safe_same_domain_email(match.group(1), source_url)
        }
    )[:MAX_CONTACT_EMAILS]

    observations: list[dict[str, Any]] = []
    for email in emails:
        observation_id = "company-site-email-" + hashlib.sha256(
            f"{org}|{email}|{source_url}|{content_sha256}".encode("utf-8")
        ).hexdigest()[:24]
        observations.append(
            {
                "id": observation_id,
                "organisation_number": org,
                "platform": "company_site",
                "signal_type": "company_profile",
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
                        "type": "same_registered_domain_contact_email",
                        "registered_domain": _registered_domain(source_url),
                        "email_domain": email.split("@", 1)[1],
                    },
                    {
                        "type": "bounded_identity_footer_excerpt",
                        "source_url": source_url,
                        "content_sha256": content_sha256,
                    },
                ],
                "acquisition_mode": "permitted_public_page",
                "rights_status": "approved",
                "source_class": "company_site",
                "evidence_span": f"Verified company page publishes contact email {email}",
                "contact_email": email,
                "metrics": {
                    "identity_score": identity.get("score"),
                    "claim_scope": (
                        "Contact email explicitly present in bounded footer/contact/legal text on the exact "
                        "company website; email domain matches the verified website registered domain."
                    ),
                },
                "strategy": "verified_company_page_same_domain_email_v1",
            }
        )
    return observations


def attach_company_site_contact_email_observations(profile: dict[str, Any]) -> dict[str, Any]:
    """Attach H2c observations idempotently without replacing H2a or future signals."""

    existing = [item for item in (profile.get("external_observations") or []) if isinstance(item, dict)]
    h2c = company_site_contact_email_observations(profile)
    by_id = {
        str(item.get("id")): item
        for item in [*existing, *h2c]
        if str(item.get("id") or "").strip()
    }
    profile["external_observations"] = sorted(
        by_id.values(),
        key=lambda row: (str(row.get("signal_type") or ""), str(row.get("platform") or ""), str(row.get("id") or "")),
    )
    return profile
