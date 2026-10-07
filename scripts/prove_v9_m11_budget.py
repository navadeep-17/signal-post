#!/usr/bin/env python3
"""M11 static request-budget preflight for the frozen V9 candidate (not a qualification run).

Reproduce the reservation structure in run_signalpost_v8/v7/v2/final with
source constants. This is a *structural* upper bound only: runtime reports,
HTTP accounting, source-policy compliance and manual precision remain separate
obligations. Nothing here can authorize release or fresh qualification.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from norway_company_agent.brreg_changes import theoretical_change_feed_requests  # noqa: E402
from norway_company_agent.final_site_discovery import MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE  # noqa: E402
from norway_company_agent.http import MAX_REDIRECTS_PER_ATTEMPT  # noqa: E402
from norway_company_agent.run_budget import RunBudget  # noqa: E402
from norway_company_agent.wikidata_discovery import theoretical_wikidata_lookup_requests  # noqa: E402
from scripts.run_signalpost_final import OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE  # noqa: E402
from scripts.run_signalpost_v7 import SUPPORT_REGISTRY_SHARED_REQUEST_CEILING  # noqa: E402
from scripts.run_signalpost_v8 import default_request_budget  # noqa: E402

CHALLENGE_CAP_PER_100 = 2000
FROZEN_V8_BASELINE = "72f1bf2892ec1c1e35674aa383433c9a37afdaca"
FROZEN_V9_CHALLENGER = "2848ed505103b3cbb0a3bf8d6313ee1ba7a25ecf"


def prove_structural_ceiling(companies: int) -> dict[str, object]:
    """Upper-bound the 1..100 evaluator shard with explicitly reserved shared calls.

    Final -> V2 -> V7 reservations compose from the inside out:
    - 5 official logical modules + 4 bounded logical site requests/company
    - ceil(n/100) shared Wikidata batches
    - ceil(n/100) BRREG change batches
    - 1 bounded Støtteregisteret call
    - at most one annual-workforce attempt/company, reduced as needed
    - 1 redirect maximum/attempt => charge multiplier 2

    Annual-report OCR and HTML processing do not create an unaccounted
    source request; the runtime workforce connector separately enforces its
    own 'max_requests' argument.
    """
    if not 1 <= companies <= 100:
        raise ValueError("This proof applies only to 1..100 companies in one shard.")

    budget = RunBudget(max_challenge_requests=CHALLENGE_CAP_PER_100)
    multiplier = budget.request_charge_multiplier
    if multiplier != 2 or MAX_REDIRECTS_PER_ATTEMPT != 1:
        raise ValueError("HTTP redirect bound no longer matches the conservative charge model.")
    if default_request_budget(companies) != CHALLENGE_CAP_PER_100:
        raise ValueError("The frozen V8 wrapper budget no longer equals the per-100 challenge cap.")

    official = companies * OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE
    site = companies * MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    wikidata = theoretical_wikidata_lookup_requests(companies)
    change = theoretical_change_feed_requests(companies)
    support = SUPPORT_REGISTRY_SHARED_REQUEST_CEILING

    reserved_shared = budget.charge_requests(change + support)
    base_structural = budget.charge_requests(official + site + wikidata)
    annual_capacity = CHALLENGE_CAP_PER_100 - reserved_shared - base_structural
    if annual_capacity < 0:
        raise ValueError(
            f"Even with annual workforce disabled, structural request charge exceeds cap "
            f"for n={companies}: {base_structural}+{reserved_shared}>{CHALLENGE_CAP_PER_100}"
        )
    annual = min(companies, annual_capacity // multiplier)
    total_logical = official + site + wikidata + change + support + annual
    bound = budget.charge_requests(total_logical)
    if not 0 < bound <= CHALLENGE_CAP_PER_100:
        raise AssertionError(f"Computed structural charge is unsafe: {bound}")
    return {
        "screen": "v9_m11_static_structural_request_preflight",
        "decision": "STATIC_THEOREM_PREFLIGHT_ONLY",
        "companies": companies,
        "frozen_v8_baseline_sha": FROZEN_V8_BASELINE,
        "frozen_v9_challenger_sha": FROZEN_V9_CHALLENGER,
        "official_logical_ceiling": official,
        "site_logical_ceiling": site,
        "wikidata_logical_ceiling": wikidata,
        "annual_workforce_logical_ceiling": annual,
        "change_feed_logical_ceiling": change,
        "support_registry_logical_ceiling": support,
        "max_redirects_per_logical_attempt": MAX_REDIRECTS_PER_ATTEMPT,
        "charge_multiplier": multiplier,
        "theoretical_logical_request_ceiling": total_logical,
        "theoretical_conservative_request_charge_ceiling": bound,
        "per_100_request_charge_cap": CHALLENGE_CAP_PER_100,
        "unallocated_conservative_request_charge": CHALLENGE_CAP_PER_100 - bound,
        "zero_external_paid_api_assumption_not_proven_by_this_script": True,
        "runtime_budget_obligation_remains": True,
        "source_policy_audit_obligation_remains": True,
        "manual_exact_company_precision_review_obligation_remains": True,
        "fresh_qualification_authorized": False,
        "production_promotion_authorized": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--companies", type=int, choices=range(1, 101), metavar="1..100",
                   default=100)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = prove_structural_ceiling(args.companies)
    blob = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(blob, encoding="utf-8")
    print(blob, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
