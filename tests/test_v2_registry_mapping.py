from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import project_canonical_profile  # noqa: E402
from norway_company_agent.output_contract import project_terminal_envelope, validate_contract_object  # noqa: E402
from norway_company_agent.v2_registry_projection import project_v2_registry_claims  # noqa: E402


def _registry_record() -> dict:
    return {
        "status": "available",
        "source_type": "official_registry_bulk",
        "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
        "retrieved_at": "2026-09-25T12:00:00Z",
        "content_sha256": "a" * 64,
        "source_row_key": "923609016",
        "value": {"organisasjonsnummer": "923609016"},
    }


def _profile() -> dict:
    return {
        "organisation_number": "923609016",
        "name": "ACME AS",
        "legal_form": "AS",
        "employees": 12,
        "municipality": "OSLO",
        "municipality_number": "0301",
        "industry_code": "62.100",
        "industry_label": "Programmeringstjenester",
        "bankrupt": False,
        "liquidating": False,
        "latest_submitted_accounts": "2025",
        "evidence": {"registry": _registry_record()},
        "run_metrics": {"requests": 0, "latencies_ms": [], "third_party_cost_usd": 0.0},
    }


def _base_contract() -> dict:
    profile = _profile()
    envelope = {
        "run_id": "v2-registry-test",
        "organisation_number": "923609016",
        "state": "complete",
        "started_at": "2026-09-25T12:00:00Z",
        "completed_at": "2026-09-25T12:00:01Z",
        "profile": profile,
    }
    return project_terminal_envelope(envelope)


def _v2_contract() -> dict:
    return project_v2_registry_claims(_base_contract(), _profile())


def _claims(item: dict) -> dict[str, dict]:
    return {claim["field"]: claim for claim in item["claims"]}


def _facts(item: dict) -> dict[str, dict]:
    return {fact["canonical_field"]: fact for fact in item["canonical_facts"]}


def test_v1_adapter_remains_unchanged_and_does_not_gain_v2_registry_fields() -> None:
    item = _base_contract()
    assert validate_contract_object(item) == []
    claims = _claims(item)
    assert "municipality_number" not in claims
    assert "bankrupt" not in claims
    assert "liquidating" not in claims
    # The historical adapter only publishes profile['industry']; this fixture intentionally
    # uses the real bulk profile's industry_code/industry_label representation instead.
    assert "industry" not in claims


def test_v2_registry_projection_recovers_exact_official_fields() -> None:
    item = _v2_contract()
    assert validate_contract_object(item) == []
    claims = _claims(item)

    assert claims["industry"]["value"] == {
        "code": "62.100",
        "description": "Programmeringstjenester",
    }
    assert claims["municipality_number"]["value"] == "0301"
    assert claims["bankrupt"]["value"] is False
    assert claims["liquidating"]["value"] is False
    assert all(claims[field]["confidence"] == 1.0 for field in ("industry", "municipality_number", "bankrupt", "liquidating"))


def test_v2_registry_fields_project_to_explicit_canonical_company_fields() -> None:
    projected = project_canonical_profile(_v2_contract())
    facts = _facts(projected)

    assert facts["company.industry"]["value"]["code"] == "62.100"
    assert facts["company.municipality_number"]["value"] == "0301"
    assert facts["company.bankrupt"]["value"] is False
    assert facts["company.liquidating"]["value"] is False
    for field in (
        "company.industry",
        "company.municipality_number",
        "company.bankrupt",
        "company.liquidating",
    ):
        assert facts[field]["evidence_ids"]
        assert facts[field]["source_field"]


def test_v2_registry_projection_is_idempotent() -> None:
    once = _v2_contract()
    twice = project_v2_registry_claims(once, _profile())
    assert twice == once
