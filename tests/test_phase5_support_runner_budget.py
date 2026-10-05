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


def _load_runner():
    return _load_script("signalpost_final_runner_phase5", "run_signalpost_final.py")


def _support_aware_theorem(expected_count: int, max_requests: int = 2000) -> dict[str, int]:
    runner = _load_runner()
    budget = RunBudget(max_challenge_requests=max_requests)
    per_profile_logical_ceiling = runner.OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE + runner.MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    wikidata = theoretical_wikidata_lookup_requests(expected_count)
    support = runner.SUPPORT_REGISTRY_SHARED_REQUEST_CEILING
    fixed = expected_count * per_profile_logical_ceiling + wikidata + support
    fixed_charge = budget.charge_requests(fixed)
    remaining = max_requests - fixed_charge
    annual = min(expected_count, max(0, remaining // budget.request_charge_multiplier))
    theoretical = fixed + annual
    return {
        "wikidata": wikidata,
        "support": support,
        "fixed": fixed,
        "annual": annual,
        "theoretical": theoretical,
        "charge": budget.charge_requests(theoretical),
    }


def _v8_combined_theorem(expected_count: int = 100) -> dict[str, int]:
    v8 = _load_script("signalpost_v8_phase5", "run_signalpost_v8.py")
    v2 = _load_script("signalpost_v2_phase5", "run_signalpost_v2.py")
    max_requests = v8.default_request_budget(expected_count)
    change_requests = theoretical_change_feed_requests(expected_count)
    change_charge = change_requests * v2.SHARED_REQUEST_CHARGE_MULTIPLIER
    base_max_requests = max_requests - change_charge
    final = _support_aware_theorem(expected_count, base_max_requests)
    return {
        "max_requests": max_requests,
        "change_requests": change_requests,
        "change_charge": change_charge,
        "base_max_requests": base_max_requests,
        "final_annual": final["annual"],
        "final_theoretical": final["theoretical"],
        "final_charge": final["charge"],
        "combined_logical": final["theoretical"] + change_requests,
        "combined_charge": final["charge"] + change_charge,
    }


def test_patched_runner_imports_support_source_and_projection():
    runner = _load_runner()
    assert callable(runner.fetch_support_award_batch)
    assert callable(runner.project_support_award_observations)
    assert runner.SUPPORT_REGISTRY_SHARED_REQUEST_CEILING == 1
    assert runner.DEFAULT_SUPPORT_LOOKBACK_DAYS == 365
    assert runner.DEFAULT_SUPPORT_EVENTS_PER_COMPANY == 5


def test_direct_final_support_dataset_reserves_one_shared_request_and_98_h2g_slots_for_100():
    result = _support_aware_theorem(100)
    assert result == {
        "wikidata": 1,
        "support": 1,
        "fixed": 902,
        "annual": 98,
        "theoretical": 1000,
        "charge": 2000,
    }


def test_direct_final_support_dataset_does_not_raise_challenge_request_cap():
    result = _support_aware_theorem(100)
    assert result["charge"] <= 2000


def test_direct_final_support_dataset_costs_only_one_h2g_slot_vs_pre_support_theorem():
    runner = _load_runner()
    budget = RunBudget(max_challenge_requests=2000)
    per_profile = runner.OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE + runner.MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    base = 100 * per_profile + theoretical_wikidata_lookup_requests(100)
    pre_support_annual = (2000 - budget.charge_requests(base)) // budget.request_charge_multiplier
    post_support_annual = _support_aware_theorem(100)["annual"]
    assert pre_support_annual == 99
    assert post_support_annual == 98


def test_actual_v8_path_reserves_change_feed_then_support_and_stays_at_2000():
    result = _v8_combined_theorem(100)
    assert result == {
        "max_requests": 2000,
        "change_requests": 1,
        "change_charge": 2,
        "base_max_requests": 1998,
        "final_annual": 97,
        "final_theoretical": 999,
        "final_charge": 1998,
        "combined_logical": 1000,
        "combined_charge": 2000,
    }


def test_actual_v8_path_never_exceeds_default_per_company_budget():
    for expected_count in (1, 20, 100):
        result = _v8_combined_theorem(expected_count)
        assert result["combined_charge"] <= result["max_requests"]
