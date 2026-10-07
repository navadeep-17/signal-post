from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any

from .domain_discovery import (
    GENERIC_EMAIL_DOMAINS,
    _domain_identity_strength,
    distinctive_legal_name_tokens,
)
from .website import _registered_domain, normalize_homepage


METHOD = "registry_domain_email_homepage_name_composite_v1"


def _email_domain(value: Any) -> str:
    text = str(value or "").strip().casefold()
    if "@" not in text:
        return ""
    local, domain = text.rsplit("@", 1)
    if not local or not domain:
        return ""
    normalized = normalize_homepage(domain)
    if not normalized:
        return ""
    return _registered_domain(normalized).casefold().rstrip(".")


def _site_domain(value: Any) -> str:
    normalized = normalize_homepage(str(value or "").strip())
    if not normalized:
        return ""
    return _registered_domain(normalized).casefold().rstrip(".")


def _substantive_tokens(profile: dict[str, Any]) -> list[str]:
    # Two-character initials/marks such as "NP" or "RÅ" are weak identity evidence.
    # They may remain in the original assessment, but this composite rule requires every
    # longer legal-name token to be independently observed on the fetched homepage.
    return [
        token
        for token in distinctive_legal_name_tokens(profile.get("name"))
        if len(token) >= 3
    ]


def assess_registry_domain_composite_identity(profile: dict[str, Any]) -> dict[str, Any] | None:
    """Recover a narrowly-scoped exact website identity from retained evidence only.

    Required independent signals:
      1) exact-org BRREG live entity declares a website;
      2) exact-org BRREG live entity declares an email on the same registered domain;
      3) the fetched final site resolves to that exact registered domain;
      4) all substantive legal-name tokens are already matched by the retained homepage
         identity assessment;
      5) the domain has at least partial legal-name compatibility; and
      6) there is no conflicting organisation-number or explicit site-owner evidence.

    This function performs no network access.
    """

    org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    if len(org) != 9:
        return None

    evidence = profile.get("evidence") or {}
    website = evidence.get("website") or {}
    registry_live = evidence.get("registry_live") or {}
    if (
        website.get("status") != "available"
        or website.get("source_type") != "registry_linked_company_website"
        or registry_live.get("status") != "available"
        or registry_live.get("source_type") != "official_registry_live"
    ):
        return None

    site_value = website.get("value") or {}
    prior = site_value.get("identity_assessment") or {}
    if prior.get("publishable"):
        return None

    registry_value = registry_live.get("value") or {}
    if re.sub(r"\D", "", str(registry_value.get("organisation_number") or "")) != org:
        return None

    final_url = str(site_value.get("final_url") or website.get("source_url") or "").strip()
    registry_website = str(registry_value.get("website") or "").strip()
    registry_email = str(registry_value.get("contact_email") or "").strip()

    final_domain = _site_domain(final_url)
    declared_domain = _site_domain(registry_website)
    email_domain = _email_domain(registry_email)
    if not final_domain or not declared_domain or not email_domain:
        return None
    if final_domain != declared_domain or final_domain != email_domain:
        return None
    if email_domain in GENERIC_EMAIL_DOMAINS:
        return None

    substantive = _substantive_tokens(profile)
    if not substantive:
        return None
    matched = {
        str(token).casefold()
        for token in (prior.get("matched_tokens") or [])
        if str(token).strip()
    }
    if not set(substantive).issubset(matched):
        return None

    strength = _domain_identity_strength(profile, final_domain)
    if strength not in {"exact", "multi", "acronym", "partial"}:
        return None

    observed_orgs = {
        re.sub(r"\D", "", str(value))
        for value in (prior.get("observed_organisation_numbers") or [])
        if re.sub(r"\D", "", str(value))
    }
    if any(value != org for value in observed_orgs):
        return None

    # Explicitly observed owner names are a high-risk conflict surface. This recovery is
    # intentionally limited to cases where the page did not name another legal owner.
    if prior.get("observed_site_owners"):
        return None

    registry_hash = str(registry_live.get("content_sha256") or "")
    website_hash = str(website.get("content_sha256") or site_value.get("content_sha256") or "")
    if len(registry_hash) != 64 or len(website_hash) != 64:
        return None

    return {
        "status": "exact",
        "score": 0.99,
        "publishable": True,
        "method": METHOD,
        "legal_name_tokens": list(distinctive_legal_name_tokens(profile.get("name"))),
        "substantive_legal_name_tokens": substantive,
        "matched_tokens": sorted(matched),
        "final_domain": final_domain,
        "registry_declared_domain": declared_domain,
        "registry_email_domain": email_domain,
        "registry_website": registry_website,
        "registry_email": registry_email,
        "observed_organisation_numbers": sorted(observed_orgs),
        "observed_site_owners": [],
        "reasons": [
            "exact-org BRREG live response declares this website domain",
            "exact-org BRREG live contact email uses the same registered domain",
            "independently fetched final website resolves to the same registered domain",
            "all substantive legal-name tokens are present in retained homepage identity evidence",
            f"domain/legal-name compatibility is {strength}",
            "no conflicting organisation-number or explicit site-owner evidence is retained",
        ],
    }


def _registry_evidence_id(org: str, registry_hash: str, final_domain: str) -> str:
    material = f"{org}|{registry_hash}|{final_domain}|{METHOD}"
    return "ev-registry-domain-composite-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def project_registry_domain_composite_website(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Upgrade only an existing ambiguous official_website claim when M19 passes.

    The original company-page evidence is retained (with its previous identity assessment
    nested for audit) and exact-org BRREG live evidence is added. No other claim family is
    created or rewritten.
    """

    assessment = assess_registry_domain_composite_identity(profile)
    if assessment is None:
        return contract

    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    if org != str(profile.get("organisation_number") or ""):
        return contract

    claims = [deepcopy(item) for item in (contract.get("claims") or []) if isinstance(item, dict)]
    evidence = [deepcopy(item) for item in (contract.get("evidence") or []) if isinstance(item, dict)]
    website_claims = [
        item
        for item in claims
        if item.get("field") == "official_website"
    ]
    if len(website_claims) != 1:
        return contract

    claim = website_claims[0]
    if claim.get("availability") != "ambiguous" or claim.get("value") is not None:
        return contract

    profile_website = (profile.get("evidence") or {}).get("website") or {}
    site_value = profile_website.get("value") or {}
    final_url = str(site_value.get("final_url") or profile_website.get("source_url") or "").strip()
    if not final_url.startswith(("http://", "https://")):
        return contract

    refs = [str(ref) for ref in (claim.get("evidence_ids") or []) if ref]
    if len(refs) != 1:
        return contract
    website_evidence_id = refs[0]
    website_evidence = next(
        (item for item in evidence if str(item.get("id") or "") == website_evidence_id),
        None,
    )
    if website_evidence is None:
        return contract
    if str(website_evidence.get("content_sha256") or "") != str(profile_website.get("content_sha256") or ""):
        return contract

    prior_identity = deepcopy(website_evidence.get("identity_proof"))
    website_evidence["prior_identity_proof"] = prior_identity
    website_evidence["identity_proof"] = deepcopy(assessment)
    website_evidence["extraction_method"] = METHOD
    website_evidence["claim_span"] = (
        f"Composite exact identity: final website {final_url}; "
        f"BRREG-declared domain {assessment['registry_declared_domain']}; "
        f"BRREG email domain {assessment['registry_email_domain']}; "
        f"substantive legal-name tokens {', '.join(assessment['substantive_legal_name_tokens'])}"
    )[:1000]

    registry_live = (profile.get("evidence") or {}).get("registry_live") or {}
    registry_hash = str(registry_live.get("content_sha256") or "")
    registry_id = _registry_evidence_id(org, registry_hash, str(assessment["final_domain"]))
    registry_evidence = {
        "id": registry_id,
        "source_url": registry_live.get("source_url"),
        "source_class": "official",
        "retrieved_at": registry_live.get("retrieved_at"),
        "content_sha256": registry_hash,
        "source_row_key": org,
        "source_field": "/hjemmeside + /epostadresse",
        "claim_span": (
            f'/hjemmeside="{assessment["registry_website"]}"; '
            f'/epostadresse="{assessment["registry_email"]}"'
        )[:1000],
        "extraction_method": METHOD,
    }
    if not any(str(item.get("id") or "") == registry_id for item in evidence):
        evidence.append(registry_evidence)

    claim.update(
        {
            "value": final_url,
            "availability": "available",
            "confidence": 0.99,
            "evidence_ids": [website_evidence_id, registry_id],
            "signal_type": "registry_domain_composite_identity_recovery",
            "claim_scope": (
                "Exact website identity recovered from agreement between the exact-org BRREG live "
                "website field, exact-org BRREG contact-email domain, fetched final-site domain and "
                "retained substantive legal-name evidence. No new network request is made."
            ),
        }
    )

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence, key=lambda item: str(item.get("id") or "")),
    }
