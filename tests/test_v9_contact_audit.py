from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_contact_audit import audit_zero_request_contacts  # noqa: E402


def ev(eid: str, *, url: str = "https://example.no/") -> dict:
    return {
        "id": eid,
        "source_url": url,
        "retrieved_at": "2026-10-06T00:00:00Z",
        "content_sha256": "a" * 64,
        "claim_span": "fixture",
    }


def claim(field: str, value: str, eid: str) -> dict:
    return {
        "field": field,
        "availability": "available",
        "value": value,
        "confidence": 0.99,
        "evidence_ids": [eid],
        "claim_scope": "fixture",
    }


def row(org: str, claims: list[dict], evidence: list[dict]) -> dict:
    return {
        "organisation_number": org,
        "claims": claims,
        "evidence": evidence,
    }


def test_reports_new_email_and_phone_without_counting_raw_duplicates() -> None:
    baseline = [row("111111111", [], [])]
    challenger = [
        row(
            "111111111",
            [
                claim("external.contact_email", "post@example.no", "e1"),
                claim("external.contact_phone", "+4798765432", "e2"),
            ],
            [ev("e1"), ev("e2")],
        )
    ]
    report = audit_zero_request_contacts(baseline, challenger)
    assert report["new_contact_publications"] == 2
    assert report["lost_contact_publications"] == 0
    assert report["fields"]["external.contact_email"]["net_new_companies"] == 1
    assert report["fields"]["external.contact_phone"]["net_new_companies"] == 1
    assert report["all_new_evidence_complete"] is True
    assert report["network_requests_added_by_feature"] == 0


def test_existing_contact_loss_is_explicit_failure_material() -> None:
    baseline = [
        row(
            "111111111",
            [claim("external.contact_email", "post@example.no", "e1")],
            [ev("e1")],
        )
    ]
    challenger = [row("111111111", [], [])]
    report = audit_zero_request_contacts(baseline, challenger)
    assert report["lost_contact_publications"] == 1
    assert report["fields"]["external.contact_email"]["lost_companies"] == 1


def test_new_contact_without_complete_evidence_is_not_marked_complete() -> None:
    broken = ev("e1")
    broken["content_sha256"] = ""
    report = audit_zero_request_contacts(
        [row("111111111", [], [])],
        [
            row(
                "111111111",
                [claim("external.contact_email", "post@example.no", "e1")],
                [broken],
            )
        ],
    )
    assert report["new_contact_publications"] == 1
    assert report["all_new_evidence_complete"] is False


def test_rejects_mismatched_company_sets() -> None:
    try:
        audit_zero_request_contacts(
            [row("111111111", [], [])],
            [row("222222222", [], [])],
        )
    except ValueError as exc:
        assert "organisation sets differ" in str(exc)
    else:
        raise AssertionError("expected ValueError")
