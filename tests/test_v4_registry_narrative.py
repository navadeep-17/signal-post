from __future__ import annotations

from copy import deepcopy

import pytest

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection
from norway_company_agent.registry_narrative import project_registry_narrative_claims
from norway_company_agent.synthesis import build_company_synthesis, validate_company_synthesis


def _profile(*, activity: str = "Utvikling av programvare.", purpose: str = "Utvikle og selge programvare.") -> dict:
    return {
        "organisation_number": "123456789",
        "name": "EKSEMPEL AS",
        "evidence": {
            "registry": {
                "status": "available",
                "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
                "retrieved_at": "2026-10-01T00:00:00Z",
                "content_sha256": "a" * 64,
                "source_row_key": "123456789",
                "value": {
                    "organisasjonsnummer": "123456789",
                    "aktivitet": activity,
                    "vedtektsfestetFormaal": purpose,
                },
            }
        },
    }


def _contract() -> dict:
    return {
        "organisation_number": "123456789",
        "claims": [],
        "evidence": [],
        "changes": [],
        "errors": [],
    }


def _claims(row: dict, field: str) -> list[dict]:
    return [claim for claim in row.get("claims") or [] if claim.get("field") == field]


def test_registry_activity_becomes_description_fallback_and_purpose_is_explicit() -> None:
    row = project_registry_narrative_claims(_contract(), _profile())

    descriptions = _claims(row, "company_description")
    purposes = _claims(row, "registered_purpose")
    assert len(descriptions) == 1
    assert descriptions[0]["value"] == "Utvikling av programvare."
    assert descriptions[0]["signal_type"] == "official_registry_narrative_projection"
    assert len(purposes) == 1
    assert purposes[0]["value"] == "Utvikle og selge programvare."

    evidence_by_id = {item["id"]: item for item in row["evidence"]}
    description_evidence = evidence_by_id[descriptions[0]["evidence_ids"][0]]
    assert description_evidence["source_class"] == "official"
    assert description_evidence["source_row_key"] == "123456789"
    assert description_evidence["claim_span"].startswith("aktivitet=")


def test_stronger_description_is_never_replaced() -> None:
    contract = _contract()
    contract["evidence"] = [
        {
            "id": "ev-site",
            "source_url": "https://example.no/",
            "source_class": "company_owned",
            "retrieved_at": "2026-10-01T00:00:00Z",
            "content_sha256": "b" * 64,
            "claim_span": "Company description",
        }
    ]
    contract["claims"] = [
        {
            "field": "company_description",
            "value": "First-party company description.",
            "availability": "available",
            "confidence": 0.99,
            "evidence_ids": ["ev-site"],
            "signal_type": "company_website",
        }
    ]

    row = project_registry_narrative_claims(contract, _profile())

    descriptions = _claims(row, "company_description")
    assert len(descriptions) == 1
    assert descriptions[0]["value"] == "First-party company description."
    assert descriptions[0]["signal_type"] == "company_website"
    assert len(_claims(row, "registered_purpose")) == 1


def test_projection_is_idempotent_and_can_yield_to_later_stronger_description() -> None:
    first = project_registry_narrative_claims(_contract(), _profile())
    second = project_registry_narrative_claims(deepcopy(first), _profile())
    assert second == first

    stronger = deepcopy(first)
    stronger["evidence"].append(
        {
            "id": "ev-report",
            "source_url": "https://example.invalid/report.pdf",
            "source_class": "official",
            "retrieved_at": "2026-10-01T00:00:00Z",
            "content_sha256": "c" * 64,
            "claim_span": "Report description",
        }
    )
    stronger["claims"].append(
        {
            "field": "company_description",
            "value": "Filed annual-report description.",
            "availability": "available",
            "confidence": 1.0,
            "evidence_ids": ["ev-report"],
            "signal_type": "official_annual_report",
        }
    )
    projected = project_registry_narrative_claims(stronger, _profile())
    descriptions = _claims(projected, "company_description")
    assert len(descriptions) == 1
    assert descriptions[0]["value"] == "Filed annual-report description."
    assert all(not item["id"].startswith("ev-v4-registry-narrative-") or item["claim_span"].startswith("vedtektsfestetFormaal=") for item in projected["evidence"])


def test_empty_activity_does_not_promote_purpose_to_description() -> None:
    row = project_registry_narrative_claims(_contract(), _profile(activity="   "))

    assert _claims(row, "company_description") == []
    assert len(_claims(row, "registered_purpose")) == 1


def test_registry_activity_flows_into_existing_canonical_description_and_synthesis() -> None:
    projected = project_registry_narrative_claims(_contract(), _profile())
    canonical = project_canonical_profile(projected)
    assert validate_canonical_projection(canonical) == []

    descriptions = [fact for fact in canonical["canonical_facts"] if fact.get("type") == "company_description"]
    assert len(descriptions) == 1
    assert descriptions[0]["value"] == "Utvikling av programvare."

    canonical["synthesis"] = build_company_synthesis(canonical)
    assert validate_company_synthesis(canonical) == []
    company_section = next(section for section in canonical["synthesis"]["sections"] if section["key"] == "company")
    assert "Utvikling av programvare." in company_section["text"]
    assert descriptions[0]["evidence_ids"][0] in company_section["evidence_ids"]


def test_org_mismatch_is_rejected() -> None:
    profile = _profile()
    contract = _contract()
    contract["organisation_number"] = "987654321"

    with pytest.raises(ValueError, match="organisation number mismatch"):
        project_registry_narrative_claims(contract, profile)
