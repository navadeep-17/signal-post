#!/usr/bin/env python3
"""M33 four-company *previously consumed* search-to-page funnel diagnostic.

A new Basic Search, only when --execute-live is explicitly supplied.
Purpose: separate empty search responses, restrictive crawl-nomination and
first-party legal-entity rejection; NEVER replace V8, publish company claims,
write provider snippets or infer an official challenge score.
All company-level output must remain PRIVATE and encrypted by caller.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_v10_m26_consumed_pilot import (  # noqa: E402
    EXPECTED_SHA, ABORT_PROVIDER_STATUSES, load_consumed_cohort,
)
from norway_company_agent.discovery import choose_search_candidate, BLOCKED_DISCOVERY_HOSTS  # noqa: E402
from norway_company_agent.final_site_discovery import fetch_bounded_homepage  # noqa: E402
from norway_company_agent.tavily_bounded_transport import (  # noqa: E402
    execute_bounded_search, SiteSlotBudget,
)
from norway_company_agent.tavily_offline_candidate import (  # noqa: E402
    normalize_tavily_results,
)
from norway_company_agent.v10_m32_offline_nomination import (  # noqa: E402
    _safe_first_party_homepage, nominate_offline, screen_independent_fixture,
)
from norway_company_agent.website import normalize_homepage  # noqa: E402

BATCH = 4
SOURCE_ROWS = 20
EXPECTED_OLD_ABSTENT = 17
MAX_SEARCHES = BATCH
MAX_FIRST_PARTY_LOGICAL = 2 * BATCH
MAX_LOGICAL = MAX_SEARCHES + MAX_FIRST_PARTY_LOGICAL
MAX_CONSERVATIVE_CHARGE = MAX_LOGICAL * 2
MAX_WALL_SECONDS = 180
MIN_SECONDS_TO_START_NEXT = 25

# Fixed source tag ensures no third-party discovery data is written into audit.
SOURCE_TYPE = "experiment_m33_independent_first_party_only"

def _assert_frozen_history(profiles: list[dict[str, Any]], history: dict[str, Any]) -> list[dict[str, Any]]:
    if len(profiles) != SOURCE_ROWS:
        raise ValueError("M33 accepts only the 20 fixed M24 consumed profiles")
    ids = [str(p["organisation_number"]) for p in profiles]
    if len(set(ids)) != SOURCE_ROWS or hashlib.sha256("\n".join(ids).encode()).hexdigest() != EXPECTED_SHA:
        raise ValueError("Frozen cohort identity/order changed")
    if (
        history.get("schema") != "m26_consumed_development_manual_review_only"
        or history.get("type") != "PREVIOUSLY_CONSUMED_NOT_FRESH"
        or history.get("selection_sha256") != EXPECTED_SHA
        or history.get("requested_companies") != SOURCE_ROWS
        or history.get("attempted_companies") != SOURCE_ROWS
        or history.get("aborted") is not False
        or history.get("published_company_claims") != 0
        or history.get("manually_reviewable_exact_org_sites") != 0
        or history.get("qualified_v8_modified") is not False
    ):
        raise ValueError("M33 requires the completed unmodified consumed-20 M26 history")
    rows = history.get("rows") or []
    if not isinstance(rows, list) or len(rows) != SOURCE_ROWS:
        raise ValueError("M26 history must have 20 completed rows")
    if [str(r.get("organisation_number")) for r in rows] != ids:
        raise ValueError("M26 history org numbers/order mismatch")
    if sum(r.get("status") == "no_candidate_qualified_for_independent_fetch" for r in rows) != EXPECTED_OLD_ABSTENT:
        raise ValueError("M31 17/20 original abstention invariant changed")
    if any(r.get("published_claims") != 0 for r in rows):
        raise ValueError("Original history claimed published companies")
    selected = [
        profile for profile, row in zip(profiles, rows)
        if row["status"] == "no_candidate_qualified_for_independent_fetch"
    ][:BATCH]
    if len(selected) != BATCH:
        raise ValueError("Not enough originally abstained companies to diagnose")
    return selected


def _result_categories(results: list[dict[str, Any]]) -> dict[str, int]:
    """Aggregated private counts; never persist URLs/title/snippets/query/rank."""
    counts = Counter()
    for r in results:
        url = normalize_homepage(r.get("url"))
        if not url:
            counts["invalid_url"] += 1
            continue
        # Only classify generic blocked directory/social type.
        from urllib.parse import urlsplit
        host = (urlsplit(url).hostname or "").casefold().removeprefix("www.")
        if any(host == bad or host.endswith("." + bad) for bad in BLOCKED_DISCOVERY_HOSTS):
            counts["directory_or_social_host"] += 1
        elif _safe_first_party_homepage(r.get("url")) is None:
            counts["not_safe_root_https_homepage"] += 1
        else:
            counts["safe_root_https_homepage"] += 1
    return dict(counts)


def diagnose_one(
    profile: dict[str, Any],
    *,
    api_key: str,
    search_fn: Callable[..., Any] = execute_bounded_search,
    fetch_fn: Callable[..., Any] = fetch_bounded_homepage,
) -> dict[str, Any]:
    budget = SiteSlotBudget()
    budget.reserve_search()   # BEFORE provider HTTP, including unsuccessful attempts
    response = search_fn(profile, api_key=api_key, timeout_seconds=8.0)
    row: dict[str, Any] = {
        "organisation_number": str(profile["organisation_number"]),  # encrypted artifact only
        "status": response.status,
        "raw_result_count": 0,
        "normalized_url_result_count": 0,
        "url_categories": {},
        "baseline_nominated": False,
        "challenger_nominated": False,
        "nominated_for_crawl": False,
        "first_party_fetch_attempted": False,
        "first_party_page_available": False,
        "identity_status": "not_attempted",
        "manual_review_candidate": False,
        "site_logical_reserved": budget.used,
        "conservative_request_charge_reserved": budget.conservative_charge,
        "published_company_claims": 0,
    }
    if response.status != "ok_transient_candidates_only" or not isinstance(response.payload, dict):
        return row
    raw = response.payload.get("results") or []
    row["raw_result_count"] = min(len(raw), 10)
    query = "transient_minimal_query"
    parsed = normalize_tavily_results(response.payload, query=query)
    row["normalized_url_result_count"] = len(parsed)
    row["url_categories"] = _result_categories(parsed)
    if not parsed:
        row["status"] = "no_valid_search_urls"
        return row
    original = choose_search_candidate(profile, parsed)
    row["baseline_nominated"] = bool(original.get("selected"))
    nominee = nominate_offline(profile, parsed)
    choice = nominee.get("selected")
    row["challenger_nominated"] = nominee.get("path") == "offline_strict_root_domain_with_full_title"
    if not choice:
        row["status"] = "no_safe_nomination"
        return row
    url = _safe_first_party_homepage(choice.get("url"))
    if not url:
        row["status"] = "unsafe_nomination_blocked"
        return row
    budget.reserve_homepage()  # BEFORE any robots/homepage HTTP
    row["nominated_for_crawl"] = True
    row["first_party_fetch_attempted"] = True
    row["site_logical_reserved"] = budget.used
    row["conservative_request_charge_reserved"] = budget.conservative_charge
    website, metrics = fetch_fn(url, source_type=SOURCE_TYPE, timeout=6.0)
    if not isinstance(metrics, dict) or not isinstance(metrics.get("requests"), int) or not 0 <= metrics["requests"] <= 2:
        row["status"] = "fetch_budget_violation"
        return row
    if website.get("status") != "available":
        row["status"] = "first_party_page_unavailable"
        return row
    row["first_party_page_available"] = True
    proof = screen_independent_fixture(
        profile, payload=response.payload, independently_fetched=website,
    )
    row["identity_status"] = proof["status"]
    row["manual_review_candidate"] = proof["identity_eligible_for_manual_review"] is True
    row["status"] = "manual_review_only" if row["manual_review_candidate"] else "identity_rejected"
    if row["manual_review_candidate"]:
        # First-party provenance only; never provider title, snippet or answer.
        value = website.get("value") or {}
        row["first_party_verified_url_for_private_audit"] = normalize_homepage(value.get("final_url"))
        row["first_party_content_sha256_for_private_audit"] = value.get("content_sha256")
    return row


def diagnostic(
    profiles: list[dict[str, Any]],
    history: dict[str, Any],
    *,
    live: bool,
    api_key: str = "",
    search_fn: Callable[..., Any] = execute_bounded_search,
    fetch_fn: Callable[..., Any] = fetch_bounded_homepage,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    cohort = _assert_frozen_history(profiles, history)
    if live and not api_key.strip():
        raise ValueError("Private provider key missing: refuse all attempts")
    start = clock()
    rows: list[dict[str, Any]] = []
    stopped = False
    for profile in cohort:
        if not live:
            rows.append({
                "organisation_number": str(profile["organisation_number"]),
                "status": "offline_no_provider_or_site_requests",
                "site_logical_reserved": 0,
                "conservative_request_charge_reserved": 0,
                "published_company_claims": 0,
            })
            continue
        if clock() - start > MAX_WALL_SECONDS - MIN_SECONDS_TO_START_NEXT:
            stopped = True
            break
        row = diagnose_one(profile, api_key=api_key, search_fn=search_fn, fetch_fn=fetch_fn)
        rows.append(row)
        if row["status"] in ABORT_PROVIDER_STATUSES or row["status"] in (
            "fetch_budget_violation", "no_key_no_request",
        ):
            stopped = True
            break
    logical = sum(row["site_logical_reserved"] for row in rows)
    conservative = sum(row["conservative_request_charge_reserved"] for row in rows)
    if (
        len(rows) > BATCH or logical > MAX_LOGICAL or
        conservative > MAX_CONSERVATIVE_CHARGE or
        sum(x.get("first_party_fetch_attempted") is True for x in rows) > BATCH
    ):
        raise ValueError("M33 live budget or exact batch ceiling violated")
    return {
        "schema": "m33_consumed4_funnel_minimal_private_v1",
        "source": "PREVIOUSLY_CONSUMED_M24_20_ONLY",
        "m24_digest": EXPECTED_SHA,
        "requested": BATCH,
        "attempted": len(rows) if live else 0,
        "aborted": stopped,
        "rows": rows,
        "reserved_logical_http": logical,
        "reserved_conservative_challenge_charge": conservative,
        "ceiling_search_basic_requests": MAX_SEARCHES,
        "ceiling_first_party_logical_http": MAX_FIRST_PARTY_LOGICAL,
        "ceiling_challenge_charge": MAX_CONSERVATIVE_CHARGE,
        "new_published_claims": 0,
        "manual_audit_complete": False,
        "official_score_measured": False,
        "qualified_v8_modified": False,
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    for opt in ("m19-a", "m19-b", "m20-a"):
        p.add_argument("--"+opt, required=True, type=Path)
    p.add_argument("--historical-private-json", required=True, type=Path)
    p.add_argument("--output", default=ROOT / "out/private-m33.json", type=Path)
    p.add_argument("--execute-live", action="store_true")
    p.add_argument("--confirm-free-credits-and-billing-off", action="store_true")
    a=p.parse_args()
    if a.execute_live and not a.confirm_free_credits_and_billing_off:
        p.error("Live mode requires explicit free-credits/PAYG-off confirmation")
    if not a.output.resolve().is_relative_to((ROOT/"out").resolve()):
        p.error("Private report must be written only within gitignored out/")
    profiles=load_consumed_cohort([a.m19_a,a.m19_b,a.m20_a],
        ROOT/"evaluation/v10_m24_consumed_dev_20.json")
    previous=json.loads(a.historical_private_json.read_text(encoding="utf-8"))
    key=os.environ.get("TAVILY_API_KEY","") if a.execute_live else ""
    report=diagnostic(profiles,previous,live=a.execute_live,api_key=key)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("M33 PRIVATE, previously consumed-only diagnostic complete. "
          "Results withheld from logs; no company claims published.")
    return 1 if report["aborted"] else 0

if __name__=="__main__":
    raise SystemExit(main())
