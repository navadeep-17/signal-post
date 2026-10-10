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
from .careers_contract import project_careers_page_claims

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

    # Measure existing first-party *source opportunity*, not publication.
    # Only already-verified webpages are eligible for these indicators.
    # Presence of a link/marker does not establish an active job or a
    # company-authored dated update, even if the URL looks persuasive.
    retained_surfaces=Counter()
    for profile in profiles:
        evidence=profile.get("evidence") or {}
        if not isinstance(evidence,dict):
            raise ValueError("Malformed profile evidence")
        website=evidence.get("website") or {}
        if not isinstance(website,dict):
            raise ValueError("Malformed retained website evidence")
        value=website.get("value") or {}
        if not isinstance(value,dict):
            raise ValueError("Malformed website content")
        assessment=value.get("identity_assessment") or {}
        if not isinstance(assessment,dict):
            raise ValueError("Malformed website identity")
        if website.get("status")!="available" or assessment.get("publishable") is not True:
            continue
        retained_surfaces["already_exact_verified_homepages"]+=1
        for flag,field in (
            ("retained_careers_links","careers_links"),
            ("retained_news_detail_links","news_detail_links"),
            ("retained_job_listing_candidates","job_listing_candidates"),
        ):
            if value.get(field):
                retained_surfaces[flag]+=1
        hiring=value.get("active_hiring_signal") or {}
        if isinstance(hiring,dict) and hiring.get("active_vacancies"):
            retained_surfaces["retained_active_hiring_marker"]+=1
    surface_names=(
        "already_exact_verified_homepages",
        "retained_careers_links",
        "retained_news_detail_links",
        "retained_job_listing_candidates",
        "retained_active_hiring_marker",
    )
    retained={name:retained_surfaces[name] for name in surface_names}
    assert all(0<=count<=n for count in retained.values())
    assert all(retained[name]<=retained["already_exact_verified_homepages"]
               for name in surface_names[1:])

    # A link appearing in retained HTML is not equivalent to an admissible
    # careers-page claim. Replay the EXISTING strict projection entirely
    # offline to distinguish lost projection from evidence-veto abstention.
    by_contract={row["organisation_number"]:row for row in contracts}
    replay_added_companies=0
    replay_net_new_companies=0
    replay_lost_companies=0
    surface_unclaimed_companies=0
    surface_ineligible_companies=0
    for profile in profiles:
        org=profile["organisation_number"]
        raw=(profile.get("evidence") or {}).get("website") or {}
        value=raw.get("value") or {}
        qualified=raw.get("status")=="available" and (
            (value.get("identity_assessment") or {}).get("publishable") is True
        )
        if not qualified or not value.get("careers_links"):
            continue
        original=by_contract[org]
        current={str(c.get("value",{}).get("url") or "") for c in original.get("claims",[])
                 if isinstance(c,dict) and c.get("field")=="external.careers_page"
                 and c.get("availability")=="available" and isinstance(c.get("value"),dict)}
        proposed=project_careers_page_claims(original,profile)
        generated={str(c.get("value",{}).get("url") or "") for c in proposed.get("claims",[])
                   if isinstance(c,dict) and c.get("field")=="external.careers_page"
                   and c.get("availability")=="available" and isinstance(c.get("value"),dict)}
        if not current:
            surface_unclaimed_companies+=1
        if not generated:
            surface_ineligible_companies+=1
        if generated-current:
            replay_added_companies+=1
        if generated and not current:
            replay_net_new_companies+=1
        if current-generated:
            replay_lost_companies+=1
    careers_replay={
        "exact_site_homepage_careers_link_companies":retained["retained_careers_links"],
        "homepage_careers_link_without_existing_claim":surface_unclaimed_companies,
        "homepage_careers_link_not_projection_eligible":surface_ineligible_companies,
        "strict_existing_careers_projector_new_claim_company_candidates":replay_added_companies,
        "strict_existing_careers_projector_net_new_company_coverage_candidates":replay_net_new_companies,
        "strict_existing_careers_projector_existing_claim_regression_candidates":replay_lost_companies,
        "additional_network_requests":0,
        "automatically_publishable_new_claims":0,
    }
    # Positive mapped families are mutually NONexclusive, never a total score.
    return {
        "schema":"m40_consumed_exact_family_reach_v1",
        "source":"PREVIOUSLY_CONSUMED_SHA_PINNED_ARCHIVES_ONLY",
        "companies":n,
        "company_counts_by_typed_family":dict(sorted(observed.items())),
        "companies_with_publishable_external_observations":len(validated_external_orgs),
        "pre_existing_exact_site_source_surfaces":retained,
        "existing_careers_projection_replay":careers_replay,
        "published_site_claims_added":0,
        "new_verified_coverage":0,
        "official_builderr_recall_measured":False,
        "official_builderr_score_measured":False,
        "new_company_http_requests":0,
        "new_provider_requests":0,
        "third_party_usd_spent":0,
        "production_modified":False,
    }
