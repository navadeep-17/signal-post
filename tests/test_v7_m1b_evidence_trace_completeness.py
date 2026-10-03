from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.synthesis import build_company_synthesis, validate_company_synthesis  # noqa: E402


def _item() -> dict:
    item = {
        "organisation_number": "923609016",
        "canonical_facts": [
            {
                "type": "company_name",
                "canonical_field": "company.legal_name",
                "source_field": "legal_name",
                "value": "ACME AS",
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-name"],
            }
        ],
        "canonical_profile": {
            "data_areas": {
                "company_record": True,
                "financials": False,
                "people_and_locations": False,
                "company_website": False,
                "hiring_and_public_activity": False,
            }
        },
        "evidence": [
            {
                "id": "ev-name",
                "source_url": "https://example.test/company",
                "source_class": "official",
                "retrieved_at": "2026-10-03T06:00:00Z",
                "content_sha256": "a" * 64,
                "claim_span": "legal_name=ACME AS",
            }
        ],
        "changes": [],
    }
    item["synthesis"] = build_company_synthesis(item)
    return item


def _trace(item: dict) -> dict:
    return item["synthesis"]["decision_brief"]["what_is_this_company"]["evidence"][0]


def test_complete_decision_trace_validates() -> None:
    item = _item()

    assert validate_company_synthesis(item) == []


@pytest.mark.parametrize("field", ["source_url", "retrieved_at", "claim_span"])
def test_validator_rejects_missing_required_trace_metadata(field: str) -> None:
    item = _item()
    _trace(item)[field] = None

    errors = validate_company_synthesis(item)

    assert f"trace missing {field}" in "\n".join(errors)


def test_validator_rejects_trace_metadata_that_does_not_match_backing_evidence() -> None:
    item = _item()
    _trace(item)["source_url"] = "https://wrong.example/"

    errors = validate_company_synthesis(item)

    assert "trace source_url mismatch" in "\n".join(errors)


def test_validator_rejects_hash_mismatch_when_backing_evidence_has_hash() -> None:
    item = _item()
    _trace(item)["content_sha256"] = "b" * 64

    errors = validate_company_synthesis(item)

    assert "trace content_sha256 mismatch" in "\n".join(errors)


def test_hash_is_not_invented_when_backing_evidence_has_no_hash() -> None:
    item = _item()
    item["evidence"][0]["content_sha256"] = None
    item["synthesis"] = build_company_synthesis(item)

    assert _trace(item)["content_sha256"] is None
    assert validate_company_synthesis(item) == []
