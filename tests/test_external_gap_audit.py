from __future__ import annotations

from norway_company_agent.external_gap_audit import audit_external_gap_coverage


def _contract(org: str, fields: list[str]) -> dict:
    return {
        "organisation_number": org,
        "claims": [
            {
                "field": field,
                "availability": "available",
                "value": True,
                "evidence_ids": [f"ev-{org}-{index}"],
            }
            for index, field in enumerate(fields)
        ],
    }


def _profile(
    org: str,
    *,
    verified: bool = False,
    careers: bool = False,
    news: bool = False,
    hiring: bool = False,
    jobs: bool = False,
) -> dict:
    if not verified:
        return {"organisation_number": org, "evidence": {}}
    return {
        "organisation_number": org,
        "evidence": {
            "website": {
                "status": "available",
                "value": {
                    "identity_assessment": {"publishable": True},
                    "careers_links": [{"url": "https://example.no/jobs"}] if careers else [],
                    "news_detail_links": [{"url": "https://example.no/news/1"}] if news else [],
                    "active_hiring_signal": {"active_vacancies": hiring},
                    "job_listing_candidates": [{"title": "Engineer"}] if jobs else [],
                },
            }
        },
    }


def test_audit_separates_site_reach_from_conditional_extraction() -> None:
    contracts = [
        _contract("111111111", ["official_website", "external.profile_handle", "external.contact_email"]),
        _contract("222222222", ["official_website", "external.contact_email"]),
        _contract("333333333", ["external.workforce_snapshot"]),
        _contract("444444444", []),
    ]
    profiles = [
        _profile("111111111", verified=True),
        _profile("222222222", verified=True),
        _profile("333333333"),
        _profile("444444444"),
    ]

    report = audit_external_gap_coverage(contracts, profiles)

    assert report["field_coverage"]["official_website"]["companies"] == 2
    assert report["field_coverage"]["external.profile_handle"]["companies"] == 1
    assert report["conditional_on_verified_site"]["profile_handle"] == {
        "companies": 1,
        "denominator_verified_sites": 2,
        "conditional_yield_pct": 50.0,
    }
    assert report["conditional_on_verified_site"]["contact_email"]["conditional_yield_pct"] == 100.0
    assert report["decisions"]["q4_social"]["status"] == "source_reach_bottleneck"
    assert report["decisions"]["q4_contact"]["status"] == "source_reach_bottleneck"
    assert report["decisions"]["q5_hiring"]["status"] == "no_surface_in_verified_site_sample"
    assert report["decisions"]["q6_activity"]["status"] == "no_surface_in_verified_site_sample"


def test_hiring_and_activity_surface_detection_is_explicit() -> None:
    contracts = [_contract("111111111", ["official_website"])]
    profiles = [
        _profile(
            "111111111",
            verified=True,
            careers=True,
            news=True,
            hiring=True,
            jobs=True,
        )
    ]

    report = audit_external_gap_coverage(contracts, profiles)
    surfaces = report["conditional_on_verified_site"]["homepage_surfaces"]

    assert surfaces["careers_links"]["companies"] == 1
    assert surfaces["news_detail_links"]["companies"] == 1
    assert surfaces["active_hiring"]["companies"] == 1
    assert surfaces["job_listing_candidates"]["companies"] == 1
    assert report["decisions"]["q5_hiring"]["status"] == "measured_surface_available"
    assert report["decisions"]["q6_activity"]["status"] == "measured_surface_available"


def test_request_context_distinguishes_observed_headroom_from_structural_headroom() -> None:
    contracts = [_contract("111111111", [])]
    profiles = [_profile("111111111")]
    run_report = {
        "request_budget": {
            "observed_logical_requests": 682,
            "observed_conservative_challenge_request_charge": 1364,
            "max_challenge_requests": 2000,
            "theoretical_challenge_request_charge_ceiling": 2000,
        },
        "site_discovery": {
            "selected_sources": {"none": 94, "registry_website": 4, "h1c_deterministic_domain": 2},
            "h1g": {"attempted": 74, "verified": 0},
            "wikidata": {"candidate_count": 0},
        },
    }

    report = audit_external_gap_coverage(contracts, profiles, run_report=run_report)
    request = report["request_context"]

    assert request["observed_unused_challenge_charge"] == 636
    assert request["structural_headroom_available"] is False
    assert request["h1g_attempted"] == 74
    assert request["h1g_verified"] == 0
    assert request["wikidata_candidate_count"] == 0


def test_mismatched_org_sets_are_reported_not_hidden() -> None:
    report = audit_external_gap_coverage(
        [_contract("111111111", [])],
        [_profile("222222222")],
    )

    assert report["organisation_sets_match"] is False
