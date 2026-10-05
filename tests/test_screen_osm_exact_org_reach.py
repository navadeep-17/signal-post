import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "screen_osm_exact_org_reach.py"
spec = importlib.util.spec_from_file_location("screen_osm_exact_org", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def element(org: str, **tags):
    return {
        "type": "node",
        "id": 1,
        "tags": {"ref:NO:orgnr": org, **tags},
    }


def test_only_standardized_exact_org_tag_counts():
    payload = {
        "elements": [
            element("999999999", website="https://example.no"),
            {"type": "node", "id": 2, "tags": {"ref:orgnr": "888888888", "website": "https://wrong.no"}},
            element("99999999X", website="https://bad.no"),
        ]
    }
    report, matches = module.screen(payload, {"999999999", "888888888"})
    assert report["exact_target_company_hits"] == 1
    assert report["malformed_ref_no_orgnr_values"] == 1
    assert matches[0]["organisation_number"] == "999999999"
    assert matches[0]["website_candidate"] == "https://example.no"


def test_conflicting_domains_abstain_from_website_candidate():
    payload = {
        "elements": [
            element("999999999", website="example.no"),
            {"type": "way", "id": 2, "tags": {"ref:NO:orgnr": "999999999", "contact:website": "https://other.no/contact"}},
        ]
    }
    report, matches = module.screen(payload, {"999999999"})
    assert report["exact_target_company_hits"] == 1
    assert report["website_candidate_companies"] == 0
    assert report["ambiguous_website_companies"] == 1
    assert matches[0]["website_candidate"] is None
    assert matches[0]["website_domains"] == ["example.no", "other.no"]


def test_same_domain_collapses_and_contact_candidates_are_observations():
    payload = {
        "elements": [
            element(
                "999999999",
                website="http://www.example.no",
                **{"contact:website": "https://example.no/about", "email": "HELLO@EXAMPLE.NO", "contact:instagram": "example"},
            )
        ]
    }
    report, matches = module.screen(payload, {"999999999"})
    assert report["website_candidate_companies"] == 1
    assert report["email_candidate_companies"] == 1
    assert report["social_candidate_companies"] == 1
    assert matches[0]["website_domains"] == ["example.no"]
    assert matches[0]["email_candidates"] == ["hello@example.no"]
