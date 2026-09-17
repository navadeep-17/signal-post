from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_submission_prototype.py"
spec = importlib.util.spec_from_file_location("build_submission_prototype", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def sample_row() -> dict:
    return {
        "organisation_number": "123456789",
        "run": {
            "run_id": "test-run",
            "started_at": "2026-09-17T00:00:00Z",
            "completed_at": "2026-09-17T00:00:01Z",
            "terminal_status": "completed",
        },
        "claims": [
            {
                "field": "legal_name",
                "value": "Example AS",
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-reg"],
            },
            {
                "field": "legal_form",
                "value": "AS",
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-reg"],
            },
            {
                "field": "municipality",
                "value": "OSLO",
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-reg"],
            },
            {
                "field": "latest_submitted_accounts",
                "value": "2025",
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-reg"],
            },
            {
                "field": "official_website",
                "value": None,
                "availability": "not_available",
                "confidence": 1.0,
                "evidence_ids": [],
            },
            {
                "field": "financial.revenue",
                "value": 123,
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-fin"],
                "currency": "NOK",
                "reporting_period": {"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
            },
            {
                "field": "external.workforce_snapshot",
                "value": {"value": 4, "measure": "full_time_equivalents"},
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-work"],
                "claim_scope": "Official company-scope workforce phrase.",
            },
            {
                "field": "external.contact_email",
                "value": "hello@example.no",
                "availability": "available",
                "confidence": 0.99,
                "evidence_ids": ["ev-site"],
            },
            {
                "field": "external.profile_handle",
                "value": "https://www.linkedin.com/company/example",
                "availability": "available",
                "confidence": 0.99,
                "evidence_ids": ["ev-site"],
                "platform": "linkedin",
            },
        ],
        "evidence": [
            {
                "id": "ev-reg",
                "source_url": "https://data.brreg.no/example",
                "source_class": "official",
                "retrieved_at": "2026-09-17T00:00:00Z",
                "content_sha256": "a" * 64,
                "claim_span": "Example AS 123456789",
            },
            {
                "id": "ev-fin",
                "source_url": "https://data.brreg.no/accounts",
                "source_class": "official",
                "retrieved_at": "2026-09-17T00:00:00Z",
                "content_sha256": "b" * 64,
                "claim_span": "revenue=123",
            },
            {
                "id": "ev-work",
                "source_url": "https://data.brreg.no/report.pdf",
                "source_class": "official",
                "retrieved_at": "2026-09-17T00:00:00Z",
                "effective_at": "2025",
                "content_sha256": "c" * 64,
                "claim_span": "4 årsverk",
            },
            {
                "id": "ev-site",
                "source_url": "https://example.no/",
                "source_class": "company_owned",
                "retrieved_at": "2026-09-17T00:00:00Z",
                "content_sha256": "d" * 64,
                "claim_span": "hello@example.no",
            },
        ],
        "changes": [],
        "errors": [],
        "operations": {
            "requests": 4,
            "runtime_ms": 1000,
            "third_party_cost_usd": 0.0,
        },
    }


def test_compact_profile_preserves_claim_boundaries_and_deduplicates_evidence() -> None:
    profile = module.compact_profile(sample_row())
    assert profile["name"] == "Example AS"
    assert profile["website"]["availability"] == "not_available"
    assert profile["website"]["value"] is None
    assert profile["workforce"]["meta"]["effectiveAt"] == "2025"
    assert profile["contacts"][0]["value"] == "hello@example.no"
    assert profile["handles"][0]["platform"] == "linkedin"
    assert len(profile["evidence"]) == 4


def test_html_has_submission_boundary_and_mobile_overflow_guards() -> None:
    output = module.build_html([sample_row()])
    assert "Company intelligence you can trace back to evidence." in output
    assert "no reviews, buzz, sentiment" in output
    assert "Not published" in output
    assert ".panel,.shell>*{min-width:0;max-width:100%}" in output
    assert "table{width:100%;table-layout:fixed" in output
    assert "code{word-break:break-all" in output
    assert "Experimental external evidence" not in output
    assert "exact LinkedIn profiles" not in output
