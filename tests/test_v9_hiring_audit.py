from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_hiring_audit import audit_hiring_semantics  # noqa: E402


def ev(eid: str) -> dict:
    return {
        "id": eid,
        "source_url": "https://example.no/",
        "retrieved_at": "2026-10-06T00:00:00Z",
        "content_sha256": "a" * 64,
        "claim_span": "We are hiring engineers.",
    }


def claim(field: str, value, eid: str, scope: str) -> dict:
    return {
        "field": field,
        "availability": "available",
        "value": value,
        "confidence": 0.98,
        "evidence_ids": [eid],
        "claim_scope": scope,
    }


def row(org: str, claims: list[dict], evidence: list[dict]) -> dict:
    return {
        "organisation_number": org,
        "claims": claims,
        "evidence": evidence,
    }


def test_audit_accepts_separate_intent_and_strict_job_shapes() -> None:
    baseline = [row("111111111", [], [])]
    challenger = [
        row(
            "111111111",
            [
                claim(
                    "external.hiring_intent",
                    {"match_type": "en_we_are_hiring", "source_url": "https://example.no/"},
                    "e1",
                    "Company-authored recruitment intent. This is not a claim that a specific vacancy is currently open.",
                ),
                claim(
                    "external.job_posting",
                    {
                        "title": "Software Engineer",
                        "url": "https://example.no/jobs/software-engineer",
                        "application_url": "https://example.no/jobs/software-engineer/apply",
                        "deadline": "2026-11-01",
                    },
                    "e2",
                    "Specific current role with employer match and application path.",
                ),
            ],
            [ev("e1"), ev("e2")],
        )
    ]
    report = audit_hiring_semantics(baseline, challenger)
    assert report["semantic_error_count"] == 0
    assert report["new_intent_or_job_publications"] == 2
    assert report["fields"]["external.hiring_intent"]["net_new_companies"] == 1
    assert report["fields"]["external.job_posting"]["net_new_companies"] == 1
    assert report["network_requests_added_by_projection"] == 0


def test_intent_without_explicit_vacancy_boundary_is_rejected() -> None:
    report = audit_hiring_semantics(
        [row("111111111", [], [])],
        [
            row(
                "111111111",
                [
                    claim(
                        "external.hiring_intent",
                        {"match_type": "en_we_are_hiring"},
                        "e1",
                        "We are hiring.",
                    )
                ],
                [ev("e1")],
            )
        ],
    )
    assert report["semantic_error_count"] == 1
    assert "vacancy boundary" in report["semantic_errors"][0]["error"]


def test_job_without_application_shape_is_rejected() -> None:
    report = audit_hiring_semantics(
        [row("111111111", [], [])],
        [
            row(
                "111111111",
                [
                    claim(
                        "external.job_posting",
                        {"title": "Engineer", "url": "https://example.no/jobs/1", "deadline": "2026-11-01"},
                        "e1",
                        "Specific current role.",
                    )
                ],
                [ev("e1")],
            )
        ],
    )
    assert report["semantic_error_count"] == 1
    assert "title/url/application/deadline" in report["semantic_errors"][0]["error"]


def test_lost_careers_surface_is_not_silently_accepted() -> None:
    baseline = [
        row(
            "111111111",
            [
                claim(
                    "external.careers_page",
                    {"url": "https://example.no/careers"},
                    "e1",
                    "Careers surface only.",
                )
            ],
            [ev("e1")],
        )
    ]
    challenger = [row("111111111", [], [])]
    report = audit_hiring_semantics(baseline, challenger)
    assert report["semantic_error_count"] == 1
    assert report["fields"]["external.careers_page"]["lost_companies"] == 1
