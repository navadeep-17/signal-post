from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.evidence_visibility import audit_contract_item, audit_contract_rows  # noqa: E402


def _evidence(**overrides):
    item = {
        "id": "ev-1",
        "source_url": "https://company.example/about",
        "source_class": "company_owned",
        "retrieved_at": "2026-10-05T12:00:00Z",
        "content_sha256": "a" * 64,
        "claim_span": "ACME AS, organisation number 923609016",
        "identity_proof": "Exact organisation number on the verified company page.",
        "extraction_method": "first_party_html",
    }
    item.update(overrides)
    return item


def _item(*, field="official_website", evidence=None):
    return {
        "organisation_number": "923609016",
        "claims": [
            {
                "field": field,
                "value": "https://company.example/",
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-1"],
            }
        ],
        "evidence": [evidence or _evidence()],
    }


def test_complete_company_owned_trace_is_visible() -> None:
    report = audit_contract_item(_item())
    claim = report["claims"][0]

    assert claim["core_evidence_complete"] is True
    assert claim["reopenable_source"] is True
    assert claim["identity_sensitive_claim"] is True
    assert claim["identity_proof_visible"] is True
    assert claim["extraction_method_visible"] is True
    assert claim["missing_external_trace"] == []


def test_missing_content_hash_is_reported_as_core_gap() -> None:
    report = audit_contract_item(_item(evidence=_evidence(content_sha256=None)))

    assert report["claims"][0]["core_evidence_complete"] is False
    assert report["claims"][0]["missing_core_evidence"] == ["content_sha256"]


def test_malformed_content_hash_is_reported_as_core_gap() -> None:
    report = audit_contract_item(_item(evidence=_evidence(content_sha256="not-a-sha256")))

    assert report["claims"][0]["core_evidence_complete"] is False
    assert report["claims"][0]["missing_core_evidence"] == ["content_sha256"]


def test_company_owned_trace_reports_hidden_identity_and_extraction_metadata() -> None:
    report = audit_contract_item(
        _item(evidence=_evidence(identity_proof=None, extraction_method=None))
    )

    assert report["claims"][0]["missing_external_trace"] == [
        "identity_proof",
        "extraction_method",
    ]


def test_official_registry_claim_does_not_require_company_site_identity_trace() -> None:
    evidence = _evidence(
        source_url="https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
        source_class="official",
        identity_proof=None,
        extraction_method=None,
    )
    report = audit_contract_item(_item(field="legal_name", evidence=evidence))

    assert report["claims"][0]["identity_sensitive_claim"] is False
    assert report["claims"][0]["missing_external_trace"] == []


def test_official_support_claim_is_identity_sensitive() -> None:
    evidence = _evidence(
        source_url="https://data.brreg.no/stotteregisteret/",
        source_class="official",
        identity_proof=None,
        extraction_method=None,
    )
    report = audit_contract_item(_item(field="official.support_award", evidence=evidence))

    assert report["claims"][0]["identity_sensitive_claim"] is True
    assert report["claims"][0]["missing_external_trace"] == [
        "identity_proof",
        "extraction_method",
    ]


def test_aggregate_report_counts_field_level_visibility_and_issues() -> None:
    complete = _item()
    incomplete = _item(evidence=_evidence(identity_proof=None, extraction_method=None))
    incomplete["organisation_number"] = "923609017"

    report = audit_contract_rows([complete, incomplete])

    assert report["companies"] == 2
    assert report["available_claims"] == 2
    assert report["core_evidence_complete_claims"] == 2
    assert report["identity_sensitive_claims"] == 2
    assert report["identity_proof_visible"] == 1
    assert report["extraction_method_visible"] == 1
    assert report["by_field"]["official_website"]["available_claims"] == 2
    assert report["by_field"]["official_website"]["identity_proof_visible"] == 1
    assert report["issues"] == [
        {
            "organisation_number": "923609017",
            "field": "official_website",
            "missing": ["extraction_method", "identity_proof"],
        }
    ]
