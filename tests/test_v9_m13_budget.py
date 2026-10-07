from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_m13_budget import allocate_m13_search_budget  # noqa: E402


def test_zero_search_reproduces_frozen_100_company_final_runner_allocation() -> None:
    r = allocate_m13_search_budget(
        expected_count=100,
        max_challenge_requests=1996,
        max_search_calls=0,
    )
    assert r["base_theoretical_logical_request_ceiling"] == 901
    assert r["provider_search_logical_request_ceiling"] == 0
    assert r["annual_report_workforce_logical_request_ceiling"] == 97
    assert r["theoretical_logical_request_ceiling"] == 998
    assert r["theoretical_challenge_request_charge_ceiling"] == 1996


def test_twenty_search_calls_trade_exactly_twenty_annual_slots_at_100() -> None:
    r = allocate_m13_search_budget(
        expected_count=100,
        max_challenge_requests=1996,
        max_search_calls=20,
    )
    assert r["provider_search_logical_request_ceiling"] == 20
    assert r["provider_search_conservative_charge_ceiling"] == 40
    assert r["annual_report_workforce_logical_request_ceiling"] == 77
    assert r["theoretical_logical_request_ceiling"] == 998
    assert r["theoretical_challenge_request_charge_ceiling"] == 1996
    assert r["candidate_fetch_additional_site_slots"] == 0


def test_ninety_seven_search_calls_fit_only_by_zeroing_annual_slots() -> None:
    r = allocate_m13_search_budget(
        expected_count=100,
        max_challenge_requests=1996,
        max_search_calls=97,
    )
    assert r["provider_search_logical_request_ceiling"] == 97
    assert r["annual_report_workforce_logical_request_ceiling"] == 0
    assert r["theoretical_challenge_request_charge_ceiling"] == 1996


def test_search_budget_above_company_count_is_clamped_to_batch_size() -> None:
    r = allocate_m13_search_budget(
        expected_count=20,
        max_challenge_requests=1996,
        max_search_calls=100,
    )
    assert r["provider_search_logical_request_ceiling"] == 20
    assert r["annual_report_workforce_logical_request_ceiling"] == 20
    assert r["theoretical_challenge_request_charge_ceiling"] == 442


def test_negative_search_calls_fail_closed() -> None:
    try:
        allocate_m13_search_budget(
            expected_count=100,
            max_challenge_requests=1996,
            max_search_calls=-1,
        )
    except ValueError as exc:
        assert "cannot be negative" in str(exc)
    else:
        raise AssertionError("negative search budget must fail")


def test_structurally_impossible_search_reservation_fails_closed() -> None:
    try:
        allocate_m13_search_budget(
            expected_count=100,
            max_challenge_requests=1802,
            max_search_calls=1,
        )
    except ValueError as exc:
        assert "cannot fit" in str(exc)
    else:
        raise AssertionError("provider search must not exceed the structural request cap")
