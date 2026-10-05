from __future__ import annotations

from norway_company_agent.evidence_visibility import audit_contract_item
from norway_company_agent.support_contract import (
    SUPPORT_AWARD_EXTRACTION_METHOD,
    project_support_award_observations,
)


def _support_observation() -> dict:
    return {
        "id": "support-award-test",
        "organisation_number": "917403376",
        "platform": "brreg",
        "signal_type": "official_support_award",
        "source_class": "official_support_registry",
        "source_url": "https://stotte.brreg.no/nb/oppslag/stoettetildeling/totalbestand/csv",
        "retrieved_at": "2026-10-05T12:00:00Z",
        "content_sha256": "a" * 64,
        "source_snapshot_sha256": "b" * 64,
        "source_row_number": 2,
        "source_row_key": "1000295424",
        "exact_entity": True,
        "identity_proof": "Støtteregisteret primary recipient organisation number equals target 917403376",
        "acquisition_mode": "official_dataset",
        "rights_status": "approved",
        "rights_basis": "NLOD",
        "evidence_span": "recipient org: 917403376; award date: 2026-09-16; awarded amount: 42500 NOK",
        "effective_at": "2026-09-16",
        "event": {
            "kind": "support_award",
            "awarded_at": "2026-09-16",
            "amount": "42500",
            "currency": "NOK",
        },
    }


def test_support_award_exposes_deterministic_extraction_method_without_changing_claim() -> None:
    observation = _support_observation()
    profile = {
        "organisation_number": "917403376",
        "external_observations": [observation],
    }
    contract = {"organisation_number": "917403376", "claims": [], "evidence": []}

    projected = project_support_award_observations(contract, profile)

    assert len(projected["claims"]) == 1
    claim = projected["claims"][0]
    assert claim["field"] == "official.support_award"
    assert claim["value"] == observation["event"]
    assert claim["confidence"] == 1.0
    assert claim["availability"] == "available"

    assert len(projected["evidence"]) == 1
    evidence = projected["evidence"][0]
    assert evidence["content_sha256"] == observation["content_sha256"]
    assert evidence["source_url"] == observation["source_url"]
    assert evidence["identity_proof"] == observation["identity_proof"]
    assert evidence["extraction_method"] == SUPPORT_AWARD_EXTRACTION_METHOD

    visibility = audit_contract_item(projected)
    assert visibility["available_claims"] == 1
    audited_claim = visibility["claims"][0]
    assert audited_claim["core_evidence_complete"] is True
    assert audited_claim["identity_proof_visible"] is True
    assert audited_claim["extraction_method_visible"] is True
    assert audited_claim["missing_external_trace"] == []


def test_support_projection_remains_idempotent_with_extraction_method() -> None:
    observation = _support_observation()
    profile = {
        "organisation_number": "917403376",
        "external_observations": [observation],
    }
    contract = {"organisation_number": "917403376", "claims": [], "evidence": []}

    once = project_support_award_observations(contract, profile)
    twice = project_support_award_observations(once, profile)

    assert twice == once
