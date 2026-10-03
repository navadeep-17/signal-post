from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import project_canonical_profile  # noqa: E402
from norway_company_agent.synthesis import build_company_synthesis, validate_company_synthesis  # noqa: E402


def _evidence(eid: str, *, retrieved_at: str = "2026-10-03T06:00:00Z") -> dict:
    return {
        "id": eid,
        "source_url": f"https://example.test/{eid}",
        "source_class": "official",
        "retrieved_at": retrieved_at,
        "content_sha256": "a" * 64,
        "claim_span": f"supporting span for {eid}",
    }


def _claim(field: str, value, eid: str, **extra) -> dict:
    return {
        "field": field,
        "value": value,
        "availability": "available",
        "confidence": 1.0,
        "evidence_ids": [eid],
        **extra,
    }


def _projected() -> dict:
    claims = [
        _claim("legal_name", "ACME AS", "ev-reg"),
        _claim("municipality", "OSLO", "ev-reg"),
        _claim("industry", {"kode": "62.100", "beskrivelse": "Programmeringstjenester"}, "ev-reg"),
        _claim("company_description", "ACME builds software for industrial teams.", "ev-desc"),
        _claim("official_website", "https://acme.no/", "ev-web"),
        _claim(
            "financial.revenue",
            12_500_000,
            "ev-fin",
            currency="NOK",
            reporting_period={"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
        ),
        _claim(
            "roles",
            {"roles": [{"name": "Ada Example", "role_code": "DAGL", "role": "Daglig leder", "inactive": False}]},
            "ev-role",
        ),
        _claim(
            "external.workforce_snapshot",
            {"measure": "employees", "value": 11, "scope": "company_phrase"},
            "ev-work",
            platform="brreg",
        ),
    ]
    ids = {eid for row in claims for eid in row["evidence_ids"]}
    contract = {
        "organisation_number": "923609016",
        "run": {"run_id": "v7-synth-test", "started_at": "x", "completed_at": "y", "terminal_status": "completed"},
        "claims": claims,
        "evidence": [_evidence(eid) for eid in sorted(ids)],
        "changes": [],
        "errors": [],
        "operations": {"requests": 0, "runtime_ms": 1, "third_party_cost_usd": 0.0},
    }
    item = project_canonical_profile(contract)
    item["synthesis"] = build_company_synthesis(item)
    return item


def test_decision_brief_exposes_all_evaluator_oriented_sections() -> None:
    item = _projected()
    brief = item["synthesis"]["decision_brief"]

    assert set(brief) == {
        "what_is_this_company",
        "what_does_it_do",
        "how_big_is_it",
        "who_runs_it",
        "hiring",
        "digital_footprint",
        "what_changed",
        "what_is_unknown",
    }
    assert "ACME AS" in brief["what_is_this_company"]["text"]
    assert "ACME builds software" in brief["what_does_it_do"]["text"]
    assert "12,500,000 nok" in brief["how_big_is_it"]["text"].casefold()
    assert "Ada Example" in brief["who_runs_it"]["text"]
    assert "No strict job posting" in brief["hiring"]["text"]
    assert "https://acme.no/" in brief["digital_footprint"]["text"]
    assert validate_company_synthesis(item) == []


def test_positive_decision_claims_expose_source_retrieval_date_and_span() -> None:
    item = _projected()
    brief = item["synthesis"]["decision_brief"]

    traces = [
        trace
        for key in (
            "what_is_this_company",
            "what_does_it_do",
            "how_big_is_it",
            "who_runs_it",
            "digital_footprint",
        )
        for trace in brief[key]["evidence"]
    ]
    assert traces
    for trace in traces:
        assert trace["evidence_id"]
        assert trace["source_url"].startswith("https://example.test/")
        assert trace["retrieved_at"] == "2026-10-03T06:00:00Z"
        assert trace["claim_span"].startswith("supporting span")
        assert trace["content_sha256"] == "a" * 64

    financial_trace = next(
        trace
        for trace in brief["how_big_is_it"]["evidence"]
        if trace["evidence_id"] == "ev-fin"
    )
    assert financial_trace["reporting_period"]["tilDato"] == "2025-12-31"


def test_unknowns_are_explicit_without_creating_negative_company_facts() -> None:
    item = _projected()
    brief = item["synthesis"]["decision_brief"]

    assert "No strict job posting is published." in brief["what_is_unknown"]
    assert "No dated company update is published." in brief["what_is_unknown"]
    assert brief["hiring"]["evidence"] == []
    assert "No strict job posting is published for this run." == brief["hiring"]["text"]


def test_validator_rejects_broken_decision_brief_evidence_reference() -> None:
    item = _projected()
    item["synthesis"]["decision_brief"]["what_does_it_do"]["evidence"].append(
        {"evidence_id": "missing-evidence"}
    )

    errors = validate_company_synthesis(item)
    assert any("decision_brief references missing evidence" in error for error in errors)
