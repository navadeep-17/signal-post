from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_activity_audit import audit_dated_first_party_activity  # noqa: E402


def ev(eid: str, *, source_url: str = "https://example.no/news/update/", retrieved_at: str = "2026-10-06T10:00:00Z", span: str = "Example update; published date 2026-09-20; date evidence jsonld_newsarticle_date_published: 2026-09-20") -> dict:
    return {
        "id": eid,
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "content_sha256": "a" * 64,
        "claim_span": span,
    }


def update_claim(*, url: str = "https://example.no/news/update/", published_date: str = "2026-09-20", eid: str = "e1") -> dict:
    return {
        "field": "external.company_update",
        "availability": "available",
        "value": {
            "title": "Example launches new service",
            "url": url,
            "published_date": published_date,
        },
        "confidence": 0.99,
        "evidence_ids": [eid],
    }


def row(org: str, claims: list[dict], evidence: list[dict]) -> dict:
    return {"organisation_number": org, "claims": claims, "evidence": evidence}


def test_new_structured_update_requires_page_local_complete_nonfuture_evidence() -> None:
    report = audit_dated_first_party_activity(
        [row("111111111", [], [])],
        [row("111111111", [update_claim()], [ev("e1")])],
    )
    assert report["audit_error_count"] == 0
    assert report["net_new_dated_activity_companies"] == 1
    assert report["new_update_publications"] == 1
    assert report["new_updates_with_structured_jsonld_date_evidence"] == 1
    assert report["manual_audit_rows"][0]["page_local_evidence"] is True
    assert report["network_requests_added_by_m6_extraction"] == 0


def test_cross_page_hash_scope_is_rejected() -> None:
    report = audit_dated_first_party_activity(
        [row("111111111", [], [])],
        [
            row(
                "111111111",
                [update_claim()],
                [ev("e1", source_url="https://example.no/")],
            )
        ],
    )
    assert report["audit_error_count"] == 1
    assert "own page URL" in report["audit_errors"][0]["error"]


def test_future_publication_date_is_rejected() -> None:
    report = audit_dated_first_party_activity(
        [row("111111111", [], [])],
        [
            row(
                "111111111",
                [update_claim(published_date="2026-10-07")],
                [ev("e1", retrieved_at="2026-10-06T10:00:00Z")],
            )
        ],
    )
    assert report["audit_error_count"] == 1
    assert "future" in report["audit_errors"][0]["error"]


def test_lost_existing_update_is_reported() -> None:
    baseline = [row("111111111", [update_claim()], [ev("e1")])]
    challenger = [row("111111111", [], [])]
    report = audit_dated_first_party_activity(baseline, challenger)
    assert report["lost_update_publications"] == 1
    assert report["lost_dated_activity_companies"] == 1


def test_company_sets_must_match() -> None:
    try:
        audit_dated_first_party_activity(
            [row("111111111", [], [])],
            [row("222222222", [], [])],
        )
    except ValueError as exc:
        assert "organisation sets differ" in str(exc)
    else:
        raise AssertionError("expected ValueError")
