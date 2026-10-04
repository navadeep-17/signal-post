from __future__ import annotations

from copy import deepcopy
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


def _registry_live_record() -> dict:
    return {
        "status": "available",
        "source_type": "official_registry_live",
        "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
        "retrieved_at": "2026-10-04T04:00:00Z",
        "content_sha256": "b" * 64,
        "value": {
            "organisation_number": "923609016",
            "industry": {"kode": "62.100", "beskrivelse": "Programmeringstjenester"},
            "business_address": {"kommune": "OSLO", "kommunenummer": "0301"},
            "bankrupt": False,
            "liquidating": False,
        },
    }


def _profile() -> dict:
    # The bulk/profile fields intentionally conflict with registry_live. C12 requires the
    # evaluator-facing additional official claims to follow the exact retained live response.
    return {
        "organisation_number": "923609016",
        "name": "ACME AS",
        "legal_form": "AS",
        "employees": 12,
        "municipality": "BERGEN",
        "municipality_number": "9999",
        "industry_code": "00.000",
        "industry_label": "WRONG BULK VALUE",
        "bankrupt": True,
        "liquidating": True,
        "latest_submitted_accounts": "2025",
        "evidence": {
            "registry": _registry_record(),
            "registry_live": _registry_live_record(),
        },
        "run_metrics": {"requests": 0, "latencies_ms": [], "third_party_cost_usd": 0.0},
    }


def _base_contract(profile: dict | None = None) -> dict:
    profile = profile or _profile()
    envelope = {
        "run_id": "v2-registry-test",
        "organisation_number": "923609016",
        "state": "complete",
        "started_at": "2026-09-25T12:00:00Z",
        "completed_at": "2026-09-25T12:00:01Z",
        "profile": profile,
    }
    return project_terminal_envelope(envelope)


def _v2_contract(profile: dict | None = None) -> dict:
    profile = profile or _profile()
    return project_v2_registry_claims(_base_contract(profile), profile)


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
    assert "industry" not in claims


def test_v2_registry_projection_uses_exact_registry_live_values_not_bulk_profile() -> None:
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
    assert all(
        claims[field]["signal_type"] == "official_registry_live_projection"
        for field in ("industry", "municipality_number", "bankrupt", "liquidating")
    )


def test_v2_registry_evidence_points_to_exact_live_response_and_source_path() -> None:
    item = _v2_contract()
    claims = _claims(item)
    evidence = {row["id"]: row for row in item["evidence"]}

    expected_paths = {
        "industry": "/naeringskode1",
        "municipality_number": "/forretningsadresse/kommunenummer",
        "bankrupt": "/konkurs",
        "liquidating": "/underAvvikling",
    }
    for field, path in expected_paths.items():
        row = evidence[claims[field]["evidence_ids"][0]]
        assert row["source_url"].endswith("/enheter/923609016")
        assert row["content_sha256"] == "b" * 64
        assert row["source_row_key"] == "923609016"
        assert row["source_field"] == path
        assert row["claim_span"].startswith(path + "=")


def test_missing_exact_live_field_is_marked_not_available_never_filled_from_bulk() -> None:
    profile = deepcopy(_profile())
    del profile["evidence"]["registry_live"]["value"]["bankrupt"]
    profile["bankrupt"] = True

    item = _v2_contract(profile)
    claim = _claims(item)["bankrupt"]
    assert claim["availability"] == "not_available"
    assert claim["value"] is None
    assert claim["signal_type"] == "official_registry_live_projection"


def test_failed_registry_live_source_withholds_v2_additional_fields() -> None:
    profile = deepcopy(_profile())
    profile["evidence"]["registry_live"] = {
        "status": "source_error",
        "source_type": "official_registry_live",
        "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
        "retrieved_at": "2026-10-04T04:00:00Z",
        "content_sha256": "c" * 64,
        "value": None,
    }
    item = _v2_contract(profile)
    claims = _claims(item)
    for field in ("industry", "municipality_number", "bankrupt", "liquidating"):
        assert field not in claims


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
