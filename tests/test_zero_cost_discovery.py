from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.zero_cost_discovery import (  # noqa: E402
    deterministic_domain_candidates,
    qualify_deterministic_domain_identity,
)


def profile(name="MASTER SURGERY SYSTEMS AS", org="993550116", municipality="HORTEN"):
    return {
        "organisation_number": org,
        "name": name,
        "municipality": municipality,
        "evidence": {
            "registry": {
                "status": "available",
                "value": {
                    "forretningsadresse.postnummer": "3187",
                    "forretningsadresse.poststed": "HORTEN",
                    "forretningsadresse.kommune": "HORTEN",
                    "forretningsadresse.adresse": "Bekkajordet 8A",
                },
            }
        },
    }


def website(text="", title="", final_url="https://mastersurgerysystems.no/"):
    return {
        "status": "available",
        "source_url": final_url,
        "value": {
            "final_url": final_url,
            "title": title,
            "description": "",
            "main_text_excerpt": text,
            "structured_organisations": [],
            "pages": [],
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


def test_candidates_are_bounded_to_exact_legal_name_forms():
    plan = deterministic_domain_candidates(profile())
    assert plan["eligible"] is True
    assert [item["domain"] for item in plan["candidates"]] == [
        "mastersurgerysystems.no",
        "master-surgery-systems.no",
    ]
    assert len(plan["candidates"]) <= 2


def test_single_token_name_does_not_duplicate_same_candidate():
    plan = deterministic_domain_candidates(profile(name="MESCO AS"))
    assert [item["domain"] for item in plan["candidates"]] == ["mesco.no"]


def test_verified_website_skips_h1c_entirely():
    item = profile()
    item["evidence"]["website"] = {
        "status": "available",
        "value": {"identity_assessment": {"publishable": True}},
    }
    plan = deterministic_domain_candidates(item)
    assert plan["eligible"] is False
    assert plan["reason"] == "verified_website_present"


def test_exact_org_number_on_page_is_strongest_h1c_proof():
    result = qualify_deterministic_domain_identity(
        profile(),
        "mastersurgerysystems.no",
        website(text="Master Surgery Systems AS. Organisasjonsnummer 993 550 116."),
        exact_assessment(),
    )
    assert result["publishable"] is True
    assert result["score"] == 1.0
    assert result["method"] == "deterministic_domain_page_identity_guard_v1"


def test_full_legal_name_on_exact_domain_can_publish_without_org_number():
    result = qualify_deterministic_domain_identity(
        profile(),
        "mastersurgerysystems.no",
        website(title="Master Surgery Systems AS", text="Master Surgery Systems AS develops surgical systems."),
        exact_assessment(),
    )
    assert result["publishable"] is True


def test_parent_or_namesake_page_without_company_compatible_domain_is_quarantined():
    result = qualify_deterministic_domain_identity(
        profile(),
        "mastersurgerysystems.no",
        website(
            title="Parent Group",
            text="Our portfolio includes Master Surgery Systems AS.",
            final_url="https://parent-group.no/",
        ),
        exact_assessment(),
    )
    assert result["publishable"] is False
    assert result["status"] == "review"


def test_generic_page_cannot_publish_just_because_guessed_domain_resolves():
    result = qualify_deterministic_domain_identity(
        profile(),
        "mastersurgerysystems.no",
        website(title="Welcome", text="Domain registered. Web hosting coming soon."),
        exact_assessment(),
    )
    assert result["publishable"] is False
    assert result["status"] == "review"


def test_registry_location_can_corroborate_full_name_after_redirect():
    result = qualify_deterministic_domain_identity(
        profile(),
        "mastersurgerysystems.no",
        website(
            title="Master Surgery Systems AS",
            text="Master Surgery Systems AS, Bekkajordet 8A, 3187 Horten.",
            final_url="https://mss-medical.no/",
        ),
        exact_assessment(),
    )
    assert result["publishable"] is True
