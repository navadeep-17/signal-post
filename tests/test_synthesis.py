from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import project_canonical_profile  # noqa: E402
from norway_company_agent.synthesis import build_company_synthesis, validate_company_synthesis  # noqa: E402


def evidence(eid: str) -> dict:
    return {
        "id": eid,
        "source_url": f"https://example.test/{eid}",
        "source_class": "official",
        "retrieved_at": "2026-09-25T10:00:00Z",
        "content_sha256": "a" * 64,
        "claim_span": eid,
    }


def claim(field: str, value, eid: str, **extra) -> dict:
    return {
        "field": field,
        "value": value,
        "availability": "available",
        "confidence": 1.0,
        "evidence_ids": [eid],
        **extra,
    }


def contract() -> dict:
    claims = [
        claim("legal_name", "ACME AS", "ev-reg"),
        claim("municipality", "OSLO", "ev-reg"),
        claim("industry", {"kode": "62.100", "beskrivelse": "Programmeringstjenester"}, "ev-reg"),
        claim("company_description", "ACME builds software for industrial teams.", "ev-web"),
        claim("official_website", "https://acme.no/", "ev-web"),
        claim(
            "financial.revenue",
            12_500_000,
            "ev-fin",
            currency="NOK",
            reporting_period={"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
        ),
        claim(
            "financial.operating_result",
            1_250_000,
            "ev-fin",
            currency="NOK",
            reporting_period={"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
        ),
        claim(
            "roles",
            {"roles": [{"name": "Ada Example", "role_code": "DAGL", "role": "Daglig leder", "inactive": False}]},
            "ev-role",
        ),
        claim(
            "locations",
            {"locations": [{"organisation_number": "999999991", "name": "ACME AS AVD OSLO"}]},
            "ev-loc",
        ),
        claim(
            "external.workforce_snapshot",
            {"measure": "full_time_equivalents", "value": 11, "scope": "company_phrase"},
            "ev-work",
            platform="brreg",
        ),
    ]
    ids = {eid for row in claims for eid in row["evidence_ids"]}
    return {
        "organisation_number": "923609016",
        "run": {"run_id": "v2-synth-test", "started_at": "x", "completed_at": "y", "terminal_status": "completed"},
        "claims": claims,
        "evidence": [evidence(eid) for eid in sorted(ids)],
        "changes": [],
        "errors": [],
        "operations": {"requests": 10, "runtime_ms": 100, "third_party_cost_usd": 0.0},
    }


def projected() -> dict:
    item = project_canonical_profile(contract())
    item["synthesis"] = build_company_synthesis(item)
    return item


def test_synthesis_is_deterministic_zero_network_and_evidence_linked() -> None:
    item = projected()
    synthesis = item["synthesis"]
    assert synthesis["generation"] == {
        "mode": "deterministic_zero_network",
        "llm_used": False,
        "new_facts_created": False,
    }
    assert validate_company_synthesis(item) == []
    available = {row["id"] for row in item["evidence"]}
    assert synthesis["evidence_ids"]
    assert set(synthesis["evidence_ids"]).issubset(available)
    for section in synthesis["sections"]:
        assert section["text"]
        assert set(section["evidence_ids"]).issubset(available)


def test_synthesis_surfaces_description_financial_leadership_location_and_workforce() -> None:
    synthesis = projected()["synthesis"]
    text = " ".join(section["text"] for section in synthesis["sections"])
    assert "ACME builds software for industrial teams." in text
    assert "12,500,000 NOK" in text
    assert "1,250,000 NOK" in text
    assert "Ada Example" in text
    assert "Daglig leder" in text
    assert "Registered workplaces published: 1." in text
    assert "11 full time equivalents" in text
    assert "Verified company website: https://acme.no/." in text


def test_synthesis_does_not_turn_absence_into_activity() -> None:
    synthesis = projected()["synthesis"]
    external = next(section for section in synthesis["sections"] if section["key"] == "external")
    assert "No strict job posting is published for this run." in external["text"]
    assert "No dated company update is published for this run." in external["text"]
    assert "No strict job posting is published." in synthesis["unknowns"]
    assert "No dated company update is published." in synthesis["unknowns"]


def test_synthesis_change_language_comes_only_from_change_contract() -> None:
    item = projected()
    assert item["synthesis"]["what_changed"]["change_count"] == 0
    assert "does not imply that nothing changed" in item["synthesis"]["what_changed"]["text"]

    item["changes"] = [{
        "id": "chg-1",
        "organisation_number": item["organisation_number"],
        "field": "financial.revenue",
        "previous_value": 10_000_000,
        "current_value": 12_500_000,
        "source_url": "https://example.test/change",
        "source_class": "official",
        "retrieved_at": "2026-09-25T10:00:00Z",
        "effective_at": "2025-12-31",
        "previous_content_sha256": "b" * 64,
        "current_content_sha256": "c" * 64,
        "current_status": "available",
    }]
    item["synthesis"] = build_company_synthesis(item)
    assert item["synthesis"]["what_changed"]["change_count"] == 1
    assert "financial.revenue: 10000000 → 12500000" in item["synthesis"]["what_changed"]["text"]
    assert validate_company_synthesis(item) == []


def test_synthesis_validator_rejects_missing_evidence_reference() -> None:
    item = projected()
    item["synthesis"]["sections"][0]["evidence_ids"].append("ev-missing")
    errors = validate_company_synthesis(item)
    assert any("missing evidence" in error for error in errors)
