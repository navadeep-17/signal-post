from __future__ import annotations

import hashlib
import re
from typing import Any

from .website import _registered_domain

EMAIL_RE = re.compile(r"(?i)(?<![A-Z0-9._%+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![A-Z0-9._%+-])")
PHONE_RE = re.compile(
    r"(?i)\b(?:telefon|tlf|phone|tel)\.?\s*[:\-]?\s*"
    r"(?:\+?47[\s.\-]*)?((?:\d[\s.\-]?){8})\b"
)
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
MAX_CONTACT_PHONES = 3


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


def _normalised_org(profile: dict[str, Any]) -> str | None:
    org = str(profile.get("organisation_number") or "")
    return org if len(org) == 9 and org.isdigit() else None


def _contact_contexts(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Return trusted retained page contexts, homepage first then exact contact surface.

    Every context is already tied to the target legal entity. The homepage requires the
    ordinary website identity gate. A retained contact surface additionally requires the
    Phase B page-local exact identity decision stored by the bounded site scheduler.
    """
    org = _normalised_org(profile)
    if org is None:
        return []

    evidence_map = profile.get("evidence") or {}
    website = evidence_map.get("website") or {}
    website_value = website.get("value") or {}
    website_identity = website_value.get("identity_assessment") or {}
    contexts: list[dict[str, Any]] = []

    if website.get("status") == "available" and website_identity.get("publishable"):
        source_url = str(website_value.get("final_url") or website.get("source_url") or "").strip()
        retrieved_at = str(website.get("retrieved_at") or "").strip()
        content_sha256 = str(website_value.get("content_sha256") or website.get("content_sha256") or "").strip()
        identity_text = str(website_value.get("identity_text_excerpt") or "")
        if (
            source_url.startswith(("http://", "https://"))
            and retrieved_at
            and len(content_sha256) == 64
            and identity_text.strip()
        ):
            contexts.append(
                {
                    "kind": "homepage",
                    "source_url": source_url,
                    "retrieved_at": retrieved_at,
                    "content_sha256": content_sha256,
                    "identity_text": identity_text,
                    "identity_score": website_identity.get("score"),
                    "identity_proof": [
                        {
                            "type": "website_identity_gate",
                            "status": website_identity.get("status"),
                            "score": website_identity.get("score"),
                            "method": website_identity.get("method"),
                        },
                        {
                            "type": "bounded_identity_footer_excerpt",
                            "source_url": source_url,
                            "content_sha256": content_sha256,
                        },
                    ],
                }
            )

    surface = evidence_map.get("website_contact_surface") or {}
    surface_value = surface.get("value") or {}
    surface_identity = surface_value.get("contact_surface_identity") or {}
    if surface.get("status") == "available" and surface_identity.get("publishable"):
        source_url = str(surface_value.get("final_url") or surface.get("source_url") or "").strip()
        retrieved_at = str(surface.get("retrieved_at") or "").strip()
        content_sha256 = str(surface_value.get("content_sha256") or surface.get("content_sha256") or "").strip()
        identity_text = str(surface_value.get("identity_text_excerpt") or "")
        primary_domain = _registered_domain(
            str(website_value.get("final_url") or website.get("source_url") or "")
        )
        if (
            source_url.startswith(("http://", "https://"))
            and retrieved_at
            and len(content_sha256) == 64
            and identity_text.strip()
            and primary_domain
            and _registered_domain(source_url) == primary_domain
        ):
            score = 1.0 if surface_identity.get("target_org_number_on_page") else 0.98
            contexts.append(
                {
                    "kind": "contact_surface",
                    "source_url": source_url,
                    "retrieved_at": retrieved_at,
                    "content_sha256": content_sha256,
                    "identity_text": identity_text,
                    "identity_score": score,
                    "identity_proof": [
                        {
                            "type": "website_identity_gate",
                            "status": website_identity.get("status"),
                            "score": website_identity.get("score"),
                            "method": website_identity.get("method"),
                        },
                        {
                            "type": "contact_surface_exact_page_identity",
                            "method": surface_identity.get("method"),
                            "target_org_number_on_page": surface_identity.get("target_org_number_on_page"),
                            "full_legal_name_on_page": surface_identity.get("full_legal_name_on_page"),
                            "registry_location_on_page": surface_identity.get("registry_location_on_page"),
                        },
                        {
                            "type": "bounded_identity_footer_excerpt",
                            "source_url": source_url,
                            "content_sha256": content_sha256,
                        },
                    ],
                }
            )
    return contexts


def company_site_contact_email_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract narrow first-party email claims from retained exact company pages.

    H2c itself performs no network access. It inspects the already-qualified homepage and,
    when the bounded site scheduler retained one, an independently exact same-domain contact
    page. Publication requires the email domain to match the source page's registered domain.
    Homepage evidence wins deterministic deduplication when the same address appears twice.
    """
    org = _normalised_org(profile)
    if org is None:
        return []

    by_email: dict[str, dict[str, Any]] = {}
    for context in _contact_contexts(profile):
        source_url = str(context["source_url"])
        for match in EMAIL_RE.finditer(str(context["identity_text"])):
            email = match.group(1).strip().lower()
            if email in by_email or not _safe_same_domain_email(email, source_url):
                continue
            content_sha256 = str(context["content_sha256"])
            observation_id = "company-site-email-" + hashlib.sha256(
                f"{org}|{email}|{source_url}|{content_sha256}".encode("utf-8")
            ).hexdigest()[:24]
            by_email[email] = {
                "id": observation_id,
                "organisation_number": org,
                "platform": "company_site",
                "signal_type": "company_profile",
                "source_url": source_url,
                "retrieved_at": context["retrieved_at"],
                "content_sha256": content_sha256,
                "exact_entity": True,
                "identity_proof": [
                    *list(context["identity_proof"]),
                    {
                        "type": "same_registered_domain_contact_email",
                        "registered_domain": _registered_domain(source_url),
                        "email_domain": email.split("@", 1)[1],
                    },
                ],
                "acquisition_mode": "permitted_public_page",
                "rights_status": "approved",
                "source_class": "company_site",
                "evidence_span": f"Verified company page publishes contact email {email}",
                "contact_email": email,
                "metrics": {
                    "identity_score": context.get("identity_score"),
                    "claim_scope": (
                        "Contact email explicitly present in bounded footer/contact/legal text on an exact "
                        "company page; email domain matches the verified website registered domain."
                    ),
                },
                "strategy": (
                    "verified_company_contact_surface_same_domain_email_v1"
                    if context["kind"] == "contact_surface"
                    else "verified_company_page_same_domain_email_v1"
                ),
            }

    return [by_email[email] for email in sorted(by_email)[:MAX_CONTACT_EMAILS]]


def company_site_contact_phone_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract explicitly labelled Norwegian contact numbers from retained exact pages.

    Only numbers immediately following Telefon/Tlf/Phone/Tel inside bounded legal/contact/
    footer text qualify. Homepage evidence wins deterministic deduplication. The claim means
    only that the exact company page published a contact number; no person, role, ownership,
    switchboard, or deliverability inference is made.
    """
    org = _normalised_org(profile)
    if org is None:
        return []

    by_phone: dict[str, dict[str, Any]] = {}
    for context in _contact_contexts(profile):
        source_url = str(context["source_url"])
        for match in PHONE_RE.finditer(str(context["identity_text"])):
            digits = re.sub(r"\D", "", match.group(1))
            if len(digits) != 8:
                continue
            phone = "+47" + digits
            if phone in by_phone:
                continue
            content_sha256 = str(context["content_sha256"])
            observation_id = "company-site-phone-" + hashlib.sha256(
                f"{org}|{phone}|{source_url}|{content_sha256}".encode("utf-8")
            ).hexdigest()[:24]
            by_phone[phone] = {
                "id": observation_id,
                "organisation_number": org,
                "platform": "company_site",
                "signal_type": "company_profile",
                "source_url": source_url,
                "retrieved_at": context["retrieved_at"],
                "content_sha256": content_sha256,
                "exact_entity": True,
                "identity_proof": [
                    *list(context["identity_proof"]),
                    {
                        "type": "explicit_labelled_contact_phone",
                        "labels": ["telefon", "tlf", "phone", "tel"],
                        "normalized_country_code": "+47",
                    },
                ],
                "acquisition_mode": "permitted_public_page",
                "rights_status": "approved",
                "source_class": "company_site",
                "evidence_span": f"Verified company page explicitly labels contact phone {phone}",
                "contact_phone": phone,
                "metrics": {
                    "identity_score": context.get("identity_score"),
                    "claim_scope": (
                        "Contact phone explicitly labelled in bounded footer/contact/legal text on an exact "
                        "company page; normalized to Norwegian +47 format without inferring a person or role."
                    ),
                },
                "strategy": (
                    "verified_company_contact_surface_labelled_phone_v1"
                    if context["kind"] == "contact_surface"
                    else "verified_company_page_labelled_phone_v1"
                ),
            }

    return [by_phone[phone] for phone in sorted(by_phone)[:MAX_CONTACT_PHONES]]


def attach_company_site_contact_email_observations(profile: dict[str, Any]) -> dict[str, Any]:
    """Attach zero-network exact-site email and phone observations idempotently."""
    existing = [item for item in (profile.get("external_observations") or []) if isinstance(item, dict)]
    h2c = [
        *company_site_contact_email_observations(profile),
        *company_site_contact_phone_observations(profile),
    ]
    managed_prefixes = ("company-site-email-", "company-site-phone-")
    existing = [
        item for item in existing
        if not str(item.get("id") or "").startswith(managed_prefixes)
    ]
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
