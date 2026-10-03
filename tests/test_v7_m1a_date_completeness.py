from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.synthesis import build_company_synthesis  # noqa: E402


def _evidence(eid: str, **extra) -> dict:
    return {
        "id": eid,
        "source_url": f"https://example.test/{eid}",
        "source_class": "official",
        "retrieved_at": "2026-10-03T06:00:00Z",
        "content_sha256": "a" * 64,
        "claim_span": f"supporting span for {eid}",
        **extra,
    }


def _fact(fact_type: str, value, eid: str, **extra) -> dict:
    return {
        "type": fact_type,
        "canonical_field": f"test.{fact_type}",
        "source_field": f"test_source.{fact_type}",
        "value": value,
        "availability": "available",
        "confidence": 1.0,
        "evidence_ids": [eid],
        **extra,
    }


def _contract() -> dict:
    facts = [
        _fact("company_name", "ACME AS", "ev-name"),
        _fact(
            "workforce_snapshot",
            {"measure": "employees", "value": 11, "scope": "company_phrase"},
            "ev-workforce",
        ),
        _fact(
            "financial_revenue",
            12_500_000,
            "ev-financial",
            currency="NOK",
            reporting_period={"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
        ),
        _fact(
            "company_update",
            {
                "title": "New product launched",
                "url": "https://example.test/news/product",
                "published_date": "2026-09-20",
            },
            "ev-update",
        ),
        _fact(
            "registry_change",
            {
                "event_id": "42",
                "effective_at": "2026-09-30T12:30:00Z",
                "summary": "Registered address changed",
                "changes": [{"field": "address"}],
            },
            "ev-change",
        ),
    ]
    return {
        "organisation_number": "923609016",
        "canonical_facts": facts,
        "canonical_profile": {
            "data_areas": {
                "company_record": True,
                "financials": True,
                "people_and_locations": True,
                "company_website": False,
                "hiring_and_public_activity": True,
            }
        },
        "evidence": [
            _evidence("ev-name"),
            _evidence("ev-workforce", effective_at="2025"),
            _evidence("ev-financial"),
            _evidence("ev-update", effective_at="2026-09-20"),
            _evidence("ev-change", effective_at="2026-09-30T12:30:00Z"),
        ],
        "changes": [],
    }


def _trace_for(synthesis: dict, section: str, evidence_id: str) -> dict:
    return next(
        trace
        for trace in synthesis["decision_brief"][section]["evidence"]
        if trace["evidence_id"] == evidence_id
    )


def test_workforce_trace_recovers_existing_effective_date_from_evidence() -> None:
    synthesis = build_company_synthesis(_contract())
    trace = _trace_for(synthesis, "how_big_is_it", "ev-workforce")

    assert trace["effective_at"] == "2025"
    assert trace["published_date"] is None


def test_dated_update_trace_exposes_publication_date_without_inventing_it() -> None:
    synthesis = build_company_synthesis(_contract())
    trace = _trace_for(synthesis, "digital_footprint", "ev-update")

    assert trace["published_date"] == "2026-09-20"
    assert trace["effective_at"] == "2026-09-20"


def test_registry_change_trace_recovers_nested_effective_date() -> None:
    synthesis = build_company_synthesis(_contract())
    trace = _trace_for(synthesis, "what_changed", "ev-change")

    assert trace["effective_at"] == "2026-09-30T12:30:00Z"
    assert trace["published_date"] is None


def test_financial_reporting_period_is_preserved_and_undated_fact_stays_undated() -> None:
    synthesis = build_company_synthesis(_contract())

    financial = _trace_for(synthesis, "how_big_is_it", "ev-financial")
    assert financial["reporting_period"] == {"fraDato": "2025-01-01", "tilDato": "2025-12-31"}

    company_name = _trace_for(synthesis, "what_is_this_company", "ev-name")
    assert company_name["effective_at"] is None
    assert company_name["published_date"] is None
