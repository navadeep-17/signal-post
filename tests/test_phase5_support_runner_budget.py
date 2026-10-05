from importlib import util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.brreg_changes import theoretical_change_feed_requests  # noqa: E402
from norway_company_agent.run_budget import RunBudget  # noqa: E402
from norway_company_agent.wikidata_discovery import theoretical_wikidata_lookup_requests  # noqa: E402


def _load_script(name: str, filename: str):
    spec = util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v1_theorem(expected_count: int, max_requests: int) -> dict[str, int]:
    v1 = _load_script("signalpost_final_runner_phase5", "run_signalpost_final.py")
    budget = RunBudget(max_challenge_requests=max_requests)
    per_profile = v1.OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE + v1.MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    wikidata = theoretical_wikidata_lookup_requests(expected_count)
    fixed = expected_count * per_profile + wikidata
    fixed_charge = budget.charge_requests(fixed)
    annual = min(
        expected_count,
        max(0, (max_requests - fixed_charge) // budget.request_charge_multiplier),
    )
    theoretical = fixed + annual
    return {
        "wikidata": wikidata,
        "fixed": fixed,
        "annual": annual,
        "theoretical": theoretical,
        "charge": budget.charge_requests(theoretical),
    }


def _v8_combined_theorem(expected_count: int = 100) -> dict[str, int]:
    v8 = _load_script("signalpost_v8_phase5", "run_signalpost_v8.py")
    v7 = _load_script("signalpost_v7_phase5", "run_signalpost_v7.py")
    v2 = _load_script("signalpost_v2_phase5", "run_signalpost_v2.py")

    max_requests = v8.default_request_budget(expected_count)
    prepared, v7_settings = v7.prepare_legacy_args(
        [
            "--output",
            "out/final.jsonl",
            "--report",
            "out/report.json",
            "--product-output",
            "out/product.html",
            "--expected-count",
            str(expected_count),
            "--max-challenge-requests",
            str(max_requests),
        ]
    )
    assert prepared
    v2_max_requests = int(v7_settings["legacy_max_challenge_requests"])
    support_charge = int(v7_settings["support_request_charge_ceiling"])

    change_requests = theoretical_change_feed_requests(expected_count)
    change_charge = change_requests * v2.SHARED_REQUEST_CHARGE_MULTIPLIER
    v1_max_requests = v2_max_requests - change_charge
    v1 = _v1_theorem(expected_count, v1_max_requests)
    return {
        "max_requests": max_requests,
        "support_charge": support_charge,
        "v2_max_requests": v2_max_requests,
        "change_requests": change_requests,
        "change_charge": change_charge,
        "v1_max_requests": v1_max_requests,
        "v1_annual": v1["annual"],
        "v1_theoretical": v1["theoretical"],
        "v1_charge": v1["charge"],
        "combined_logical": v1["theoretical"] + change_requests + v7.SUPPORT_REGISTRY_SHARED_REQUEST_CEILING,
        "combined_charge": v1["charge"] + change_charge + support_charge,
    }


def test_certified_v1_remains_support_unaware_and_immutable_layer() -> None:
    v1 = _load_script("signalpost_final_runner_phase5_immutable", "run_signalpost_final.py")
    assert not hasattr(v1, "fetch_support_award_batch")
    assert not hasattr(v1, "project_support_award_observations")
    assert not hasattr(v1, "SUPPORT_REGISTRY_SHARED_REQUEST_CEILING")


def test_v7_wrapper_owns_support_fetch_projection_and_reservation() -> None:
    v7 = _load_script("signalpost_v7_phase5_owner", "run_signalpost_v7.py")
    assert callable(v7.fetch_support_award_batch)
    assert callable(v7.project_support_award_observations)
    assert v7.SUPPORT_REGISTRY_SHARED_REQUEST_CEILING == 1
    assert v7.DEFAULT_SUPPORT_LOOKBACK_DAYS == 365
    assert v7.DEFAULT_SUPPORT_EVENTS_PER_COMPANY == 5


def test_v7_reserves_one_shared_support_request_before_calling_v2() -> None:
    v7 = _load_script("signalpost_v7_phase5_reservation", "run_signalpost_v7.py")
    prepared, settings = v7.prepare_legacy_args(
        [
            "--output",
            "out/final.jsonl",
            "--report",
            "out/report.json",
            "--product-output",
            "out/product.html",
            "--max-challenge-requests",
            "2000",
            "--support-registry-timeout",
            "123",
            "--support-lookback-days=365",
            "--support-events-per-company",
            "5",
        ]
    )
    assert settings["legacy_max_challenge_requests"] == 1998
    assert settings["support_request_charge_ceiling"] == 2
    assert "--support-registry-timeout" not in prepared
    assert not any(arg.startswith("--support-lookback-days") for arg in prepared)
    assert "--support-events-per-company" not in prepared


def test_v7_support_canonical_fact_counter_uses_canonical_field() -> None:
    v7 = _load_script("signalpost_v7_phase5_canonical_counter", "run_signalpost_v7.py")
    rows = [
        {
            "canonical_facts": [
                {
                    "type": "support_award",
                    "canonical_field": "public.official_support_award",
                },
                {
                    "type": "registry_change",
                    "canonical_field": "public.official_registry_change",
                },
            ]
        }
    ]
    assert v7._support_canonical_fact_count(rows) == 1


def test_actual_v8_path_reserves_support_then_change_feed_and_stays_at_2000() -> None:
    result = _v8_combined_theorem(100)
    assert result == {
        "max_requests": 2000,
        "support_charge": 2,
        "v2_max_requests": 1998,
        "change_requests": 1,
        "change_charge": 2,
        "v1_max_requests": 1996,
        "v1_annual": 97,
        "v1_theoretical": 998,
        "v1_charge": 1996,
        "combined_logical": 1000,
        "combined_charge": 2000,
    }


def test_actual_v8_path_never_exceeds_dynamic_budget() -> None:
    for expected_count in (1, 20, 100, 1200):
        result = _v8_combined_theorem(expected_count)
        assert result["combined_charge"] <= result["max_requests"]
