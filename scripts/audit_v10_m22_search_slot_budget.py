#!/usr/bin/env python3
"""M22 offline request-slot feasibility screen; not an API connector.

This proves only conservative *request accounting* for hypothetical one-search
first-party-domain nomination. It proves neither legal access nor recall,
precision, throughput, wall time, nor publication qualification.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

COMPANIES = 100
OFFICIAL_PER_COMPANY = 5
SITE_PER_COMPANY = 4
SHARED_WIKIDATA = 1
ANNUAL_WORKFORCE_RESERVED = 97
BRREG_CHANGES_SHARED = 1
SUPPORT_REGISTER_SHARED = 1
CHARGE_MULTIPLIER = 2
REQUEST_LIMIT = 2000
RUNTIME_LIMIT_SECONDS = 2400

# The search route must consume EXISTING site slots, never add a new family.
# One search + one bounded robots/homepage fetch = 1+2 logical requests.
SEARCH = 1
CRAWL = 2
H1C_CRAWL = 2
SECONDARY = 2
REGISTRY_SEED_CRAWL = 2


def charge(logical: int) -> int:
    assert logical >= 0
    return CHARGE_MULTIPLIER * logical


def capped_sequence(actions: tuple[tuple[str, int], ...]) -> dict:
    used = 0
    executed: list[str] = []
    skipped: list[str] = []
    for name, cost in actions:
        if used + cost <= SITE_PER_COMPANY:
            used += cost
            executed.append(name)
        else:
            skipped.append(name)
    assert used <= SITE_PER_COMPANY
    return {"logical": used, "executed": executed, "skipped": skipped}


def enumerate_scenarios() -> list[dict]:
    """Completely enumerate specified normal/failed candidate control paths."""
    cases: list[dict] = []
    # Prior registry or email domain exists: leave current source priority in
    # place; do not run search after its expensive unsuccessful crawl.
    for existing_seed, seed_qualifies, needs_secondary in itertools.product(
        (False, True), (False, True), (False, True)
    ):
        if existing_seed:
            steps = [("registry_or_email_candidate_crawl", REGISTRY_SEED_CRAWL)]
            if seed_qualifies:
                if needs_secondary:
                    steps.append(("optional_site_activity", SECONDARY))
            else:
                steps.append(("h1c_fallback", H1C_CRAWL))
                if needs_secondary:
                    steps.append(("h1c_secondary", SECONDARY))
            variant = "existing_seed_priority_no_search"
        else:
            # With no registry/email seed, search FIRST instead of running
            # the deterministic H1c and H1g guesses unconditionally.
            steps = [("provider_search", SEARCH)]
            if seed_qualifies:
                steps.append(("independently_fetch_provider_candidate", CRAWL))
                if needs_secondary:
                    # Candidate can only publish on homepage-level proof;
                    # any secondary requiring two more requests abstains.
                    steps.append(("provider_candidate_secondary", SECONDARY))
            else:
                steps.append(("h1c_fallback_if_search_no_candidate", H1C_CRAWL))
                if needs_secondary:
                    steps.append(("h1c_secondary", SECONDARY))
            variant = "search_first_fallback_to_h1c"
        allocated = capped_sequence(tuple(steps))
        cases.append({
            "variant": variant,
            "existing_seed": existing_seed,
            "candidate_accepted": seed_qualifies,
            "secondary_requested": needs_secondary,
            **allocated,
        })
    return cases


def make_report() -> dict:
    per_company = OFFICIAL_PER_COMPANY + SITE_PER_COMPANY
    shared = SHARED_WIKIDATA + ANNUAL_WORKFORCE_RESERVED + BRREG_CHANGES_SHARED + SUPPORT_REGISTER_SHARED
    baseline_logical = COMPANIES * per_company + shared
    baseline_charge = charge(baseline_logical)
    assert baseline_logical == 1000 and baseline_charge == REQUEST_LIMIT
    cases = enumerate_scenarios()
    assert len(cases) == 8
    assert max(c["logical"] for c in cases) == SITE_PER_COMPANY
    # At most one search per company, no additional *reserved* logical calls.
    assert all(c["executed"].count("provider_search") <= 1 for c in cases)
    assert all(not ("provider_search" in c["executed"] and c["existing_seed"]) for c in cases)
    assert all(
        "provider_candidate_secondary" in c["skipped"]
        for c in cases
        if c["variant"] == "search_first_fallback_to_h1c"
        and c["candidate_accepted"] and c["secondary_requested"]
    )
    # Deliberate negative proof: appending provider search + independent
    # candidate crawl to existing V8 ceiling is NOT safe.
    naive_added_per_company = SEARCH + CRAWL
    invalid_charge = charge(baseline_logical + COMPANIES * naive_added_per_company)
    assert invalid_charge == 2600 and invalid_charge > REQUEST_LIMIT
    return {
        "screen_type": "v10_m22_offline_provider_slot_feasibility_v1",
        "qualified_v8_sha": "200f056a5a60cad23610a3958b6bec62dfb624a5",
        "companies": COMPANIES,
        "official_logical_ceiling_per_company": OFFICIAL_PER_COMPANY,
        "inclusive_site_logical_ceiling_per_company": SITE_PER_COMPANY,
        "shared_wikidata_logical_ceiling": SHARED_WIKIDATA,
        "annual_workforce_logical_reservation": ANNUAL_WORKFORCE_RESERVED,
        "shared_change_and_support_logical_reservations": BRREG_CHANGES_SHARED + SUPPORT_REGISTER_SHARED,
        "baseline_theoretical_logical_ceiling": baseline_logical,
        "baseline_theoretical_challenge_charge": baseline_charge,
        "naively_appended_search_plus_crawl_challenge_charge": invalid_charge,
        "structurally_feasible_with_reallocation": True,
        "method": "search-first *replaces* eligible H1c/H1g request paths inside 4 reserved site slots; official/Wikidata/workforce slots unchanged",
        "provider_search_counted_inside_site_slots": True,
        "independent_provider_candidate_crawl_logical_ceiling": CRAWL,
        "scenario_count": len(cases),
        "scenarios": cases,
        "provider_usage_rights_verified": False,
        "provider_reproducible_api_key_supplied": False,
        "new_verified_websites_measured": False,
        "runtime_bound_for_provider_fully_proven": False,
        "third_party_cost_zero_verified": False,
        "production_promotion_authorized": False,
        "live_provider_experiment_authorized": False,
        "fresh_company_evaluation_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = make_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("M22 OFFLINE REQUEST ALLOCATION: PASS (rights/runtime/recall remain BLOCKED)")
    print(json.dumps({key: report[key] for key in (
        "baseline_theoretical_challenge_charge",
        "naively_appended_search_plus_crawl_challenge_charge",
        "scenario_count",
        "production_promotion_authorized",
    )}, indent=2))


if __name__ == "__main__":
    main()
