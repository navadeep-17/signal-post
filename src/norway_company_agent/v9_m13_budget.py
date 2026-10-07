from __future__ import annotations

from typing import Any

from .final_site_discovery import MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
from .run_budget import RunBudget
from .wikidata_discovery import theoretical_wikidata_lookup_requests

OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE = 5


def allocate_m13_search_budget(
    *,
    expected_count: int,
    max_challenge_requests: int,
    max_search_calls: int,
    request_charge_multiplier: int = 2,
) -> dict[str, Any]:
    """Reserve provider search before allocating bounded annual-report attempts.

    The provider candidate fetch does not add a site slot: M13 is allowed only as a
    replacement for H1g's existing final two logical site requests. Therefore the only
    new structural logical request is one Responses API request per possible search call.
    """
    if expected_count < 1:
        raise ValueError("expected_count must be positive")
    if max_challenge_requests < 1:
        raise ValueError("max_challenge_requests must be positive")
    if max_search_calls < 0:
        raise ValueError("max_search_calls cannot be negative")
    if request_charge_multiplier != 2:
        raise ValueError("M13 theorem is pinned to the existing one-redirect conservative multiplier")

    budget = RunBudget(
        max_challenge_requests=max_challenge_requests,
        max_redirects_per_logical_request=request_charge_multiplier - 1,
    )
    provider_search_ceiling = min(expected_count, max_search_calls)
    per_profile_logical_ceiling = (
        OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE + MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    )
    shared_wikidata = theoretical_wikidata_lookup_requests(expected_count)
    base_logical = expected_count * per_profile_logical_ceiling + shared_wikidata
    base_charge = budget.charge_requests(base_logical)
    provider_charge = budget.charge_requests(provider_search_ceiling)
    structural_charge = base_charge + provider_charge
    if structural_charge > max_challenge_requests:
        raise ValueError(
            "M13 base + provider search cannot fit inside supplied final-run request budget"
        )

    remaining_charge = max_challenge_requests - structural_charge
    annual = min(
        expected_count,
        max(0, remaining_charge // budget.request_charge_multiplier),
    )
    total_logical = base_logical + provider_search_ceiling + annual
    total_charge = budget.charge_requests(total_logical)
    if total_charge > max_challenge_requests:
        raise AssertionError("M13 structural allocation exceeded request budget")

    return {
        "expected_count": expected_count,
        "official_logical_requests_per_profile_ceiling": OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE,
        "site_logical_requests_per_profile_ceiling": MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
        "shared_wikidata_logical_request_ceiling": shared_wikidata,
        "base_theoretical_logical_request_ceiling": base_logical,
        "base_theoretical_conservative_charge_ceiling": base_charge,
        "provider_search_logical_request_ceiling": provider_search_ceiling,
        "provider_search_conservative_charge_ceiling": provider_charge,
        "annual_report_workforce_logical_request_ceiling": annual,
        "theoretical_logical_request_ceiling": total_logical,
        "theoretical_challenge_request_charge_ceiling": total_charge,
        "max_challenge_requests": max_challenge_requests,
        "unallocated_conservative_request_charge": max_challenge_requests - total_charge,
        "candidate_fetch_additional_site_slots": 0,
        "candidate_fetch_policy": "replaces existing H1g final two-logical-request site slot",
    }
