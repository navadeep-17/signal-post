from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_contact import (  # noqa: E402
    attach_company_site_contact_email_observations,
    company_site_contact_email_observations,
    company_site_contact_phone_observations,
)
from norway_company_agent.external_footprint import validate_observation  # noqa: E402


def _profile(identity_text: str, *, website: str = "https://example.no/") -> dict:
    return {
        "organisation_number": "123456789",
        "external_observations": [],
        "evidence": {
            "website": {
                "status": "available",
                "source_url": website,
                "retrieved_at": "2026-09-15T10:00:00Z",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": website,
                    "content_sha256": "a" * 64,
                    "identity_text_excerpt": identity_text,
                    "identity_assessment": {
                        "status": "exact",
                        "score": 0.99,
                        "publishable": True,
                        "method": "test_exact_identity",
                    },
                },
            }
        },
    }


def test_extracts_same_domain_email_from_identity_footer_text() -> None:
    observations = company_site_contact_email_observations(
        _profile("Example AS · Org.nr 123 456 789 · Kontakt: Post@Example.no")
    )
    assert len(observations) == 1
    item = observations[0]
    assert item["contact_email"] == "post@example.no"
    assert item["signal_type"] == "company_profile"
    assert item["platform"] == "company_site"
    assert item["source_url"] == "https://example.no/"
    assert validate_observation(item) == []


def test_extracts_only_explicitly_labelled_norwegian_contact_phones() -> None:
    observations = company_site_contact_phone_observations(
        _profile("Telefon: +47 916 86 061 · Tlf. 481 70 071 · Org.nr 123 456 789 · Ref 87654321")
    )
    assert [item["contact_phone"] for item in observations] == [
        "+4748170071",
        "+4791686061",
    ]
    assert all(item["signal_type"] == "company_profile" for item in observations)
    assert all(validate_observation(item) == [] for item in observations)
    assert all("explicitly labels contact phone" in item["evidence_span"] for item in observations)


def test_unlabelled_numbers_do_not_become_contact_phones() -> None:
    assert company_site_contact_phone_observations(
        _profile("Org.nr 123 456 789 · Kundereferanse 87654321")
    ) == []


def test_rejects_cross_domain_email_even_when_present_in_footer() -> None:
    observations = company_site_contact_email_observations(
        _profile("Kontakt oss på support@parent-company.com")
    )
    assert observations == []


def test_rejects_placeholder_and_no_reply_addresses() -> None:
    observations = company_site_contact_email_observations(
        _profile("example@example.no noreply@example.no no-reply@example.no")
    )
    assert observations == []


def test_does_not_scan_main_text_outside_identity_excerpt() -> None:
    profile = _profile("Org.nr 123456789")
    profile["evidence"]["website"]["value"]["main_text_excerpt"] = (
        "Author: journalist@example.no Telefon: +47 999 88 777"
    )
    assert company_site_contact_email_observations(profile) == []
    assert company_site_contact_phone_observations(profile) == []


def test_unverified_website_abstains() -> None:
    profile = _profile("post@example.no Telefon: +47 999 88 777")
    profile["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    assert company_site_contact_email_observations(profile) == []
    assert company_site_contact_phone_observations(profile) == []


def test_invalid_org_abstains() -> None:
    profile = _profile("post@example.no Telefon: +47 999 88 777")
    profile["organisation_number"] = "123"
    assert company_site_contact_email_observations(profile) == []
    assert company_site_contact_phone_observations(profile) == []


def test_caps_and_deduplicates_contacts_deterministically() -> None:
    observations = company_site_contact_email_observations(
        _profile("z@example.no a@example.no a@example.no b@example.no c@example.no")
    )
    assert [item["contact_email"] for item in observations] == [
        "a@example.no",
        "b@example.no",
        "c@example.no",
    ]

    phones = company_site_contact_phone_observations(
        _profile(
            "Telefon: 999 99 999 · Telefon: 111 11 111 · Tlf: 11111111 · "
            "Phone: 222 22 222 · Tel: 33333333"
        )
    )
    assert [item["contact_phone"] for item in phones] == [
        "+4711111111",
        "+4722222222",
        "+4733333333",
    ]


def test_attachment_is_idempotent_and_preserves_other_observations() -> None:
    profile = _profile("post@example.no · Telefon: +47 999 88 777")
    profile["external_observations"] = [
        {
            "id": "existing-h2a",
            "organisation_number": "123456789",
            "platform": "instagram",
            "signal_type": "profile_handle",
        }
    ]
    attach_company_site_contact_email_observations(profile)
    attach_company_site_contact_email_observations(profile)
    ids = [item["id"] for item in profile["external_observations"]]
    assert ids.count("existing-h2a") == 1
    assert len([value for value in ids if value.startswith("company-site-email-")]) == 1
    assert len([value for value in ids if value.startswith("company-site-phone-")]) == 1
