from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_contact import company_site_contact_email_observations  # noqa: E402
from norway_company_agent.external_footprint import validate_observation  # noqa: E402


def _profile(*, name: str = "EXAMPLE COMPANY AS", website: str = "https://example.no/") -> dict:
    return {
        "organisation_number": "123456789",
        "name": name,
        "external_observations": [],
        "evidence": {
            "website": {
                "status": "available",
                "source_url": website,
                "retrieved_at": "2026-10-06T00:00:00Z",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": website,
                    "content_sha256": "a" * 64,
                    "identity_text_excerpt": "",
                    "identity_assessment": {
                        "status": "exact",
                        "score": 0.99,
                        "publishable": True,
                        "method": "test_exact_identity",
                    },
                    "structured_organisations": [],
                },
            }
        },
    }


def _structured(profile: dict, node: dict) -> dict:
    profile["evidence"]["website"]["value"]["structured_organisations"] = [node]
    return profile


def test_exact_org_node_can_recover_same_domain_email() -> None:
    profile = _structured(
        _profile(),
        {
            "@type": "Organization",
            "name": "Completely Different Display Brand",
            "identifier": "NO 123 456 789",
            "contactPoint": {"@type": "ContactPoint", "email": "hello@example.no"},
        },
    )
    rows = company_site_contact_email_observations(profile)
    assert len(rows) == 1
    item = rows[0]
    assert item["contact_email"] == "hello@example.no"
    assert item["strategy"] == "verified_company_jsonld_same_domain_email_v1"
    gate = next(x for x in item["identity_proof"] if x.get("type") == "structured_organization_identity_gate")
    assert gate["method"] == "structured_exact_organisation_number"
    assert gate["observed_organisation_numbers"] == ["123456789"]
    assert validate_observation(item) == []


def test_explicit_different_org_number_vetoes_even_matching_name() -> None:
    profile = _structured(
        _profile(),
        {
            "@type": "Organization",
            "legalName": "EXAMPLE COMPANY AS",
            "identifier": "987654321",
            "email": "hello@example.no",
        },
    )
    assert company_site_contact_email_observations(profile) == []


def test_exact_legal_name_node_without_org_can_recover_same_domain_email() -> None:
    profile = _structured(
        _profile(name="ALPINE DESIGN STUDIO AS", website="https://alpine.no/"),
        {
            "@type": "Organization",
            "legalName": "Alpine Design Studio AS",
            "email": "kontakt@alpine.no",
        },
    )
    rows = company_site_contact_email_observations(profile)
    assert len(rows) == 1
    gate = next(x for x in rows[0]["identity_proof"] if x.get("type") == "structured_organization_identity_gate")
    assert gate["method"] == "structured_legal_name_token_match"
    assert gate["observed_organisation_numbers"] == []


def test_partial_name_node_is_not_sufficient() -> None:
    profile = _structured(
        _profile(name="ALPINE DESIGN STUDIO AS", website="https://alpine.no/"),
        {
            "@type": "Organization",
            "name": "Alpine",
            "email": "kontakt@alpine.no",
        },
    )
    assert company_site_contact_email_observations(profile) == []


def test_cross_domain_structured_email_abstains() -> None:
    profile = _structured(
        _profile(),
        {
            "@type": "Organization",
            "identifier": "123456789",
            "email": "contact@parent-company.com",
        },
    )
    assert company_site_contact_email_observations(profile) == []


def test_email_like_free_text_is_not_scanned_outside_email_field() -> None:
    profile = _structured(
        _profile(),
        {
            "@type": "Organization",
            "identifier": "123456789",
            "description": "Contact hello@example.no for more information",
        },
    )
    assert company_site_contact_email_observations(profile) == []


def test_unrelated_organisation_node_cannot_donate_contact() -> None:
    profile = _profile()
    profile["evidence"]["website"]["value"]["structured_organisations"] = [
        {
            "@type": "Organization",
            "legalName": "EXAMPLE COMPANY AS",
            "identifier": "123456789",
        },
        {
            "@type": "Organization",
            "legalName": "THEME VENDOR AS",
            "identifier": "987654321",
            "email": "support@example.no",
        },
    ]
    assert company_site_contact_email_observations(profile) == []


def test_existing_footer_email_keeps_precedence_over_same_jsonld_email() -> None:
    profile = _profile()
    value = profile["evidence"]["website"]["value"]
    value["identity_text_excerpt"] = "Kontakt: hello@example.no"
    value["structured_organisations"] = [
        {
            "@type": "Organization",
            "identifier": "123456789",
            "email": "hello@example.no",
        }
    ]
    rows = company_site_contact_email_observations(profile)
    assert len(rows) == 1
    assert rows[0]["strategy"] == "verified_company_page_same_domain_email_v1"
