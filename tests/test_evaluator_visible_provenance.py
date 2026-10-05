from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.evidence_provenance import (  # noqa: E402
    observation_provenance,
    project_evaluator_visible_provenance,
    website_provenance,
)
from norway_company_agent.support_contract import project_support_award_observations  # noqa: E402


def _website_profile() -> dict:
    return {
        "organisation_number": "923609016",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://acme.example/",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": "https://acme.example/",
                    "identity_assessment": {
                        "status": "exact",
                        "score": 0.95,
                        "publishable": True,
                        "reasons": ["exact company identity evidence"],
                        "method": "deterministic_name_org_evidence_v4",
                    },
                },
            }
        },
        "external_observations": [],
    }


def test_observation_provenance_copies_retained_identity_and_strategy() -> None:
    observation = {
        "identity_proof": [{"type": "official_registry_exact_organisation_number", "value": "923609016"}],
        "strategy": "official_registry_employee_count_v1",
    }

    assert observation_provenance(observation) == {
        "identity_proof": observation["identity_proof"],
        "extraction_method": "official_registry_employee_count_v1",
    }


def test_website_provenance_exposes_existing_identity_assessment() -> None:
    website = _website_profile()["evidence"]["website"]

    trace = website_provenance(website)

    assert trace["identity_proof"] == website["value"]["identity_assessment"]
    assert trace["extraction_method"] == "deterministic_name_org_evidence_v4"


def test_projects_observation_provenance_by_observation_id() -> None:
    profile = _website_profile()
    profile["external_observations"] = [
        {
            "id": "obs-contact",
            "identity_proof": [{"type": "website_identity_gate", "status": "exact"}],
            "strategy": "verified_company_page_same_domain_email_v1",
        }
    ]
    contract = {
        "organisation_number": "923609016",
        "claims": [
            {
                "field": "external.contact_email",
                "availability": "available",
                "value": "post@acme.example",
                "evidence_ids": ["ev-contact"],
                "observation_id": "obs-contact",
            }
        ],
        "evidence": [
            {
                "id": "ev-contact",
                "source_url": "https://acme.example/",
                "source_class": "company_owned",
                "retrieved_at": "2026-10-05T12:00:00Z",
                "content_sha256": "a" * 64,
                "claim_span": "post@acme.example",
            }
        ],
    }

    projected = project_evaluator_visible_provenance(contract, profile)
    evidence = projected["evidence"][0]

    assert evidence["identity_proof"] == [{"type": "website_identity_gate", "status": "exact"}]
    assert evidence["extraction_method"] == "verified_company_page_same_domain_email_v1"


def test_projects_website_provenance_only_when_url_and_hash_match() -> None:
    profile = _website_profile()
    contract = {
        "organisation_number": "923609016",
        "claims": [
            {
                "field": "official_website",
                "availability": "available",
                "value": "https://acme.example/",
                "evidence_ids": ["ev-site"],
            },
            {
                "field": "company_description",
                "availability": "available",
                "value": "Registry activity text",
                "evidence_ids": ["ev-registry-description"],
            },
        ],
        "evidence": [
            {
                "id": "ev-site",
                "source_url": "https://acme.example/",
                "source_class": "company_owned",
                "retrieved_at": "2026-10-05T12:00:00Z",
                "content_sha256": "a" * 64,
                "claim_span": "Verified company website",
            },
            {
                "id": "ev-registry-description",
                "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
                "source_class": "official",
                "retrieved_at": "2026-10-05T12:00:00Z",
                "content_sha256": "b" * 64,
                "claim_span": "aktivitet=Registry activity text",
            },
        ],
    }

    projected = project_evaluator_visible_provenance(contract, profile)
    evidence = {row["id"]: row for row in projected["evidence"]}

    assert evidence["ev-site"]["identity_proof"]["status"] == "exact"
    assert evidence["ev-site"]["extraction_method"] == "deterministic_name_org_evidence_v4"
    assert "identity_proof" not in evidence["ev-registry-description"]
    assert "extraction_method" not in evidence["ev-registry-description"]


def test_existing_visible_provenance_is_never_overwritten() -> None:
    profile = _website_profile()
    contract = {
        "organisation_number": "923609016",
        "claims": [
            {
                "field": "official_website",
                "availability": "available",
                "value": "https://acme.example/",
                "evidence_ids": ["ev-site"],
            }
        ],
        "evidence": [
            {
                "id": "ev-site",
                "source_url": "https://acme.example/",
                "source_class": "company_owned",
                "retrieved_at": "2026-10-05T12:00:00Z",
                "content_sha256": "a" * 64,
                "claim_span": "Verified company website",
                "identity_proof": {"status": "preexisting"},
                "extraction_method": "preexisting_method",
            }
        ],
    }

    projected = project_evaluator_visible_provenance(contract, profile)
    evidence = projected["evidence"][0]

    assert evidence["identity_proof"] == {"status": "preexisting"}
    assert evidence["extraction_method"] == "preexisting_method"


def test_support_projection_exposes_exact_recipient_provenance() -> None:
    profile = {
        "organisation_number": "923609016",
        "external_observations": [
            {
                "id": "support-1",
                "organisation_number": "923609016",
                "platform": "brreg",
                "signal_type": "official_support_award",
                "source_url": "https://data.brreg.no/stotteregisteret/data",
                "retrieved_at": "2026-10-05T12:00:00Z",
                "content_sha256": "c" * 64,
                "source_snapshot_sha256": "d" * 64,
                "source_row_number": 42,
                "source_row_key": "923609016|2026-09-15|42",
                "exact_entity": True,
                "identity_proof": [
                    {
                        "type": "official_support_primary_recipient_organisation_number",
                        "value": "923609016",
                    }
                ],
                "acquisition_mode": "official_dataset",
                "rights_status": "approved",
                "source_class": "official_support_registry",
                "evidence_span": "Primary recipient organisation number 923609016 received NOK 100000.",
                "effective_at": "2026-09-15",
                "event": {
                    "kind": "support_award",
                    "awarded_at": "2026-09-15",
                    "amount": 100000,
                    "currency": "NOK",
                },
                "strategy": "official_support_registry_primary_recipient_exact_org_v1",
            }
        ],
    }
    contract = {
        "organisation_number": "923609016",
        "claims": [],
        "evidence": [],
    }

    projected = project_support_award_observations(contract, profile)
    evidence = projected["evidence"][0]

    assert evidence["identity_proof"] == profile["external_observations"][0]["identity_proof"]
    assert evidence["extraction_method"] == "official_support_registry_primary_recipient_exact_org_v1"
