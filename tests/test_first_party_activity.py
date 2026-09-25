from __future__ import annotations

from copy import deepcopy

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection
from norway_company_agent.first_party_activity import (
    extract_strict_first_party_facts,
    project_first_party_activity_claims,
)
from norway_company_agent.output_contract import validate_contract_object


def _profile(*pages: dict, publishable: bool = True) -> dict:
    return {
        "organisation_number": "123456789",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no/",
                "retrieved_at": "2026-09-25T10:00:00Z",
                "value": {
                    "final_url": "https://example.no/",
                    "identity_assessment": {"publishable": publishable},
                    "pages": list(pages),
                },
            }
        },
    }


def _page(url: str, title: str, text: str, digest: str = "abc123") -> dict:
    return {
        "url": url,
        "title": title,
        "main_text_excerpt": text,
        "identity_text_excerpt": "",
        "content_sha256": digest,
    }


def _contract() -> dict:
    return {
        "organisation_number": "123456789",
        "run": {
            "run_id": "test-v2",
            "started_at": "2026-09-25T10:00:00Z",
            "completed_at": "2026-09-25T10:00:01Z",
            "terminal_status": "completed",
        },
        "claims": [],
        "evidence": [],
        "changes": [],
        "errors": [],
        "operations": {"requests": 0, "runtime_ms": 1000, "third_party_cost_usd": 0.0},
    }


def test_unverified_website_never_publishes_activity() -> None:
    profile = _profile(
        _page(
            "https://example.no/jobs/software-engineer",
            "Software Engineer | Example AS",
            "Full-time position. Apply now.",
        ),
        publishable=False,
    )
    assert extract_strict_first_party_facts(profile) == {"jobs": [], "updates": []}


def test_generic_careers_page_is_not_a_hiring_fact_even_with_apply_copy() -> None:
    profile = _profile(
        _page(
            "https://example.no/careers",
            "Careers — Example AS",
            "See our full-time opportunities. Apply now to join the team.",
        ),
        _page(
            "https://example.no/careers/",
            "Join our team | Example AS",
            "Full-time positions in Oslo. Apply now.",
            "generic-rich",
        ),
    )
    assert extract_strict_first_party_facts(profile)["jobs"] == []


def test_specific_role_page_requires_explicit_apply_action_and_job_detail() -> None:
    accepted = _profile(
        _page(
            "https://example.no/jobs/software-engineer",
            "Software Engineer | Example AS",
            "Full-time position in Oslo. Apply now before the application deadline.",
        )
    )
    rejected = _profile(
        _page(
            "https://example.no/jobs/software-engineer",
            "Software Engineer | Example AS",
            "Meet our software engineering team in Oslo.",
        )
    )
    jobs = extract_strict_first_party_facts(accepted)["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Software Engineer | Example AS"
    assert extract_strict_first_party_facts(rejected)["jobs"] == []


def test_explicit_job_id_query_can_identify_a_detail_page() -> None:
    profile = _profile(
        _page(
            "https://example.no/jobs?jobid=42",
            "Senior Platform Engineer | Example AS",
            "Full-time position in Oslo. Apply now.",
        )
    )
    jobs = extract_strict_first_party_facts(profile)["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["url"].endswith("jobid=42")


def test_generic_filter_query_does_not_turn_job_index_into_detail() -> None:
    profile = _profile(
        _page(
            "https://example.no/jobs?department=engineering",
            "Engineering opportunities | Example AS",
            "Full-time positions. Apply now.",
        )
    )
    assert extract_strict_first_party_facts(profile)["jobs"] == []


def test_cross_domain_role_page_is_rejected() -> None:
    profile = _profile(
        _page(
            "https://jobs.example-evil.no/jobs/software-engineer",
            "Software Engineer | Example AS",
            "Full-time position. Apply now.",
        )
    )
    assert extract_strict_first_party_facts(profile)["jobs"] == []


def test_dated_specific_update_is_published_but_indexes_and_undated_pages_are_not() -> None:
    profile = _profile(
        _page(
            "https://example.no/news/new-factory",
            "Example opens new factory",
            "Published 2026-09-20. The new facility opened this week.",
            "news1",
        ),
        _page(
            "https://example.no/news",
            "News | Example AS",
            "Latest stories 2026-09-20.",
            "news2",
        ),
        _page(
            "https://example.no/news/",
            "Latest company news | Example AS",
            "Stories updated 2026-09-20.",
            "news-index-rich",
        ),
        _page(
            "https://example.no/news/new-contract",
            "Example wins new contract",
            "A new customer agreement was announced.",
            "news3",
        ),
    )
    updates = extract_strict_first_party_facts(profile)["updates"]
    assert len(updates) == 1
    assert updates[0]["title"] == "Example opens new factory"
    assert updates[0]["published_date"] == "2026-09-20"


def test_projection_is_idempotent_and_contract_evidence_complete() -> None:
    profile = _profile(
        _page(
            "https://example.no/jobs/software-engineer",
            "Software Engineer | Example AS",
            "Full-time position in Oslo. Apply now.",
            "jobhash",
        ),
        _page(
            "https://example.no/news/new-factory",
            "Example opens new factory",
            "Published 25.09.2026. Expansion is complete.",
            "newshash",
        ),
    )
    once = project_first_party_activity_claims(_contract(), profile)
    twice = project_first_party_activity_claims(deepcopy(once), profile)

    assert once == twice
    assert validate_contract_object(twice) == []

    fields = [claim["field"] for claim in twice["claims"]]
    assert fields.count("external.job_posting") == 1
    assert fields.count("external.company_update") == 1

    canonical = project_canonical_profile(twice)
    assert validate_canonical_projection(canonical) == []
    fact_types = [fact["type"] for fact in canonical["canonical_facts"]]
    assert fact_types.count("job_posting") == 1
    assert fact_types.count("company_update") == 1
    assert canonical["canonical_profile"]["data_areas"]["hiring_and_public_activity"] is True
