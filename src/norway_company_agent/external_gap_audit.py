from __future__ import annotations

from collections import defaultdict
from typing import Any


TRACKED_FIELDS = (
    "official_website",
    "external.profile_handle",
    "social_links",
    "external.contact_email",
    "external.careers_page",
    "external.job_posting",
    "external.company_update",
    "external.workforce_snapshot",
    "official.support_award",
)


def _percentage(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(100.0 * numerator / denominator, 1)


def _available_claims_by_field(contracts: list[dict[str, Any]]) -> dict[str, set[str]]:
    companies: dict[str, set[str]] = defaultdict(set)
    for contract in contracts:
        org = str(contract.get("organisation_number") or "")
        if not org:
            continue
        for claim in contract.get("claims") or []:
            if not isinstance(claim, dict) or claim.get("availability") != "available":
                continue
            field = str(claim.get("field") or "")
            if field:
                companies[field].add(org)
    return companies


def _verified_site(profile: dict[str, Any]) -> bool:
    website = ((profile.get("evidence") or {}).get("website") or {})
    assessment = ((website.get("value") or {}).get("identity_assessment") or {})
    return bool(website.get("status") == "available" and assessment.get("publishable"))


def _surface_flags(profile: dict[str, Any]) -> dict[str, bool]:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    hiring = value.get("active_hiring_signal") or {}
    return {
        "careers_links": bool(value.get("careers_links")),
        "news_detail_links": bool(value.get("news_detail_links")),
        "active_hiring": bool(hiring.get("active_vacancies")),
        "job_listing_candidates": bool(value.get("job_listing_candidates")),
    }


def audit_external_gap_coverage(
    contracts: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
    *,
    run_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Measure evaluator-visible external coverage and conditional first-party yield.

    The audit is deliberately read-only. It does not infer missing facts or treat a missing
    external signal as a negative company fact. Its purpose is to separate collector/
    projection weaknesses from upstream source-reach bottlenecks before new qualification
    work is attempted.
    """

    contract_orgs = [str(row.get("organisation_number") or "") for row in contracts]
    profile_orgs = [str(row.get("organisation_number") or "") for row in profiles]
    contract_set = {org for org in contract_orgs if org}
    profile_set = {org for org in profile_orgs if org}
    available = _available_claims_by_field(contracts)

    verified_profiles = [profile for profile in profiles if _verified_site(profile)]
    verified_site_orgs = {
        str(profile.get("organisation_number") or "") for profile in verified_profiles
    }
    verified_site_orgs.discard("")

    field_coverage: dict[str, Any] = {}
    total = len(contract_set)
    for field in TRACKED_FIELDS:
        companies = available.get(field, set())
        field_coverage[field] = {
            "companies": len(companies),
            "total_companies": total,
            "company_coverage_pct": _percentage(len(companies), total),
        }

    site_count = len(verified_site_orgs)
    handles_on_sites = len(verified_site_orgs & available.get("external.profile_handle", set()))
    contact_on_sites = len(verified_site_orgs & available.get("external.contact_email", set()))

    surface_counts = {
        "careers_links": 0,
        "news_detail_links": 0,
        "active_hiring": 0,
        "job_listing_candidates": 0,
    }
    for profile in verified_profiles:
        flags = _surface_flags(profile)
        for key, present in flags.items():
            surface_counts[key] += int(present)

    conditional = {
        "verified_site_companies": site_count,
        "profile_handle": {
            "companies": handles_on_sites,
            "denominator_verified_sites": site_count,
            "conditional_yield_pct": _percentage(handles_on_sites, site_count),
        },
        "contact_email": {
            "companies": contact_on_sites,
            "denominator_verified_sites": site_count,
            "conditional_yield_pct": _percentage(contact_on_sites, site_count),
        },
        "homepage_surfaces": {
            key: {
                "companies": count,
                "denominator_verified_sites": site_count,
                "conditional_yield_pct": _percentage(count, site_count),
            }
            for key, count in surface_counts.items()
        },
    }

    decisions = {
        "q4_social": {
            "status": (
                "source_reach_bottleneck"
                if site_count < total and handles_on_sites > 0
                else "extractor_or_source_gap"
            ),
            "reason": (
                "Profile-handle extraction already succeeds on verified sites; company-level "
                "coverage is bounded primarily by verified-site reach."
                if site_count < total and handles_on_sites > 0
                else "No positive conditional signal is available to separate source reach from extraction."
            ),
        },
        "q4_contact": {
            "status": (
                "source_reach_bottleneck"
                if site_count < total and contact_on_sites == site_count and site_count > 0
                else "extractor_or_source_gap"
            ),
            "reason": (
                "Contact-email extraction is complete on the verified-site sample; company-level "
                "coverage is bounded by verified-site reach."
                if site_count < total and contact_on_sites == site_count and site_count > 0
                else "Conditional contact-email extraction is not complete on the verified-site sample."
            ),
        },
        "q5_hiring": {
            "status": (
                "no_surface_in_verified_site_sample"
                if not surface_counts["careers_links"]
                and not surface_counts["active_hiring"]
                and not surface_counts["job_listing_candidates"]
                else "measured_surface_available"
            ),
            "reason": (
                "No verified homepage in the consumed sample exposes a careers link, active-hiring "
                "marker, or job-listing candidate. Unchanged first-party hiring extraction has no measured transfer surface."
                if not surface_counts["careers_links"]
                and not surface_counts["active_hiring"]
                and not surface_counts["job_listing_candidates"]
                else "At least one verified site exposes a hiring surface worth separate measurement."
            ),
        },
        "q6_activity": {
            "status": (
                "no_surface_in_verified_site_sample"
                if not surface_counts["news_detail_links"]
                else "measured_surface_available"
            ),
            "reason": (
                "No verified homepage in the consumed sample exposes a dated-news/detail nomination. "
                "Unchanged first-party activity extraction has no measured transfer surface."
                if not surface_counts["news_detail_links"]
                else "At least one verified site exposes a news/detail surface worth separate measurement."
            ),
        },
    }

    request_context: dict[str, Any] | None = None
    if run_report is not None:
        budget = run_report.get("request_budget") or {}
        site = run_report.get("site_discovery") or {}
        observed_charge = int(budget.get("observed_conservative_challenge_request_charge") or 0)
        max_charge = int(budget.get("max_challenge_requests") or 0)
        theoretical_charge = int(budget.get("theoretical_challenge_request_charge_ceiling") or 0)
        request_context = {
            "observed_logical_requests": int(budget.get("observed_logical_requests") or 0),
            "observed_conservative_challenge_request_charge": observed_charge,
            "max_challenge_requests": max_charge,
            "observed_unused_challenge_charge": max(0, max_charge - observed_charge),
            "theoretical_challenge_request_charge_ceiling": theoretical_charge,
            "structural_headroom_available": bool(max_charge and theoretical_charge < max_charge),
            "selected_site_sources": dict(site.get("selected_sources") or {}),
            "h1g_attempted": int(((site.get("h1g") or {}).get("attempted") or 0)),
            "h1g_verified": int(((site.get("h1g") or {}).get("verified") or 0)),
            "wikidata_candidate_count": int(((site.get("wikidata") or {}).get("candidate_count") or 0)),
        }

    return {
        "total_contract_companies": len(contract_set),
        "total_profile_companies": len(profile_set),
        "organisation_sets_match": contract_set == profile_set,
        "duplicate_contract_organisation_numbers": len(contract_orgs) - len(contract_set),
        "duplicate_profile_organisation_numbers": len(profile_orgs) - len(profile_set),
        "field_coverage": field_coverage,
        "conditional_on_verified_site": conditional,
        "decisions": decisions,
        "request_context": request_context,
        "policy": (
            "Read-only consumed/dev coverage audit. Missing signals remain unknown/unavailable; "
            "the audit never fabricates negative company facts or weakens identity publication rules."
        ),
    }
