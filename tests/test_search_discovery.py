from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.discovery import (  # noqa: E402
    build_company_search_query,
    choose_search_candidate,
    parse_serpapi_web_results,
    qualify_search_discovered_website,
    score_search_candidate,
)


def profile(*, name="EXAMPLE BEDRIFT AS", org="123456789", municipality="OSLO"):
    return {
        "organisation_number": org,
        "name": name,
        "municipality": municipality,
    }


def website(*, title="", text="", final_url="https://examplebedrift.no/", pages=None):
    return {
        "status": "available",
        "source_url": final_url,
        "value": {
            "final_url": final_url,
            "title": title,
            "description": "",
            "main_text_excerpt": text,
            "structured_organisations": [],
            "pages": pages or [],
        },
    }


def exact_assessment():
    return {
        "status": "exact",
        "score": 0.95,
        "publishable": True,
        "reasons": ["general website gate passed"],
        "method": "deterministic_name_org_evidence_v2",
    }


def test_serpapi_parser_normalizes_only_search_fields_needed_in_memory():
    payload = {
        "organic_results": [
            {
                "position": 2,
                "title": "Example Bedrift AS",
                "link": "https://examplebedrift.no/",
                "snippet": "Org nr 123 456 789 – Oslo",
                "thumbnail": "must-not-be-carried",
            }
        ]
    }
    result = parse_serpapi_web_results(payload, query='"EXAMPLE BEDRIFT AS" 123456789 OSLO')
    assert result == [
        {
            "url": "https://examplebedrift.no/",
            "title": "Example Bedrift AS",
            "snippet": "Org nr 123 456 789 – Oslo",
            "rank": 2,
            "provider": "serpapi_google",
            "query": '"EXAMPLE BEDRIFT AS" 123456789 OSLO',
        }
    ]


def test_search_query_requires_legal_name_and_org_number():
    assert build_company_search_query(profile()) == '"EXAMPLE BEDRIFT AS" 123456789 OSLO'


def test_directory_result_is_never_a_company_site_candidate():
    item = score_search_candidate(
        profile(),
        {
            "url": "https://proff.no/selskap/example-bedrift-as/",
            "title": "Example Bedrift AS",
            "snippet": "Org 123 456 789 Oslo",
            "rank": 1,
            "provider": "serpapi_google",
            "query": "q",
        },
    )
    assert item["publishable_candidate"] is False
    assert item["status"] == "rejected"


def test_candidate_selection_prefers_exact_company_hostname_and_search_evidence():
    results = [
        {
            "url": "https://examplebedrift.no/",
            "title": "Example Bedrift AS",
            "snippet": "Org nr 123 456 789 Oslo",
            "rank": 2,
            "provider": "serpapi_google",
            "query": "q",
        },
        {
            "url": "https://example.com/",
            "title": "Example Bedrift AS",
            "snippet": "Org nr 123 456 789 Oslo",
            "rank": 1,
            "provider": "serpapi_google",
            "query": "q",
        },
    ]
    decision = choose_search_candidate(profile(), results)
    assert decision["selected"]["url"] == "https://examplebedrift.no/"


def test_search_result_success_cannot_publish_without_independent_page_identity():
    result = qualify_search_discovered_website(
        profile(),
        website(title="Welcome", text="Generic web hosting page with no legal identity."),
        exact_assessment(),
    )
    assert result["publishable"] is False
    assert result["status"] == "review"
    assert result["method"] == "search_discovered_page_identity_guard_v1"


def test_exact_org_number_on_independent_page_is_strongest_proof():
    result = qualify_search_discovered_website(
        profile(),
        website(title="Example Bedrift", text="Example Bedrift AS. Organisasjonsnummer 123 456 789."),
        exact_assessment(),
    )
    assert result["publishable"] is True
    assert result["score"] == 1.0


def test_full_legal_name_plus_registry_municipality_can_publish_acronym_domain():
    result = qualify_search_discovered_website(
        profile(name="ARKITEKTFIRMA JON VIKØREN AS", org="985589003", municipality="OSLO"),
        website(
            title="Arkitektfirma Jon Vikøren AS",
            text="Arkitektfirma Jon Vikøren AS holder til i Oslo.",
            final_url="https://arkjv.no/",
        ),
        exact_assessment(),
    )
    assert result["publishable"] is True
    assert result["status"] == "exact"


def test_parent_page_mention_without_location_or_exact_company_domain_is_quarantined():
    result = qualify_search_discovered_website(
        profile(name="EXAMPLE BEDRIFT AS", municipality="OSLO"),
        website(
            title="Parent Group",
            text="Our subsidiaries include Example Bedrift AS and several other companies.",
            final_url="https://parentgroup.no/",
        ),
        exact_assessment(),
    )
    assert result["publishable"] is False
    assert result["status"] == "review"


def test_namesake_page_wrong_municipality_is_quarantined():
    result = qualify_search_discovered_website(
        profile(name="EXAMPLE BEDRIFT AS", municipality="OSLO"),
        website(
            title="Example Bedrift AS",
            text="Example Bedrift AS holder til i Bergen.",
            final_url="https://unrelated-example.no/",
        ),
        exact_assessment(),
    )
    assert result["publishable"] is False


def test_exact_name_domain_plus_full_page_name_can_publish_without_municipality_text():
    result = qualify_search_discovered_website(
        profile(name="EXAMPLE BEDRIFT AS", municipality="OSLO"),
        website(
            title="Example Bedrift AS",
            text="Velkommen til Example Bedrift AS.",
            final_url="https://examplebedrift.no/",
        ),
        exact_assessment(),
    )
    assert result["publishable"] is True
