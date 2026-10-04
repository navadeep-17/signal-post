from __future__ import annotations

from norway_company_agent.company_site_contact import (
    company_site_contact_email_observations,
    company_site_contact_phone_observations,
)
from norway_company_agent.external_footprint import validate_observation


def _profile(*, homepage_text: str = "EXAMPLE AS · Org.nr 912 345 678", surface_text: str = "") -> dict:
    profile = {
        "organisation_number": "912345678",
        "name": "EXAMPLE AS",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no/",
                "retrieved_at": "2026-10-04T10:00:00Z",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": "https://example.no/",
                    "registered_domain": "example.no",
                    "content_sha256": "a" * 64,
                    "identity_text_excerpt": homepage_text,
                    "identity_assessment": {
                        "status": "exact",
                        "score": 1.0,
                        "publishable": True,
                        "method": "test_homepage_exact",
                    },
                },
            }
        },
    }
    if surface_text:
        profile["evidence"]["website_contact_surface"] = {
            "status": "available",
            "source_url": "https://example.no/kontakt/",
            "retrieved_at": "2026-10-04T10:00:01Z",
            "content_sha256": "b" * 64,
            "value": {
                "final_url": "https://example.no/kontakt/",
                "registered_domain": "example.no",
                "content_sha256": "b" * 64,
                "identity_text_excerpt": surface_text,
                "contact_surface_identity": {
                    "status": "exact",
                    "publishable": True,
                    "method": "verified_homepage_contact_surface_exact_page_v1",
                    "target_org_number_on_page": True,
                    "full_legal_name_on_page": True,
                    "registry_location_on_page": False,
                },
            },
        }
    return profile


def test_contact_surface_email_and_phone_keep_page_local_url_and_hash() -> None:
    profile = _profile(
        surface_text=(
            "EXAMPLE AS · Org.nr 912 345 678 · Kontakt post@example.no · "
            "Telefon: +47 916 86 061"
        )
    )
    emails = company_site_contact_email_observations(profile)
    phones = company_site_contact_phone_observations(profile)

    assert [item["contact_email"] for item in emails] == ["post@example.no"]
    assert [item["contact_phone"] for item in phones] == ["+4791686061"]
    for item in [*emails, *phones]:
        assert item["source_url"] == "https://example.no/kontakt/"
        assert item["content_sha256"] == "b" * 64
        assert validate_observation(item) == []
        assert any(proof.get("type") == "contact_surface_exact_page_identity" for proof in item["identity_proof"])


def test_homepage_wins_when_same_contact_value_is_repeated_on_surface() -> None:
    profile = _profile(
        homepage_text=(
            "EXAMPLE AS · Org.nr 912 345 678 · post@example.no · Telefon: +47 916 86 061"
        ),
        surface_text=(
            "EXAMPLE AS · Org.nr 912 345 678 · post@example.no · Telefon: +47 916 86 061"
        ),
    )
    emails = company_site_contact_email_observations(profile)
    phones = company_site_contact_phone_observations(profile)

    assert len(emails) == 1
    assert len(phones) == 1
    assert emails[0]["source_url"] == "https://example.no/"
    assert phones[0]["source_url"] == "https://example.no/"
    assert emails[0]["content_sha256"] == "a" * 64
    assert phones[0]["content_sha256"] == "a" * 64


def test_untrusted_contact_surface_is_ignored() -> None:
    profile = _profile(surface_text="post@example.no · Telefon: +47 916 86 061")
    profile["evidence"]["website_contact_surface"]["value"]["contact_surface_identity"]["publishable"] = False
    assert company_site_contact_email_observations(profile) == []
    assert company_site_contact_phone_observations(profile) == []


def test_cross_domain_contact_surface_is_ignored_even_if_marked_publishable() -> None:
    profile = _profile(surface_text="post@example.no · Telefon: +47 916 86 061")
    surface = profile["evidence"]["website_contact_surface"]
    surface["source_url"] = "https://other.no/kontakt/"
    surface["value"]["final_url"] = "https://other.no/kontakt/"
    surface["value"]["registered_domain"] = "other.no"
    assert company_site_contact_email_observations(profile) == []
    assert company_site_contact_phone_observations(profile) == []
