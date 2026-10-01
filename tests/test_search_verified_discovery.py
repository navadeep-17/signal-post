from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import norway_company_agent.search_verified_discovery as search  # noqa: E402


def profile(
    *,
    name="EXAMPLE SYSTEMS AS",
    org="912345678",
    street="Karl Johans gate 1",
    postcode="0154",
    town="OSLO",
    municipality="OSLO",
):
    return {
        "organisation_number": org,
        "name": name,
        "municipality": municipality,
        "website": "",
        "evidence": {
            "registry": {
                "status": "available",
                "value": {
                    "forretningsadresse.adresse": street,
                    "forretningsadresse.postnummer": postcode,
                    "forretningsadresse.poststed": town,
                    "forretningsadresse.kommune": municipality,
                },
            },
            "website": {"status": "not_found"},
        },
    }


def website(
    *,
    url="https://example-systems.no/",
    title="Example Systems AS",
    text="Example Systems AS",
    identity_text="",
):
    return {
        "status": "available",
        "source_url": url,
        "value": {
            "final_url": url,
            "title": title,
            "description": "",
            "identity_text_excerpt": identity_text,
            "main_text_excerpt": text,
            "structured_organisations": [],
            "pages": [
                {
                    "url": url,
                    "title": title,
                    "identity_text_excerpt": identity_text,
                    "main_text_excerpt": text,
                }
            ],
        },
    }


def base_assessment(publishable=True):
    return {
        "status": "exact" if publishable else "review",
        "score": 0.95 if publishable else 0.8,
        "publishable": publishable,
        "reasons": ["general gate fixture"],
        "method": "fixture",
    }


def test_directory_and_platform_hosts_are_removed_before_nomination():
    results = [
        {"url": "https://proff.no/selskap/example-systems-as/", "title": "Example Systems AS", "snippet": "912345678", "rank": 1},
        {"url": "https://www.linkedin.com/company/example-systems/", "title": "Example Systems AS", "snippet": "", "rank": 2},
        {"url": "https://example-systems.no/", "title": "Example Systems AS", "snippet": "Org nr 912 345 678", "rank": 3},
    ]
    kept = search.filter_search_results(results)
    assert [item["url"] for item in kept] == ["https://example-systems.no/"]


def test_search_nomination_is_only_a_crawl_candidate():
    decision = search.choose_search_nomination(
        profile(),
        [
            {
                "url": "https://example-systems.no/",
                "title": "Example Systems AS",
                "snippet": "Org nr 912 345 678 Oslo",
                "rank": 1,
                "provider": "brave_search_api",
                "query": '"EXAMPLE SYSTEMS AS" 912345678 OSLO',
            }
        ],
    )
    assert decision["selected"] is not None
    assert decision["selected"]["url"] == "https://example-systems.no/"
    assert "crawl" in decision["selected"]["status"]


def test_exact_target_org_on_independent_page_is_strongest_proof():
    result = search.qualify_search_discovered_page(
        profile(),
        website(text="Example Systems AS. Organisasjonsnummer 912 345 678."),
        base_assessment(),
    )
    assert result is not None
    assert result["publishable"] is True
    assert result["score"] == 1.0
    assert result["method"] == "search_discovered_exact_company_guard_v2"


def test_target_org_plus_other_labelled_org_is_quarantined():
    result = search.qualify_search_discovered_page(
        profile(),
        website(
            text=(
                "Example Systems AS. Organisasjonsnummer 912 345 678. "
                "Parent Group AS. Organisasjonsnummer 999 888 777."
            )
        ),
        base_assessment(),
    )
    assert result is not None
    assert result["publishable"] is False
    assert result["status"] == "review"
    assert "another organisation number" in " ".join(result["reasons"]).casefold()


def test_legal_name_in_identity_position_plus_postcode_and_town_can_publish():
    result = search.qualify_search_discovered_page(
        profile(),
        website(
            title="Example Systems AS",
            text="Software company. Visit us at 0154 Oslo.",
        ),
        base_assessment(False),
    )
    assert result is not None
    assert result["publishable"] is True
    assert result["score"] >= 0.98


def test_legal_name_in_footer_plus_exact_street_and_house_can_publish():
    result = search.qualify_search_discovered_page(
        profile(),
        website(
            title="Example",
            text="Products and services.",
            identity_text="Example Systems AS · Karl Johans gate 1",
        ),
        base_assessment(False),
    )
    assert result is not None
    assert result["publishable"] is True


def test_municipality_name_alone_is_not_address_proof():
    result = search.qualify_search_discovered_page(
        profile(),
        website(
            title="Example Systems AS",
            text="Example Systems AS works with customers across Oslo.",
        ),
        base_assessment(),
    )
    assert result is not None
    assert result["publishable"] is False


def test_bare_postcode_without_town_is_not_address_proof():
    result = search.qualify_search_discovered_page(
        profile(),
        website(
            title="Example Systems AS",
            text="Example Systems AS. Reference number 0154.",
        ),
        base_assessment(),
    )
    assert result is not None
    assert result["publishable"] is False


def test_legal_name_only_in_body_does_not_establish_site_owner():
    result = search.qualify_search_discovered_page(
        profile(),
        website(
            title="Parent Group",
            text="Our portfolio includes Example Systems AS at Karl Johans gate 1, 0154 Oslo.",
            identity_text="Parent Group",
        ),
        base_assessment(),
    )
    assert result is not None
    assert result["publishable"] is False


def test_single_token_legal_name_requires_legal_form_in_identity_position():
    item = profile(name="MESCO AS", org="999111222", street="Storgata 5", postcode="0184", town="OSLO")
    weak = search.qualify_search_discovered_page(
        item,
        website(title="Mesco", text="Mesco · Storgata 5, 0184 Oslo."),
        base_assessment(),
    )
    strong = search.qualify_search_discovered_page(
        item,
        website(title="MESCO AS", text="MESCO AS · Storgata 5, 0184 Oslo."),
        base_assessment(),
    )
    assert weak is not None and weak["publishable"] is False
    assert strong is not None and strong["publishable"] is True


def test_evaluate_search_nomination_never_promotes_when_strict_gate_fails(monkeypatch):
    record = website(title="Parent Group", text="Parent Group mentions Example Systems AS in Oslo.")

    monkeypatch.setattr(
        search,
        "fetch_bounded_homepage",
        lambda url, *, source_type, timeout: (record, {"requests": 2, "bytes": 10, "latencies_ms": [1]}),
    )
    monkeypatch.setattr(
        search,
        "apply_website_identity_gate",
        lambda row, candidate: {"website": candidate, "assessment": base_assessment()},
    )

    row, metrics = search.evaluate_search_nomination(profile(), "https://parent-group.no/")
    assert metrics["publishable"] is False
    assert row.get("website") in (None, "")
    assert row["evidence"]["website_search_candidate"]["status"] == "available"
    assert row["evidence"]["website"]["status"] == "not_found"


def test_query_hash_is_deterministic_and_does_not_expose_plaintext():
    query = '"EXAMPLE SYSTEMS AS" 912345678 OSLO'
    digest = search.query_hash(query)
    assert len(digest) == 64
    assert query not in digest
    assert digest == search.query_hash(query)
