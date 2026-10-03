from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from summarize_v9_m1c_qualification import summarize


def candidate_row(org: str, *, publishable=True, content_hash="a" * 64):
    return {
        "organisation_number": org,
        "name": f"COMPANY {org} AS",
        "municipality": "OSLO",
        "evidence": {
            "website_model_search_candidate": {
                "status": "available",
                "source_url": f"https://{org}.example.no/",
                "content_sha256": content_hash,
                "value": {
                    "final_url": f"https://{org}.example.no/",
                    "identity_assessment": {
                        "status": "exact",
                        "publishable": publishable,
                        "score": 1.0,
                        "method": "test_exact",
                        "reasons": ["exact organisation proof"],
                    },
                },
            }
        },
    }


def reports(*, verified=5, queried=20, provider_errors=0, cost=0.2):
    cohort = {
        "selected_unresolved": 20,
        "model_or_search_called": False,
        "fresh_cohort_consumed_by_this_step": 40,
    }
    discovery = {
        "queried_unresolved_profiles": queried,
        "counts": {"verified_sites": verified, "provider_errors": provider_errors},
        "operations": {
            "provider_requests": queried,
            "web_search_tool_calls": queried,
            "independent_crawl_requests": verified * 2,
            "estimated_third_party_cost_usd": cost,
        },
        "raw_provider_response_persisted": False,
        "provider_response_text_persisted": False,
        "quarantined_candidate_pages_persisted": False,
    }
    return cohort, discovery


def test_five_verified_is_only_provisional_go_until_manual_audit():
    cohort, discovery = reports(verified=5)
    rows = [candidate_row(str(100000000 + i)) for i in range(5)]
    summary, review = summarize(
        cohort_report=cohort,
        discovery_report=discovery,
        output_rows=rows,
        max_external_cost_usd=0.5,
    )
    assert summary["decision"] == "PROVISIONAL_GO_PENDING_MANUAL_WRONG_COMPANY_AUDIT"
    assert summary["manual_wrong_company_review_required"] is True
    assert len(review) == 5
    assert all(row["manual_wrong_company_review"] == "PENDING" for row in review)


def test_three_to_four_verified_is_hold():
    cohort, discovery = reports(verified=4)
    summary, _ = summarize(
        cohort_report=cohort,
        discovery_report=discovery,
        output_rows=[candidate_row(str(200000000 + i)) for i in range(4)],
        max_external_cost_usd=0.5,
    )
    assert summary["decision"] == "HOLD_PENDING_MANUAL_AUDIT"


def test_below_three_is_no_go():
    cohort, discovery = reports(verified=2)
    summary, _ = summarize(
        cohort_report=cohort,
        discovery_report=discovery,
        output_rows=[candidate_row(str(300000000 + i)) for i in range(2)],
        max_external_cost_usd=0.5,
    )
    assert summary["decision"] == "NO_GO_LOW_YIELD"


def test_provider_error_is_hard_failure():
    cohort, discovery = reports(verified=5, provider_errors=1)
    summary, _ = summarize(
        cohort_report=cohort,
        discovery_report=discovery,
        output_rows=[candidate_row(str(400000000 + i)) for i in range(5)],
        max_external_cost_usd=0.5,
    )
    assert summary["decision"] == "HARD_FAIL"
    assert any("provider_errors" in item for item in summary["hard_failures"])


def test_cost_ceiling_is_hard_failure():
    cohort, discovery = reports(verified=5, cost=0.51)
    summary, _ = summarize(
        cohort_report=cohort,
        discovery_report=discovery,
        output_rows=[candidate_row(str(500000000 + i)) for i in range(5)],
        max_external_cost_usd=0.5,
    )
    assert summary["decision"] == "HARD_FAIL"
    assert summary["cost_within_ceiling"] is False


def test_verified_count_must_match_evidence_rows():
    cohort, discovery = reports(verified=5)
    summary, _ = summarize(
        cohort_report=cohort,
        discovery_report=discovery,
        output_rows=[candidate_row(str(600000000 + i)) for i in range(4)],
        max_external_cost_usd=0.5,
    )
    assert summary["decision"] == "HARD_FAIL"
    assert any("mismatch" in item for item in summary["hard_failures"])


def test_missing_destination_hash_is_hard_failure():
    cohort, discovery = reports(verified=1)
    summary, review = summarize(
        cohort_report=cohort,
        discovery_report=discovery,
        output_rows=[candidate_row("700000000", content_hash="short")],
        max_external_cost_usd=0.5,
    )
    assert summary["decision"] == "HARD_FAIL"
    assert len(review) == 1
    assert any("destination hash" in item for item in summary["hard_failures"])


def test_provider_output_persistence_boundary_is_hard_failure():
    cohort, discovery = reports(verified=0)
    discovery["raw_provider_response_persisted"] = True
    summary, _ = summarize(
        cohort_report=cohort,
        discovery_report=discovery,
        output_rows=[],
        max_external_cost_usd=0.5,
    )
    assert summary["decision"] == "HARD_FAIL"
    assert summary["provider_output_transient"] is False
