from __future__ import annotations

from dataclasses import dataclass
from typing import Any


APPROVED_RIGHTS_STATES = {"approved", "contract_confirmed"}


@dataclass(frozen=True)
class ProviderContract:
    name: str
    evaluator_reproducible: bool
    rights_status: str
    key_available_to_evaluator: bool
    cost_per_search_usd: float
    max_searches: int

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "ProviderContract":
        name = str(value.get("name") or "").strip()
        if not name:
            raise ValueError("provider contract requires a name")
        try:
            cost = float(value.get("cost_per_search_usd"))
        except (TypeError, ValueError) as exc:
            raise ValueError("provider cost_per_search_usd must be numeric") from exc
        try:
            max_searches = int(value.get("max_searches"))
        except (TypeError, ValueError) as exc:
            raise ValueError("provider max_searches must be an integer") from exc
        if cost < 0:
            raise ValueError("provider cost_per_search_usd cannot be negative")
        if max_searches < 1:
            raise ValueError("provider max_searches must be positive")
        return cls(
            name=name,
            evaluator_reproducible=bool(value.get("evaluator_reproducible")),
            rights_status=str(value.get("rights_status") or "").strip().casefold(),
            key_available_to_evaluator=bool(value.get("key_available_to_evaluator")),
            cost_per_search_usd=cost,
            max_searches=max_searches,
        )


def evaluate_provider_contract(
    contract: ProviderContract,
    *,
    challenge_cost_budget_usd: float,
) -> dict[str, Any]:
    """Decide whether a search provider may leave the experimental boundary.

    The V9 plan requires evaluator reproducibility plus an explicit provider/key/cost/rights
    contract before search can be wired into a production candidate. This function does
    not approve any provider by itself; it merely enforces that all required declarations
    are present and within the supplied challenge budget.
    """
    if challenge_cost_budget_usd < 0:
        raise ValueError("challenge_cost_budget_usd cannot be negative")

    reasons: list[str] = []
    if not contract.evaluator_reproducible:
        reasons.append("provider_not_evaluator_reproducible")
    if contract.rights_status not in APPROVED_RIGHTS_STATES:
        reasons.append("provider_rights_not_confirmed")
    if not contract.key_available_to_evaluator:
        reasons.append("provider_key_not_available_to_evaluator")

    projected_cost = round(contract.cost_per_search_usd * contract.max_searches, 6)
    if projected_cost > challenge_cost_budget_usd:
        reasons.append("projected_provider_cost_exceeds_budget")

    allowed = not reasons
    return {
        "provider": contract.name,
        "allowed_for_live_v9_experiment": allowed,
        "allowed_for_production_candidate": False,
        "rights_status": contract.rights_status,
        "evaluator_reproducible": contract.evaluator_reproducible,
        "key_available_to_evaluator": contract.key_available_to_evaluator,
        "cost_per_search_usd": contract.cost_per_search_usd,
        "max_searches": contract.max_searches,
        "projected_provider_cost_usd": projected_cost,
        "challenge_cost_budget_usd": challenge_cost_budget_usd,
        "reasons": reasons,
        "note": (
            "Passing this gate only permits a bounded experiment. Production still requires "
            "consumed/dev transfer, zero wrong-company publications, complete evidence, "
            "a re-proved request theorem, and an explicit promotion decision."
        ),
    }
