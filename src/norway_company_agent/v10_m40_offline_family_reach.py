"""M40 read-only, external-family evidence gap screen; NO collection and NO score claim.

Uses only ALREADY-CONSUMED exact-org contract claims and provenance-valid
observations. Typed facts are never relabelled to improve the proxy:
  - government grants are not public buzz or company-authored updates;
  - workforce snapshots are not individual job postings;
  - first-party profile handles are not engagement or account metrics;
  - missing sentiments are not neutral sentiments;
  - URLs/names/registries are not independent customer reviews.

Output contains fixed aggregate counts only, never companies, profiles or URLs.
This is NOT the Builderr official score or weighted recall denominator.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from typing import Any

from .external_footprint import publishable_observation

FAMILY_CLAIM_FIELDS = {
    "verified_company_site":frozenset({"official_website"}),
    "verified_social_handle":frozenset({"external.profile_handle"}),
    "first_party_contact_email":frozenset({"external.contact_email"}),
    "workforce_snapshot":frozenset({"external.workforce_snapshot"}),
    "official_support_award":frozenset({"official.support_award"}),
    "concrete_job_posting":frozenset({"external.job_posting"}),
    "company_careers_link":frozenset({"external.careers_page"}),
    "first_party_company_update":frozenset({"external.company_update"}),
    "independent_reviews_or_places":frozenset({
        "external.review","external.review_summary","external.place_summary",
    }),
    "independent_public_buzz_or_metrics":frozenset({
        "external.public_post","external.public_mention",
        "external.profile_metrics","external.buzz_metrics",
    }),
}
INDEPENDENT_SENTIMENT_OBSERVATION_TYPES=frozenset({
    "review","public_mention",
})
PLATFORM_ALLOWED=frozenset({
    "linkedin","facebook","instagram","youtube","x","tiktok",
    "glassdoor","indeed","google_places","openstreetmap",
    "google_play","apple_app_store","news",
})


def _valid_org(value:Any)->bool:
    return isinstance(value,str) and len(value)==9 and value.isascii() and value.isdecimal()


def score_evidence_family_reach(
    contracts:list[dict[str,Any]],profiles:list[dict[str,Any]],
)->dict[str,Any]:
    """Report actual available source claim coverage, NOT hypothetical gains.

    Input is frozen evaluator-shaped contracts and retained profiles. Strictly
    reject duplicate/mismatched org sets so denominators never silently drift.
    """
    if not isinstance(contracts,list) or not isinstance(profiles,list) or not contracts:
        raise ValueError("Need already-consumed profile and contract collections")
    if len(contracts)>300:
        raise ValueError("Development screen <=300 only")
    claim_ids=[r.get("organisation_number") if isinstance(r,dict) else None for r in contracts]
    profile_ids=[r.get("organisation_number") if isinstance(r,dict) else None for r in profiles]
    if not all(_valid_org(x) for x in claim_ids+profile_ids):
        raise ValueError("All company organisation numbers must be exact 9-digit strings")
    if len(set(claim_ids))!=len(claim_ids) or len(set(profile_ids))!=len(profile_ids):
        raise ValueError("Duplicate company IDs cannot inflate reach")
    if set(claim_ids)!=set(profile_ids) or len(contracts)!=len(profiles):
        raise ValueError("Mismatched existing profile and contract sets")

    n=len(contracts)
    family_orgs={key:set() for key in FAMILY_CLAIM_FIELDS}
    sentiment_orgs=set()
    two_platform_orgs=set()
    validated_external_orgs=set()
    all_claim_orgs=defaultdict(set)
    for item in contracts:
        org=item["organisation_number"]
        platform_claims=set()
        claims=item.get("claims") or []
        if not isinstance(claims,list):
            raise ValueError("Malformed output-contract claims")
        for claim in claims:
            if not isinstance(claim,dict):
                raise ValueError("Malformed claim")
            if claim.get("availability")!="available":
                continue  # unavailable/unknown never becomes false or an observation
            field=claim.get("field")
            if not isinstance(field,str) or not field.strip():
                raise ValueError("Available claim missing typed field")
            if not claim.get("evidence_ids"):
                raise ValueError("Available claim lacks evidence ID references")
            all_claim_orgs[field].add(org)
            for category,fields in FAMILY_CLAIM_FIELDS.items():
                if field in fields:
                    family_orgs[category].add(org)
            if field=="external.profile_handle":
                platform=claim.get("platform")
                if platform in PLATFORM_ALLOWED:
                    platform_claims.add(platform)
        if len(platform_claims)>=2:
            two_platform_orgs.add(org)

    for profile in profiles:
        org=profile["organisation_number"]
        observations=profile.get("external_observations") or []
        if not isinstance(observations,list):
            raise ValueError("Malformed external observations")
        for item in observations:
            if not isinstance(item,dict):
                raise ValueError("Malformed external observation")
            if str(item.get("organisation_number") or "")!=org:
                raise ValueError("Cross-company external observation")
            if not publishable_observation(item):
                continue
            validated_external_orgs.add(org)
            signal=item.get("signal_type")
            if signal in {"review","review_summary","place_summary"}:
                family_orgs["independent_reviews_or_places"].add(org)
            if signal in {"public_post","public_mention","buzz_metrics","profile_metrics"}:
                family_orgs["independent_public_buzz_or_metrics"].add(org)
            # A sentiment score demands stricter separate multisource tests;
            # count only actually labeled admissible independent observations.
            if item.get("sentiment_label") is not None and signal in INDEPENDENT_SENTIMENT_OBSERVATION_TYPES:
                sentiment_orgs.add(org)

    observed={key:len(family_orgs[key]) for key in FAMILY_CLAIM_FIELDS}
    observed["labeled_independent_sentiment_input"]=len(sentiment_orgs)
    observed["two_verified_external_profile_platforms"]=len(two_platform_orgs)
    assert all(0<=count<=n for count in observed.values())
    # Positive mapped families are mutually NONexclusive, never a total score.
    return {
        "schema":"m40_consumed_exact_family_reach_v1",
        "source":"PREVIOUSLY_CONSUMED_SHA_PINNED_ARCHIVES_ONLY",
        "companies":n,
        "company_counts_by_typed_family":dict(sorted(observed.items())),
        "companies_with_publishable_external_observations":len(validated_external_orgs),
        "published_site_claims_added":0,
        "new_verified_coverage":0,
        "official_builderr_recall_measured":False,
        "official_builderr_score_measured":False,
        "new_company_http_requests":0,
        "new_provider_requests":0,
        "third_party_usd_spent":0,
        "production_modified":False,
    }
