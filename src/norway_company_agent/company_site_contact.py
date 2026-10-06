from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse

from .identity import _tokens
from .website import _registered_domain

EMAIL_RE = re.compile(r"(?i)(?<![A-Z0-9._%+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![A-Z0-9._%+-])")
NINE_DIGIT_RE = re.compile(r"(?<!\d)(\d(?:[\s.\-]?\d){8})(?!\d)")
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
STRUCTURED_ID_KEYS = {"identifier", "taxid", "vatid"}
STRUCTURED_NAME_KEYS = ("legalName", "name", "alternateName")


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


def _structured_identity_numbers(value: Any, *, enabled: bool = False) -> set[str]:
    """Extract nine-digit values only from schema identity fields.

    Arbitrary numbers elsewhere in JSON-LD (telephone, postal code, etc.) are not legal
    identity evidence. identifier, taxID and vatID are the only traversals that enable
    number extraction.
    """

    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            child_enabled = enabled or str(key).casefold() in STRUCTURED_ID_KEYS
            found.update(_structured_identity_numbers(child, enabled=child_enabled))
    elif isinstance(value, list):
        for child in value:
            found.update(_structured_identity_numbers(child, enabled=enabled))
    elif enabled and isinstance(value, (str, int)):
        text = str(value)
        for match in NINE_DIGIT_RE.finditer(text):
            digits = re.sub(r"\D", "", match.group(1))
            if len(digits) == 9:
                found.add(digits)
    return found


def _structured_names(node: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in STRUCTURED_NAME_KEYS:
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            names.append(value.strip())
        elif isinstance(value, list):
            names.extend(str(item).strip() for item in value if isinstance(item, str) and item.strip())
    return list(dict.fromkeys(names))


def _structured_node_identity(
    profile: dict[str, Any],
    node: dict[str, Any],
) -> dict[str, Any] | None:
    """Require the individual JSON-LD Organization node to identify the target.

    Page-level exact identity is necessary but not sufficient because one page may contain
    several Organization nodes such as parent, publisher, or vendor. A node is accepted
    only when an explicit structured identity field carries the exact target org number,
    or when no conflicting structured org number is present and a node name contains all
    normalized legal-name tokens.

    Any explicit different nine-digit identity vetoes name-based acceptance.
    """

    target_org = str(profile.get("organisation_number") or "")
    if len(target_org) != 9 or not target_org.isdigit():
        return None

    observed_orgs = _structured_identity_numbers(node)
    if observed_orgs:
        if target_org in observed_orgs:
            return {
                "method": "structured_exact_organisation_number",
                "observed_organisation_numbers": sorted(observed_orgs),
                "matched_name": None,
            }
        return None

    target_tokens = set(_tokens(profile.get("name")))
    if not target_tokens:
        return None

    for name in _structured_names(node):
        node_tokens = set(_tokens(name))
        if target_tokens.issubset(node_tokens):
            return {
                "method": "structured_legal_name_token_match",
                "observed_organisation_numbers": [],
                "matched_name": name[:200],
            }
    return None


def _structured_email_values(value: Any, *, email_field: bool = False) -> set[str]:
    """Extract emails only from schema fields explicitly named email.

    Nested ContactPoint.email values are allowed; free-text JSON-LD values are not scanned.
    """

    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.update(
                _structured_email_values(
                    child,
                    email_field=email_field or str(key).casefold() == "email",
                )
            )
    elif isinstance(value, list):
        for child in value:
            found.update(_structured_email_values(child, email_field=email_field))
    elif email_field and isinstance(value, str):
        for match in EMAIL_RE.finditer(value):
            found.add(match.group(1).strip().lower())
    return found


def _structured_target_emails(
    profile: dict[str, Any],
    website_value: dict[str, Any],
    source_url: str,
) -> dict[str, dict[str, Any]]:
    """Return exact-node, same-domain JSON-LD contact candidates keyed by email."""

    candidates: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(website_value.get("structured_organisations") or []):
        if not isinstance(node, dict):
            continue
        node_identity = _structured_node_identity(profile, node)
        if node_identity is None:
            continue
        for email in sorted(_structured_email_values(node)):
            if not _safe_same_domain_email(email, source_url):
                continue
            candidates.setdefault(
                email,
                {
                    "strategy": "verified_company_jsonld_same_domain_email_v1",
                    "node_index": index,
                    "node_identity": node_identity,
                },
            )
    return candidates


def company_site_contact_email_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract narrow first-party email claims from an already-qualified company page.

    H2c performs no network access. Existing behavior inspects the bounded
    identity/footer/contact text retained from the exact company website snapshot.

    The zero-request structured recovery additionally accepts schema.org Organization email
    fields only when the individual structured node itself identifies the target legal
    entity by exact org number, or by target legal-name tokens without a conflicting
    structured org number. In every path the email domain must match the verified website
    registered domain. Cross-domain and ambiguous structured contacts abstain.
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
    if not source_url.startswith(("http://", "https://")) or not retrieved_at or len(content_sha256) != 64:
        return []

    candidates: dict[str, dict[str, Any]] = {}

    # Preserve the existing H2c footer/contact/legal-text path exactly and give it
    # precedence when the same email is also declared in JSON-LD.
    identity_text = str(value.get("identity_text_excerpt") or "")
    if identity_text.strip():
        for match in EMAIL_RE.finditer(identity_text):
            email = match.group(1).strip().lower()
            if not _safe_same_domain_email(email, source_url):
                continue
            candidates[email] = {
                "strategy": "verified_company_page_same_domain_email_v1",
                "node_index": None,
                "node_identity": None,
            }

    for email, metadata in _structured_target_emails(profile, value, source_url).items():
        candidates.setdefault(email, metadata)

    observations: list[dict[str, Any]] = []
    for email in sorted(candidates)[:MAX_CONTACT_EMAILS]:
        metadata = candidates[email]
        strategy = str(metadata["strategy"])
        observation_id = "company-site-email-" + hashlib.sha256(
            f"{org}|{email}|{source_url}|{content_sha256}".encode("utf-8")
        ).hexdigest()[:24]

        proof: list[dict[str, Any]] = [
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
        ]
        if strategy == "verified_company_jsonld_same_domain_email_v1":
            node_identity = dict(metadata.get("node_identity") or {})
            proof.append(
                {
                    "type": "structured_organization_identity_gate",
                    "node_index": metadata.get("node_index"),
                    "method": node_identity.get("method"),
                    "observed_organisation_numbers": list(
                        node_identity.get("observed_organisation_numbers") or []
                    ),
                    "matched_name": node_identity.get("matched_name"),
                }
            )
            proof.append(
                {
                    "type": "structured_organization_email_field",
                    "source_url": source_url,
                    "content_sha256": content_sha256,
                }
            )
            evidence_span = (
                f"Exact company homepage schema.org Organization node publishes contact email {email}"
            )
            claim_scope = (
                "Contact email explicitly present in an already-retained schema.org Organization email "
                "field on the exact company website; the individual structured node matches the target "
                "legal entity and the email domain matches the verified website registered domain."
            )
        else:
            proof.append(
                {
                    "type": "bounded_identity_footer_excerpt",
                    "source_url": source_url,
                    "content_sha256": content_sha256,
                }
            )
            evidence_span = f"Verified company page publishes contact email {email}"
            claim_scope = (
                "Contact email explicitly present in bounded footer/contact/legal text on the exact "
                "company website; email domain matches the verified website registered domain."
            )

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
                "identity_proof": proof,
                "acquisition_mode": "permitted_public_page",
                "rights_status": "approved",
                "source_class": "company_site",
                "evidence_span": evidence_span,
                "contact_email": email,
                "metrics": {
                    "identity_score": identity.get("score"),
                    "claim_scope": claim_scope,
                    "network_requests_added": 0,
                },
                "strategy": strategy,
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
