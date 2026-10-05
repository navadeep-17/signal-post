from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_q7_consumed_transfer import (  # noqa: E402
    apply_current_zero_network_provenance,
    build_transfer_report,
)
from norway_company_agent.support_contract import (  # noqa: E402
    SUPPORT_AWARD_EXTRACTION_METHOD,
    SUPPORT_AWARD_SOURCE_URL,
)


def _evidence(evidence_id: str, *, source_url: str = "https://example.no/") -> dict:
    return {
        "id": evidence_id,
        "source_url": source_url,
        "retrieved_at": "2026-10-05T12:00:00Z",
        "claim_span": "bounded evidence span",
        "content_sha256": "a" * 64,
        "identity_proof": {"publishable": True, "status": "exact"},
        "extraction_method": "test_fixture",
    }


def _claim(field: str, value, evidence_id: str) -> dict:
    return {
        "field": field,
        "value": value,
        "availability": "available",
        "confidence": 1.0,
        "evidence_ids": [evidence_id],
    }


def _row(org: str, claims: list[dict], evidence: list[dict]) -> dict:
    return {
        "organisation_number": org,
        "claims": claims,
        "evidence": evidence,
    }


def _run_report(requests: int) -> dict:
    return {
        "passed": True,
        "request_budget": {
            "observed_conservative_challenge_request_charge": requests,
            "theoretical_challenge_request_charge_ceiling": 2000,
        },
        "runtime": {"wall_runtime_seconds": 100},
        "source_policy": {"third_party_cost_usd": 0.0},
    }


def test_q7_reports_company_and_claim_details_for_feed_activity_gain() -> None:
    website_ev = _evidence("ev-website")
    update_ev = _evidence("ev-feed", source_url="https://example.no/feed/")
    baseline = [
        _row(
            "900000001",
            [_claim("official_website", "https://example.no/", "ev-website")],
            [website_ev],
        )
    ]
    candidate = [
        _row(
            "900000001",
            [
                _claim("official_website", "https://example.no/", "ev-website"),
                _claim(
                    "external.company_update",
                    {
                        "title": "Company opens new office",
                        "url": "https://example.no/news/new-office",
                        "published_date": "2026-10-05",
                    },
                    "ev-feed",
                ),
            ],
            [website_ev, update_ev],
        )
    ]

    report = build_transfer_report(
        baseline,
        _run_report(100),
        candidate,
        _run_report(102),
    )

    assert report["fresh_qualification"] is False
    assert report["companies"] == 1
    assert report["coverage"]["candidate"]["external.company_update"] == 1
    assert report["coverage"]["delta"]["external.company_update"] == 1
    assert report["coverage"]["company_level_changes"]["external.company_update"] == {
        "gained_organisations": ["900000001"],
        "lost_organisations": [],
    }
    assert report["claim_delta"]["added_by_field"] == {"external.company_update": 1}
    assert report["claim_delta"]["removed_claims"] == 0
    detail = report["claim_delta"]["added_claim_details"][0]
    assert detail["organisation_number"] == "900000001"
    assert detail["field"] == "external.company_update"
    assert detail["value"]["published_date"] == "2026-10-05"
    assert report["evidence_visibility"]["candidate"]["core_evidence_complete_claims"] == 2
    assert report["run_metrics"]["candidate"]["observed_conservative_requests"] == 102


def test_q7_requires_identical_consumed_company_set() -> None:
    baseline = [_row("900000001", [], [])]
    candidate = [_row("900000002", [], [])]

    try:
        build_transfer_report(baseline, _run_report(10), candidate, _run_report(10))
    except ValueError as exc:
        assert "organisation sets differ" in str(exc)
    else:
        raise AssertionError("expected consumed-set mismatch to be rejected")


def test_q7_surfaces_known_wrong_company_publications() -> None:
    row = _row(
        "825188592",
        [
            _claim(
                "official_website",
                "https://interiorkupp.no/",
                "ev-wrong",
            )
        ],
        [_evidence("ev-wrong", source_url="https://interiorkupp.no/")],
    )

    report = build_transfer_report(
        [row],
        _run_report(10),
        [row],
        _run_report(10),
        forbidden_map={"825188592": ["interiorkupp.no"]},
    )

    assert report["known_wrong_company_publications"] == [
        {
            "organisation_number": "825188592",
            "field": "official_website",
            "forbidden_text": "interiorkupp.no",
        }
    ]


def test_q7_claim_delta_detects_regressions_and_exact_removed_detail() -> None:
    ev = _evidence("ev-social")
    baseline = [
        _row(
            "900000001",
            [_claim("external.profile_handle", "https://linkedin.com/company/example", "ev-social")],
            [ev],
        )
    ]
    candidate = [_row("900000001", [], [])]

    report = build_transfer_report(
        baseline,
        _run_report(10),
        candidate,
        _run_report(10),
    )

    assert report["coverage"]["delta"]["external.profile_handle"] == -1
    assert report["claim_delta"]["removed_by_field"] == {"external.profile_handle": 1}
    assert report["claim_delta"]["removed_claim_details"] == [
        {
            "organisation_number": "900000001",
            "field": "external.profile_handle",
            "value": "https://linkedin.com/company/example",
            "count": 1,
        }
    ]


def _legacy_support_row() -> dict:
    return {
        "organisation_number": "917403376",
        "claims": [
            {
                "field": "official.support_award",
                "value": {
                    "kind": "support_award",
                    "awarded_at": "2026-09-16",
                    "amount": "42500",
                    "currency": "NOK",
                },
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-support-existing"],
                "platform": "brreg",
                "signal_type": "official_support_award",
                "claim_scope": "official_recipient_support_event",
            }
        ],
        "evidence": [
            {
                "id": "ev-support-existing",
                "source_url": SUPPORT_AWARD_SOURCE_URL,
                "source_class": "official",
                "retrieved_at": "2026-10-05T12:00:00Z",
                "content_sha256": "a" * 64,
                "source_row_key": "1000295424",
                "claim_span": "recipient org: 917403376; award date: 2026-09-16",
                "identity_proof": "Støtteregisteret primary recipient organisation number equals target 917403376",
            }
        ],
    }


def test_q7_current_main_normalization_adds_only_merged_support_provenance() -> None:
    original = _legacy_support_row()

    normalized, summary = apply_current_zero_network_provenance([original])

    assert original["evidence"][0].get("extraction_method") is None
    assert normalized[0]["claims"] == original["claims"]
    assert normalized[0]["evidence"][0]["id"] == original["evidence"][0]["id"]
    assert normalized[0]["evidence"][0]["content_sha256"] == original["evidence"][0]["content_sha256"]
    assert normalized[0]["evidence"][0]["extraction_method"] == SUPPORT_AWARD_EXTRACTION_METHOD
    assert summary["network_requests_added"] == 0
    assert summary["claim_semantics_changed"] is False
    assert summary["support_evidence_rows_with_method_added"] == 1
    assert summary["organisations_changed"] == ["917403376"]


def test_q7_transfer_can_measure_candidate_after_current_main_provenance_normalization() -> None:
    baseline = [_legacy_support_row()]
    candidate = [_legacy_support_row()]

    report = build_transfer_report(
        baseline,
        _run_report(10),
        candidate,
        _run_report(10),
        apply_current_provenance=True,
    )

    assert report["candidate_zero_network_normalization"]["support_evidence_rows_with_method_added"] == 1
    candidate_evidence = report["evidence_visibility"]["candidate"]
    assert candidate_evidence["identity_sensitive_claims"] == 1
    assert candidate_evidence["identity_proof_visible"] == 1
    assert candidate_evidence["extraction_method_visible"] == 1
    assert report["evidence_visibility"]["candidate_issue_count"] == 0
