from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import project_canonical_profile  # noqa: E402
from norway_company_agent.output_contract import project_terminal_envelope, validate_contract_object  # noqa: E402


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


def _contract() -> dict:
    profile = {
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
    envelope = {
        "run_id": "v2-registry-test",
        "organisation_number": "923609016",
        "state": "complete",
        "started_at": "2026-09-25T12:00:00Z",
        "completed_at": "2026-09-25T12:00:01Z",
        "profile": profile,
    }
    return project_terminal_envelope(envelope)


def _claims(item: dict) -> dict[str, dict]:
    return {claim["field"]: claim for claim in item["claims"]}


def _facts(item: dict) -> dict[str, dict]:
    return {fact["canonical_field"]: fact for fact in item["canonical_facts"]}


def test_registry_fields_are_not_lost_between_bulk_profile_and_output_contract() -> None:
    item = _contract()
    assert validate_contract_object(item) == []
    claims = _claims(item)

    assert claims["industry"]["value"] == {
        "code": "62.100",
        "description": "Programmeringstjenester",
    }
    assert claims["municipality_number"]["value"] == "0301"
    assert claims["bankrupt"]["value"] is False
    assert claims["liquidating"]["value"] is False


def test_registry_fields_project_to_explicit_canonical_company_fields() -> None:
    projected = project_canonical_profile(_contract())
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
