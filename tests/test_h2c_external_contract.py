from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection  # noqa: E402
from norway_company_agent.company_site_contact import attach_company_site_contact_email_observations  # noqa: E402
from norway_company_agent.external_contract import project_contact_email_observations  # noqa: E402
from norway_company_agent.output_contract import project_terminal_envelope, validate_contract_object  # noqa: E402


def _profile() -> dict:
    digest = "c" * 64
    source_url = "https://example.no/"
    return {
        "organisation_number": "912345678",
        "name": "EXAMPLE AS",
        "legal_form": "AS",
        "evidence": {
            "registry": {
                "status": "available",
                "source_type": "official_registry_bulk",
                "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
                "retrieved_at": "2026-09-15T09:00:00Z",
                "content_sha256": "d" * 64,
                "value": {},
            },
            "website": {
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": source_url,
                "retrieved_at": "2026-09-15T09:00:00Z",
                "content_sha256": digest,
                "value": {
                    "final_url": source_url,
                    "content_sha256": digest,
                    "identity_text_excerpt": "Kontakt oss på post@example.no · Telefon: +47 916 86 061",
                    "identity_assessment": {
                        "status": "exact",
                        "score": 1.0,
                        "publishable": True,
                        "method": "test_exact_identity",
                    },
                    "pages": [{"url": source_url, "content_sha256": digest}],
                },
            },
        },
        "run_metrics": {"requests": 4, "latencies_ms": [10, 20]},
    }


def _envelope(profile: dict) -> dict:
    return {
        "run_id": "h2c-test",
        "organisation_number": profile["organisation_number"],
        "state": "complete",
        "started_at": "2026-09-15T09:00:00Z",
        "completed_at": "2026-09-15T09:00:01Z",
        "profile": profile,
    }


def test_contract_projects_contact_email_and_phone_with_exact_company_page_evidence() -> None:
    profile = attach_company_site_contact_email_observations(_profile())
    base = project_terminal_envelope(_envelope(profile))
    projected = project_contact_email_observations(base, profile)

    assert validate_contract_object(projected) == []
    email_claims = [claim for claim in projected["claims"] if claim["field"] == "external.contact_email"]
    phone_claims = [claim for claim in projected["claims"] if claim["field"] == "external.contact_phone"]
    assert len(email_claims) == 1
    assert len(phone_claims) == 1
    assert email_claims[0]["value"] == "post@example.no"
    assert phone_claims[0]["value"] == "+4791686061"
    assert email_claims[0]["signal_type"] == "company_profile"
    assert phone_claims[0]["signal_type"] == "company_profile"
    assert "registered domain" in email_claims[0]["claim_scope"].lower()
    assert "explicitly labelled" in phone_claims[0]["claim_scope"].lower()

    evidence_by_id = {item["id"]: item for item in projected["evidence"]}
    email_evidence = evidence_by_id[email_claims[0]["evidence_ids"][0]]
    phone_evidence = evidence_by_id[phone_claims[0]["evidence_ids"][0]]
    assert email_evidence["source_url"] == "https://example.no/"
    assert phone_evidence["source_url"] == "https://example.no/"
    assert email_evidence["content_sha256"] == "c" * 64
    assert phone_evidence["content_sha256"] == "c" * 64
    assert "post@example.no" in email_evidence["claim_span"]
    assert "+4791686061" in phone_evidence["claim_span"]


def test_contact_projection_is_idempotent_for_email_and_phone() -> None:
    profile = attach_company_site_contact_email_observations(_profile())
    base = project_terminal_envelope(_envelope(profile))
    once = project_contact_email_observations(base, profile)
    twice = project_contact_email_observations(once, profile)

    for field in ("external.contact_email", "external.contact_phone"):
        once_claims = [claim for claim in once["claims"] if claim["field"] == field]
        twice_claims = [claim for claim in twice["claims"] if claim["field"] == field]
        assert twice_claims == once_claims
        assert len(twice_claims) == 1
    assert len([item for item in twice["evidence"] if str(item["id"]).startswith("ev-external-")]) == 2


def test_contact_projection_does_not_remove_other_external_claims() -> None:
    profile = attach_company_site_contact_email_observations(_profile())
    base = project_terminal_envelope(_envelope(profile))
    base["claims"].append(
        {
            "field": "external.profile_handle",
            "value": "https://linkedin.com/company/example-as",
            "availability": "available",
            "confidence": 0.98,
            "evidence_ids": [],
        }
    )

    projected = project_contact_email_observations(base, profile)
    assert any(claim["field"] == "external.profile_handle" for claim in projected["claims"])
    assert any(claim["field"] == "external.contact_email" for claim in projected["claims"])
    assert any(claim["field"] == "external.contact_phone" for claim in projected["claims"])


def test_contact_phone_is_canonical_website_fact_without_overwriting_registered_phone() -> None:
    profile = attach_company_site_contact_email_observations(_profile())
    base = project_terminal_envelope(_envelope(profile))
    projected = project_contact_email_observations(base, profile)
    projected["claims"].append(
        {
            "field": "registered_phone",
            "value": "22 33 44 55",
            "availability": "available",
            "confidence": 1.0,
            "evidence_ids": [projected["evidence"][0]["id"]],
        }
    )
    canonical = project_canonical_profile(projected)
    assert validate_canonical_projection(canonical) == []
    facts = canonical["canonical_facts"]
    assert any(
        fact["type"] == "contact_phone"
        and fact["canonical_field"] == "website.contact_phone"
        and fact["value"] == "+4791686061"
        for fact in facts
    )
    assert any(
        fact["type"] == "registered_phone"
        and fact["canonical_field"] == "company.contact.phone"
        and fact["value"] == "22 33 44 55"
        for fact in facts
    )
