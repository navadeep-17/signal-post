#!/usr/bin/env python3
"""M38 pre-registered consumed-four comparison, no production side effects.

Replays exactly M33's four previously consumed, originally-abstaining legal
entities. The ONLY new query variant is M37's full-legal-name + municipality +
'hjemmeside' (no org number). This does NOT mean removing exact org verification
from first-party evidence. Reuse M33 bounded 1-search+robots/homepage accounting
and M32/M23 strict independent-page legal-entity vetoes.

The live caller MUST encrypt the report before saving/uploading any artifact.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import time
from typing import Any, Callable

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src")]

from run_v10_m33_consumed4_diagnostic import (
    BATCH, EXPECTED_SHA, _assert_frozen_history,
    diagnostic as m33_diagnostic,
)
from norway_company_agent.tavily_offline_candidate import normalize_tavily_results
from norway_company_agent.v10_m36_offline_rejection_diagnostics import summarize_transient_candidate_rejections
from norway_company_agent.v10_m38_alternative_search import (
    FROZEN_VARIANT, execute_bounded_alternative,
)
from norway_company_agent.final_site_discovery import fetch_bounded_homepage


def _validate_previous_four(cohort: list[dict[str, Any]], previous_four: dict[str, Any]) -> None:
    """Same identities/order, no previous positive eligible for manual review."""
    if not isinstance(previous_four, dict):
        raise ValueError("Prior four-company development report missing")
    if (
        previous_four.get("schema")!="m33_consumed4_funnel_minimal_private_v1"
        or previous_four.get("source")!="PREVIOUSLY_CONSUMED_M24_20_ONLY"
        or previous_four.get("m24_digest")!=EXPECTED_SHA
        or previous_four.get("requested")!=BATCH
        or previous_four.get("attempted")!=BATCH
        or previous_four.get("aborted") is not False
        or previous_four.get("new_published_claims")!=0
        or previous_four.get("qualified_v8_modified") is not False
    ):
        raise ValueError("Historical development comparator does not meet frozen criteria")
    old_rows=previous_four.get("rows")
    if not isinstance(old_rows, list) or len(old_rows)!=BATCH:
        raise ValueError("Unexpected historical four-company comparison size")
    if [str(x.get("organisation_number")) for x in old_rows] != [
        str(p["organisation_number"]) for p in cohort
    ]:
        raise ValueError("Historic comparator IDs/order differ from frozen four")
    if any(
        x.get("baseline_nominated") is not False
        or x.get("challenger_nominated") is not False
        or x.get("manual_review_candidate") is not False
        or x.get("first_party_fetch_attempted") is not False
        or x.get("published_company_claims") != 0
        for x in old_rows
    ):
        raise ValueError("Historical comparator must be original all-abstention")
    if not (0 < previous_four.get("reserved_logical_http", 0) <= 12):
        raise ValueError("Historical comparison request charge invalid")


def run_m38(
    frozen_20_profiles: list[dict[str, Any]],
    prior_20: dict[str, Any],
    prior_4: dict[str, Any],
    *,
    live: bool,
    api_key: str = "",
    search_fn: Callable[..., Any] = execute_bounded_alternative,
    fetch_fn: Callable[..., Any] = fetch_bounded_homepage,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """One fixed alternative query for each of exactly four consumed companies.

    Returned report is sensitive and may contain independent first-party URLs
    for manual review. NEVER print or write plaintext. Caller encrypts in memory.
    """
    cohort=_assert_frozen_history(frozen_20_profiles,prior_20)
    _validate_previous_four(cohort,prior_4)
    per_company_reasons: dict[str, dict[str, Any]]={}
    search_attempts=0

    def inspected_search(profile: dict[str, Any], *, api_key: str, timeout_seconds: float):
        nonlocal search_attempts
        search_attempts+=1
        if search_attempts > BATCH:
            raise ValueError("More than four Basic Search attempts forbidden")
        result=search_fn(profile,api_key=api_key,timeout_seconds=timeout_seconds)
        if result.status=="ok_transient_candidates_only" and result.payload is not None:
            transient=normalize_tavily_results(result.payload, query="private_in_memory_query")
            per_company_reasons[str(profile["organisation_number"])]=summarize_transient_candidate_rejections(
                profile,transient
            )
        return result

    report=m33_diagnostic(
        frozen_20_profiles, prior_20,
        live=live, api_key=api_key if live else "",
        search_fn=inspected_search, fetch_fn=fetch_fn, clock=clock,
    )
    assert report["requested"]==4 and report["ceiling_search_basic_requests"]==4
    assert report["ceiling_first_party_logical_http"]==8
    assert report["reserved_logical_http"]<=12
    assert report["reserved_conservative_challenge_charge"]<=24
    assert report["new_published_claims"]==0
    assert report["qualified_v8_modified"] is False
    assert search_attempts==(report["attempted"] if live else 0)
    reasons={
        "inspected_total":0, "safe_https_root":0,"directory_or_social_host":0,
        "unsafe_or_non_root_url":0, "invalid_or_missing_url":0,
        "full_legal_name_title_missing":0,
        "deterministic_domain_alias_missing":0,
        "both_title_and_alias_missing":0,
        "m32_per_result_fetch_nomination":0,
        "m35_shadow_per_result_fetch_nomination":0,
    }
    for row in report["rows"]:
        diagnostics=per_company_reasons.get(str(row["organisation_number"]))
        if diagnostics:
            row["private_internal_m36_reason_counts"]=diagnostics["reasons"]
            row["private_internal_result_items_inspected"]=diagnostics["inspected"]
            reasons["inspected_total"]+=diagnostics["inspected"]
            for k in reasons:
                if k != "inspected_total":
                    reasons[k]+=diagnostics["reasons"].get(k,0)
        else:
            row["private_internal_m36_reason_counts"]={}
            row["private_internal_result_items_inspected"]=0
    old_rows=prior_4["rows"]
    out={
        "schema":"m38_private_frozen_four_single_query_v1",
        "source":"PREVIOUSLY_CONSUMED_M24_20_AND_M33_4",
        "selection_sha256":EXPECTED_SHA,
        "query_variant":FROZEN_VARIANT,
        "comparison_design":"same_historical_four_records_not_new_or_randomized",
        "historical_m33_companies_with_normalized_urls":sum(x["normalized_url_result_count"]>0 for x in old_rows),
        "historical_m33_original_nominations":sum(bool(x["baseline_nominated"]) for x in old_rows),
        "historical_m33_m32_nominations":sum(bool(x["challenger_nominated"]) for x in old_rows),
        "historical_m33_first_party_fetch_attempts":sum(bool(x["first_party_fetch_attempted"]) for x in old_rows),
        "query_alt_diagnostic":report,
        "reason_counts":reasons,
        "frozen_original_four_ids_sha256":hashlib.sha256(
            "\n".join(str(p["organisation_number"]) for p in cohort).encode()
        ).hexdigest(),
        "independent_manual_audit_completed":False,
        "fresh_holdout_used":False,
        "provider_search_content_persisted":False,
        "production_modified":False,
        "official_score_measured":False,
        "published_company_claims":0,
        "third_party_cost_usd_confirmed":None if live else 0,
    }
    return out
