from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_sgregister_bulk_reach.py"
spec = importlib.util.spec_from_file_location("screen_sgregister_bulk_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _write_source(path: Path) -> None:
    payload = {
        "enterprises": [
            {
                "organizational_number": "123456789",
                "name": "TARGET AS",
                "www": "www.target.example",
                "email": "post@target.example",
                "phone": "11111111",
                "status": {
                    "approved": True,
                    "approval_period_to": "2027-01-01",
                    "approval_certificate": "https://example.test/cert/123456789",
                },
                "valid_approval_areas": [
                    {"function": "Utførende", "subject_area": "Tømrerarbeid", "grade": "2"}
                ],
            },
            {
                "organizational_number": "987654321",
                "name": "OTHER AS",
                "www": None,
                "email": None,
                "phone": "22222222",
                "status": {
                    "approved": True,
                    "approval_period_to": "2025-01-01",
                    "approval_certificate": None,
                },
                "valid_approval_areas": [],
            },
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_parse_source_requires_exact_org_and_extracts_contact(tmp_path: Path) -> None:
    source = tmp_path / "sg.json"
    _write_source(source)
    parsed = module.parse_source(source)
    assert parsed["source_rows"] == 2
    assert parsed["unique_orgs"] == 2
    row = parsed["records"]["123456789"]
    assert row["website"] == "www.target.example"
    assert row["email"] == "post@target.example"
    assert row["phone"] == "11111111"
    assert row["approved"] is True
    assert row["approval_period_to"] == "2027-01-01"
    assert row["approval_areas"][0]["subject_area"] == "Tømrerarbeid"


def test_cohort_metrics_counts_only_exact_matches_and_current_approval(tmp_path: Path) -> None:
    source = tmp_path / "sg.json"
    _write_source(source)
    parsed = module.parse_source(source)
    companies = {
        "123456789": {"organisation_number": "123456789", "website": ""},
        "987654321": {"organisation_number": "987654321", "website": "https://existing.example"},
        "111111111": {"organisation_number": "111111111", "website": ""},
    }
    metrics, hits = module.cohort_metrics(
        companies,
        parsed["records"],
        today=date(2026, 10, 5),
    )
    assert metrics["exact_company_hits"] == 2
    assert metrics["approved_true_companies"] == 2
    assert metrics["approval_current_through_today_companies"] == 1
    assert metrics["website_candidate_companies"] == 1
    assert metrics["email_candidate_companies"] == 1
    assert metrics["phone_candidate_companies"] == 2
    assert metrics["blank_input_website_gains_candidate"] == 1
    assert set(hits) == {"123456789", "987654321"}


def test_parse_source_rejects_wrong_top_level_shape(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text(json.dumps({"enterprise": []}), encoding="utf-8")
    try:
        module.parse_source(source)
    except ValueError as exc:
        assert "enterprises array" in str(exc)
    else:
        raise AssertionError("expected invalid SGregister shape to fail")
