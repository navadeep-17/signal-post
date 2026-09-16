from __future__ import annotations

import ast
from pathlib import Path

from norway_company_agent.run_budget import RunBudget


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_signalpost_final.py"


def _runner_source() -> str:
    return RUNNER.read_text(encoding="utf-8")


def _constant(name: str):
    tree = ast.parse(_runner_source())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"constant {name!r} not found")


def test_default_100_company_budget_is_official_2000_envelope() -> None:
    assert _constant("DEFAULT_MAX_CHALLENGE_REQUESTS") == 2000

    budget = RunBudget(
        max_challenge_requests=2000,
        max_third_party_cost_usd=0.0,
        max_wall_runtime_seconds=2400,
        max_redirects_per_logical_request=1,
    )
    # Current qualified base theorem: 100 * 9 per-profile logical requests
    # plus one shared Wikidata batch = 901 logical requests = 1,802 charge.
    base_logical = 901
    remaining_charge = budget.max_challenge_requests - budget.charge_requests(base_logical)
    annual_slots = remaining_charge // budget.request_charge_multiplier
    assert budget.charge_requests(base_logical) == 1802
    assert annual_slots == 99
    assert budget.charge_requests(base_logical + annual_slots) == 2000


def test_transient_h2g_execution_errors_are_reported_not_batch_fatal() -> None:
    source = _runner_source()
    # Production reports connector execution errors for auditability, but a source
    # failure must leave that company as an abstention rather than invalidate all
    # otherwise-terminal company outputs.
    assert '"execution_errors": list(annual_workforce_report.get("execution_errors") or [])' in source
    assert '"annual_workforce_execution_clean"' not in source
