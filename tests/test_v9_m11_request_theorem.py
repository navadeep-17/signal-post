from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _preflight():
    file = ROOT / "scripts" / "prove_v9_m11_budget.py"
    spec = importlib.util.spec_from_file_location("v9_m11_theorem_preflight", file)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_a_20_reproduces_exact_frozen_406_request_theorem() -> None:
    result = _preflight().prove_structural_ceiling(20)
    assert result["official_logical_ceiling"] == 100
    assert result["site_logical_ceiling"] == 80
    assert result["wikidata_logical_ceiling"] == 1
    assert result["annual_workforce_logical_ceiling"] == 20
    assert result["change_feed_logical_ceiling"] == 1
    assert result["support_registry_logical_ceiling"] == 1
    assert result["theoretical_conservative_request_charge_ceiling"] == 406
    assert result["unallocated_conservative_request_charge"] == 1594
    assert result["decision"] == "STATIC_THEOREM_PREFLIGHT_ONLY"


def test_gate_b_100_reserves_change_and_support_inside_2000_request_theorem() -> None:
    result = _preflight().prove_structural_ceiling(100)
    assert result["official_logical_ceiling"] == 500
    assert result["site_logical_ceiling"] == 400
    assert result["wikidata_logical_ceiling"] == 1
    assert result["change_feed_logical_ceiling"] == 1
    assert result["support_registry_logical_ceiling"] == 1
    assert result["annual_workforce_logical_ceiling"] == 97
    assert result["theoretical_logical_request_ceiling"] == 1000
    assert result["theoretical_conservative_request_charge_ceiling"] == 2000
    assert result["unallocated_conservative_request_charge"] == 0
    assert result["fresh_qualification_authorized"] is False
    assert result["production_promotion_authorized"] is False


def test_every_supported_shard_size_is_bounded_and_reports_all_charges() -> None:
    proof = _preflight()
    previous = 0
    for n in range(1, 101):
        result = proof.prove_structural_ceiling(n)
        logical = sum(result[k] for k in (
            "official_logical_ceiling",
            "site_logical_ceiling",
            "wikidata_logical_ceiling",
            "annual_workforce_logical_ceiling",
            "change_feed_logical_ceiling",
            "support_registry_logical_ceiling",
        ))
        assert logical == result["theoretical_logical_request_ceiling"]
        charge = logical * result["charge_multiplier"]
        assert charge == result["theoretical_conservative_request_charge_ceiling"]
        assert previous <= charge <= 2000
        assert result["max_redirects_per_logical_attempt"] == 1
        assert result["annual_workforce_logical_ceiling"] <= n
        previous = charge


@pytest.mark.parametrize("bad_count", [0, -1, 101, 150])
def test_outside_one_shard_is_not_silently_treated_as_one_100_company_shard(
    bad_count: int,
) -> None:
    with pytest.raises(ValueError, match="1..100"):
        _preflight().prove_structural_ceiling(bad_count)
