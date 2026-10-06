from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_measurement import compare_company_family_coverage  # noqa: E402


def row(org: str, fields: list[str], *, requests: int = 1) -> dict:
    return {
        "organisation_number": org,
        "run": {"terminal_status": "completed"},
        "claims": [
            {
                "field": field,
                "availability": "available",
                "value": f"value:{field}",
                "evidence_ids": [f"e:{field}"],
            }
            for field in fields
        ],
        "errors": [],
        "operations": {
            "requests": requests,
            "runtime_ms": 10,
            "third_party_cost_usd": 0.0,
        },
    }


def test_compare_reports_company_family_delta_not_raw_claim_delta() -> None:
    baseline = [
        row("111111111", ["official_website"]),
        row("222222222", []),
    ]
    challenger = [
        row("111111111", ["official_website", "external.profile_handle"]),
        row("222222222", ["official_website", "external.contact_email"]),
    ]
    report = compare_company_family_coverage(baseline, challenger)

    assert report["companies"] == 2
    assert report["families"]["verified_website"] == {
        "baseline_companies": 1,
        "challenger_companies": 2,
        "net_new_companies": 1,
        "lost_companies": 0,
    }
    assert report["families"]["social"]["net_new_companies"] == 1
    assert report["families"]["external_contact"]["net_new_companies"] == 1
    assert report["wrong_company_publications"] is None
    assert report["manual_precision_audit_required"] is True
    assert report["baseline"]["conservative_request_charge"] == 4
    assert report["challenger"]["conservative_request_charge"] == 4


def test_compare_rejects_non_identical_cohorts() -> None:
    try:
        compare_company_family_coverage(
            [row("111111111", [])],
            [row("222222222", [])],
        )
    except ValueError as exc:
        assert "organisation sets differ" in str(exc)
    else:
        raise AssertionError("expected ValueError")
