"""M39 OFFLINE-ONLY inventory of EXISTING Norwegian company-site discovery inputs.

This inventory answers a narrow question before another live search: which
candidate signals are actually present in the previously consumed profile
snapshots, and which were already covered by V8's registry/email/H1c logic?

Output is aggregated BOOLEAN/INTEGER COUNTS ONLY: never org numbers, company
names, website URLs, email domains, email addresses, or provider source data.

Important: potential candidate != company site. NO network, NO production hook,
NO publication. All positive sites still require independent first-party
exact-entity verification, including correct Norwegian organisation number.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from .domain_discovery import registry_email_addresses, registry_email_domain_candidates
from .zero_cost_discovery import deterministic_domain_candidates

FIELDS = (
    "verified_existing_site",
    "profile_site_seed_present",
    "bulk_registry_site_field_present",
    "live_registry_site_field_present",
    "registry_site_evidence_missing_from_profile",
    "no_registry_site_signal_anywhere",
    "registry_email_present",
    "registry_email_generic_or_rejected",
    "registry_email_company_domain_candidate",
    "registry_multiple_company_email_domains",
    "legal_name_compact_guess_available",
    "legal_name_hyphenated_guess_available",
    "h1a_email_discovery_record_present",
    "h1a_email_discovery_record_absent",
    "existing_website_evidence_available_unverified",
    "existing_website_evidence_nonavailable",
    "verified_site_social_link_recovery_eligible",
    "no_new_registered_source_url_signal",
)


def _valid_org(profile: dict[str, Any]) -> bool:
    org=profile.get("organisation_number")
    return isinstance(org,str) and len(org)==9 and org.isascii() and org.isdecimal()


def _evidence_value(evidence: dict[str, Any], name: str) -> dict[str, Any]:
    row=evidence.get(name)
    if not isinstance(row,dict):
        return {}
    value=row.get("value")
    return value if isinstance(value,dict) else {}


def inspect_existing_profile_signals(profile: dict[str, Any]) -> dict[str, bool]:
    """Return fixed boolean flags; NEVER any candidate string or identity."""
    if not isinstance(profile,dict) or not _valid_org(profile):
        raise ValueError("Expected existing exact nine-digit Norwegian company profile")
    if not str(profile.get("name") or "").strip():
        raise ValueError("Profile lacks legal name")
    if not str(profile.get("municipality") or "").strip():
        raise ValueError("Profile lacks municipality")
    evidence=profile.get("evidence",{})
    if evidence is None:
        evidence={}
    if not isinstance(evidence,dict):
        raise ValueError("Malformed evidence structure")
    if any(key in evidence and not isinstance(evidence[key],dict)
           for key in ("registry","registry_live","website","website_email_discovery")):
        raise ValueError("Malformed source evidence record")
    if ("registry" in evidence and evidence["registry"].get("value") is not None
        and not isinstance(evidence["registry"].get("value"),dict)):
        raise ValueError("Malformed BRREG registry value")

    root=str(profile.get("website") or "").strip()
    bulk=_evidence_value(evidence,"registry")
    live=_evidence_value(evidence,"registry_live")
    bulk_site=str(bulk.get("hjemmeside") or "").strip()
    live_site=str(live.get("website") or "").strip()
    website_record=evidence.get("website") or {}
    if not isinstance(website_record,dict):
        website_record={}
    website_value=website_record.get("value") or {}
    if not isinstance(website_value,dict):
        website_value={}
    assessment=website_value.get("identity_assessment") or {}
    if not isinstance(assessment,dict):
        assessment={}
    verified=(
        website_record.get("status")=="available"
        and assessment.get("publishable") is True
    )

    addresses=registry_email_addresses(profile)
    email_plan=registry_email_domain_candidates(profile)
    email_candidates=email_plan.get("candidates") or []
    eligible_email=bool(email_plan.get("eligible") and email_candidates)
    if not isinstance(email_candidates,list):
        raise ValueError("Unexpected registry email candidate type")
    name_plan=deterministic_domain_candidates(profile,max_candidates=2)
    name_candidates=name_plan.get("candidates") or []
    strategies={str(x.get("strategy") or "") for x in name_candidates if isinstance(x,dict)}
    email_attempt_row=evidence.get("website_email_discovery")
    email_attempt_recorded=isinstance(email_attempt_row,dict)
    root_evidence_signal=bool(root or bulk_site or live_site)
    flags={
        "verified_existing_site":verified,
        "profile_site_seed_present":bool(root),
        "bulk_registry_site_field_present":bool(bulk_site),
        "live_registry_site_field_present":bool(live_site),
        "registry_site_evidence_missing_from_profile":bool((bulk_site or live_site) and not root),
        "no_registry_site_signal_anywhere":not root_evidence_signal,
        "registry_email_present":bool(addresses),
        "registry_email_generic_or_rejected":bool(addresses and not eligible_email),
        "registry_email_company_domain_candidate":eligible_email,
        "registry_multiple_company_email_domains":len(email_candidates)>1,
        "legal_name_compact_guess_available":"legal_name_compact" in strategies,
        "legal_name_hyphenated_guess_available":"legal_name_hyphenated" in strategies,
        "h1a_email_discovery_record_present":email_attempt_recorded,
        "h1a_email_discovery_record_absent":not email_attempt_recorded,
        "existing_website_evidence_available_unverified":bool(
            website_record.get("status")=="available" and not verified
        ),
        "existing_website_evidence_nonavailable":bool(
            website_record and website_record.get("status")!="available"
        ),
        # Already-owned page data is interesting only for existing verified
        # websites. Social links and registry email by themselves never prove
        # ownership for missing websites.
        "verified_site_social_link_recovery_eligible":bool(
            verified and (
                website_value.get("social_links")
                or website_value.get("structured_organisations")
            )
        ),
        "no_new_registered_source_url_signal":not (bulk_site or live_site or eligible_email),
    }
    assert set(flags)==set(FIELDS)
    assert all(type(value)==bool for value in flags.values())
    return flags


def aggregate_existing_signals(
    profiles: list[dict[str, Any]], *,
    allow_missing_identity_fields: bool = False,
) -> dict[str, Any]:
    """Fixed-schema privacy-minimal cross-profile summary; no provider calls.

    Only the 300-company baseline may include legally incomplete profiles:
    count them explicitly as ineligible, never silently promote or substitute.
    The targeted frozen 20 must have complete registry identity.
    """
    if not isinstance(profiles,list) or not profiles:
        raise ValueError("Nonempty consumed profile cohort required")
    if len(profiles)>300:
        raise ValueError("Offline development batch limited to 300 profiles")
    ids=[p.get("organisation_number") if isinstance(p,dict) else None for p in profiles]
    if len(ids)!=len(set(ids)):
        raise ValueError("Profiles must have unique organisation numbers")
    counters=Counter()
    missing_identity=0
    for profile in profiles:
        if (
            isinstance(profile,dict) and _valid_org(profile)
            and (not str(profile.get("name") or "").strip()
                 or not str(profile.get("municipality") or "").strip())
        ):
            if not allow_missing_identity_fields:
                raise ValueError("Frozen cohort has incomplete registry identity")
            missing_identity+=1
            continue
        signals=inspect_existing_profile_signals(profile)
        counters.update(key for key,value in signals.items() if value)
    return {
        "schema":"m39_offline_existing_source_inventory_v1",
        "type":"PREVIOUSLY_CONSUMED_PROFILES_ONLY",
        "profiles_inspected":len(profiles),
        "profiles_with_complete_registry_identity":len(profiles)-missing_identity,
        "profiles_ineligible_missing_registry_identity":missing_identity,
        "non_exclusive_company_flags":{key:counters[key] for key in FIELDS},
        "company_ownership_inferred":False,
        "independent_site_fetch_performed":False,
        "verified_new_websites":0,
        "published_claims":0,
        "additional_external_http_requests":0,
        "provider_credits_used":0,
        "production_modified":False,
    }
