"""M23: synthetic provider output and independently fetched pages only (no HTTP)."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.tavily_offline_candidate import (
    ProviderPrerequisites,
    normalize_tavily_results,
    offline_screen,
    tavily_basic_search_body,
)

ORG = "123456789"
COMPANY = "EXAMPLE BEDRIFT AS"
URL = "https://examplebedrift.no/"


def profile(*, website="", holding=False):
    row = {
        "organisation_number": ORG, "name": COMPANY,
        "municipality": "OSLO", "website": website,
    }
    if holding:
        row["evidence"] = {
            "registry": {
                "value": {"vedtektsfestetFormaal": "Eie og forvalte aksjer"}
            }
        }
    return row


def payload(*, url=URL, title="Example Bedrift AS", content="Org nr 123 456 789 Oslo"):
    return {
        "query": "PROVIDER'S ORIGINAL QUERY NOT TRUSTED",
        "answer": "UNTRUSTED_LLM_ANSWER",
        "response_time": "1.5",
        "usage": {"credits": 1},
        "results": [{
            "url": url, "title": title, "content": content,
            "score": 0.999, "raw_content": "SECRET_RAW_PROVIDER_TEXT",
            "images": [{"url": "https://example.org/pixel"}],
        }],
    }


def site(*, url=URL, requested_url=URL,
         text="Velkommen til Example Bedrift AS. Organisasjonsnummer 123 456 789. Vårt kontor ligger i Oslo.",
         title=COMPANY, status="available"):
    return {
        "status": status, "source_url": url,
        "source_type": "synthetic_offline_first_party_fixture",
        "value": {
            "requested_url": requested_url, "final_url": url,
            "title": title, "description": "",
            "identity_text_excerpt": "",
            "main_text_excerpt": text, "pages": [],
            "structured_organisations": [], "social_links": [],
        },
    }


def test_provider_gate_defaults_all_false():
    assert not ProviderPrerequisites().all_met
    assert ProviderPrerequisites(
        terms_clearance=True,
        benchmark_disclosure_permission=True,
        api_key_in_evaluator=True,
        zero_dollar_plan_confirmed=True,
        available_monthly_credits_confirmed=True,
    ).all_met is False


def test_tavily_basic_body_excludes_generations_and_raw_crawl():
    body = tavily_basic_search_body(profile())
    assert body["query"] == f'"{COMPANY}" {ORG} OSLO'
    assert body["search_depth"] == "basic"
    assert body["max_results"] == 10
    assert body["include_answer"] is False
    assert body["include_raw_content"] is False
    assert body["include_images"] is False
    assert body["auto_parameters"] is False


def test_parser_preserves_only_transient_candidate_fields():
    query = "transient search"
    parsed = normalize_tavily_results(payload(), query=query)
    assert parsed == [{
        "url": URL, "title": "Example Bedrift AS",
        "snippet": "Org nr 123 456 789 Oslo",
        "rank": 1, "provider": "tavily_basic", "query": query,
    }]
    assert "SECRET_RAW_PROVIDER_TEXT" not in str(parsed)
    assert "UNTRUSTED_LLM_ANSWER" not in str(parsed)


def test_offline_no_page_cannot_qualify_publication():
    result = offline_screen(profile(), payload())
    assert result["candidate_nominated"]
    assert not result["independent_exact_site_eligible"]
    assert result["status"] == "independent_fetch_required"
    assert result["published_claims"] == 0


def test_exact_org_page_eligible_only_for_future_manual_review():
    result = offline_screen(profile(), payload(), site())
    assert result["candidate_nominated"]
    assert result["independent_exact_site_eligible"]
    assert result["status"] == "eligible_for_future_manual_review_only"
    assert result["published_claims"] == 0
    assert result["site_logical_requests_worst_case"] == 3
    assert result["provider_requests_executed"] == result["network_requests_executed"] == 0
    assert "UNTRUSTED_LLM_ANSWER" not in str(result)
    assert ORG not in str(result)


def test_provider_directory_result_quarantined_even_with_correct_org():
    result = offline_screen(
        profile(),
        payload(url="https://proff.no/selskap/example-bedrift-as/", content="Org 123 456 789"),
    )
    assert result["status"] == "no_qualifying_search_candidate"
    assert not result["candidate_nominated"]


def test_unrelated_hostname_with_only_company_title_no_org_never_nominated():
    result = offline_screen(
        profile(), payload(url="https://parentgroup.no/", content="subsidiary in Oslo")
    )
    assert result["status"] == "no_qualifying_search_candidate"


def test_website_already_seeded_does_not_run_search():
    result = offline_screen(profile(website="https://brreg-linked.no"), payload(), site())
    assert result["status"] == "existing_registry_site_seed"
    assert result["site_logical_requests_worst_case"] == 0


def test_wrong_requested_url_fixture_is_never_used_as_proof():
    result = offline_screen(profile(), payload(), site(requested_url="https://other.no/"))
    assert result["status"] == "independent_page_provenance_mismatch"
    assert not result["independent_exact_site_eligible"]


def test_wrong_org_number_in_independent_page_is_quarantined():
    bad = site(text="Example Bedrift AS. Organisasjonsnummer 987 654 321. Oslo.")
    result = offline_screen(profile(), payload(), bad)
    assert result["status"] == "conflicting_organisation_number"
    assert not result["independent_exact_site_eligible"]


def test_generic_hosting_placeholder_not_independent_identity():
    bad = site(text="Domain is for sale. Find the best information and links.", title="Domain for sale")
    result = offline_screen(profile(), payload(), bad)
    assert result["status"] == "page_identity_not_proven"


def test_parent_site_lacks_exact_legal_entity_page_proof():
    parent = site(
        url="https://parentgroup.no/", requested_url="https://parentgroup.no/",
        title="Parent Group",
        text="Among our subsidiary companies is Example Bedrift AS.",
    )
    result = offline_screen(
        profile(), payload(url="https://parentgroup.no/", content="Org nr 123 456 789 Oslo"),
        parent,
    )
    assert not result["independent_exact_site_eligible"]


def test_foreign_same_name_entity_stays_quarantined():
    foreign = site(text="Example Bedrift AB — svensk selskap i Oslo. Vi er et selskap.",
                   title=COMPANY)
    result = offline_screen(profile(), payload(), foreign)
    assert not result["independent_exact_site_eligible"]
    assert result["status"] in ("registry_collision_risk", "page_identity_not_proven")


def test_holding_company_needs_registry_location_when_org_absent():
    ambiguous = site(
        title=COMPANY,
        text="Example Bedrift AS utvikler bedriftsløsninger uten registrert lokasjon.",
    )
    result = offline_screen(profile(holding=True), payload(), ambiguous)
    assert result["status"] == "registry_collision_risk"
    assert not result["independent_exact_site_eligible"]


def test_provider_empty_and_malformed_outputs_abstain_without_exceptions():
    for p in ({}, {"results": None}, {"results": [{}]}, {"results": "garbage"}):
        result = offline_screen(profile(), p)
        assert result["status"] == "no_qualifying_search_candidate"
        assert not result["independent_exact_site_eligible"]
        assert result["published_claims"] == 0


def test_nonavailable_independent_page_cannot_qualify():
    result = offline_screen(profile(), payload(), site(status="blocked"))
    assert not result["independent_exact_site_eligible"]
    assert result["status"] == "page_identity_not_proven"
