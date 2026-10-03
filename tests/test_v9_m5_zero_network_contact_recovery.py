from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.zero_network_contact_recovery import (
    recover_secondary_contact_email_observations,
)


def profile(*, page_url="https://example.no/kontakt", page_hash="b" * 64, text="Kontakt oss på post@example.no"):
    return {
        "organisation_number": "123456789",
        "external_observations": [],
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no/",
                "retrieved_at": "2026-10-03T10:00:00Z",
                "value": {
                    "final_url": "https://example.no/",
                    "identity_assessment": {
                        "status": "exact",
                        "publishable": True,
                        "score": 0.99,
                        "method": "test_exact",
                    },
                    "secondary_identity_page": {
                        "url": page_url,
                        "content_sha256": page_hash,
                    },
                    "pages": [
                        {
                            "url": "https://example.no/",
                            "content_sha256": "a" * 64,
                            "identity_text_excerpt": "Example AS",
                            "main_text_excerpt": "Homepage",
                        },
                        {
                            "url": page_url,
                            "content_sha256": page_hash,
                            "identity_text_excerpt": text,
                            "main_text_excerpt": text,
                        },
                    ],
                },
            }
        },
    }


def test_recovers_same_domain_email_with_secondary_page_provenance():
    rows = recover_secondary_contact_email_observations(profile())
    assert len(rows) == 1
    row = rows[0]
    assert row["contact_email"] == "post@example.no"
    assert row["source_url"] == "https://example.no/kontakt"
    assert row["content_sha256"] == "b" * 64
    assert row["metrics"]["network_requests_added"] == 0
    assert any(item["type"] == "retained_secondary_identity_page" for item in row["identity_proof"])


def test_cross_domain_email_is_not_published():
    assert recover_secondary_contact_email_observations(
        profile(text="Kontakt support@vendor.com")
    ) == []


def test_cross_registered_domain_secondary_page_is_not_trusted():
    assert recover_secondary_contact_email_observations(
        profile(page_url="https://other.no/kontakt", text="post@example.no")
    ) == []


def test_secondary_marker_must_match_retained_page_hash_exactly():
    row = profile()
    row["evidence"]["website"]["value"]["secondary_identity_page"]["content_sha256"] = "c" * 64
    assert recover_secondary_contact_email_observations(row) == []


def test_unpublishable_website_never_recovers_contact():
    row = profile()
    row["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    assert recover_secondary_contact_email_observations(row) == []


def test_existing_contact_email_is_not_duplicated():
    row = profile()
    row["external_observations"] = [
        {
            "id": "existing",
            "signal_type": "company_profile",
            "contact_email": "post@example.no",
        }
    ]
    assert recover_secondary_contact_email_observations(row) == []


def test_placeholder_and_noreply_addresses_are_rejected():
    row = profile(text="example@example.no no-reply@example.no valid@example.no")
    rows = recover_secondary_contact_email_observations(row)
    assert [item["contact_email"] for item in rows] == ["valid@example.no"]


def test_missing_secondary_marker_abstains_even_if_page_contains_email():
    row = profile()
    row["evidence"]["website"]["value"].pop("secondary_identity_page")
    assert recover_secondary_contact_email_observations(row) == []
