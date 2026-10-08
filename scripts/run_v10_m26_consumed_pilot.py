#!/usr/bin/env python3
"""M26 frozen, already-consumed 20-company pilot, disabled by default.

NEVER use for fresh-company evaluation, production V8, or an official score.
No import side effects. Without --execute-live, not one company HTTP call occurs.
Local output is a manual-review queue with zero published company claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_v10_m24_consumed_dev import SOURCES, freeze, parse_jsonl  # noqa: E402
from norway_company_agent.discovery import choose_search_candidate  # noqa: E402
from norway_company_agent.domain_discovery import _page_contains_org_number  # noqa: E402
from norway_company_agent.final_site_discovery import fetch_bounded_homepage  # noqa: E402
from norway_company_agent.tavily_bounded_transport import SiteSlotBudget, execute_bounded_search  # noqa: E402
from norway_company_agent.tavily_offline_candidate import (  # noqa: E402
    normalize_tavily_results, offline_screen, tavily_basic_search_body,
)
from norway_company_agent.website import _registered_domain, normalize_homepage  # noqa: E402

EXPECTED_SHA = "3967c2a4b16e6645d3426168d32511944c5e196d19e147b65924925c69c6360e"
MAX_BATCH = 20
MAX_LOGICAL_REQUESTS = 3 * MAX_BATCH  # 1 provider + 2 independent webpage per org
MAX_CONSERVATIVE_CHARGE = 2 * MAX_LOGICAL_REQUESTS
MAX_PILOT_WALL_SECONDS = 600
PER_COMPANY_MIN_REMAINING_SECONDS = 25
ABORT_PROVIDER_STATUSES = {
    "invalid_or_forbidden_key",
    "rate_limited_or_out_of_credits",
    "provider_http_error",
    "redirect_blocked",
    "unexpected_response_origin",
    "transport_error",
    "oversized_provider_response",
    "invalid_json_response",
    "invalid_search_response",
}


def load_consumed_cohort(archive_paths: list[Path], manifest_path: Path) -> list[dict[str, Any]]:
    """Verify all pinned source artifacts and exact order before opening output."""
    if len(archive_paths) != len(SOURCES):
        raise ValueError("Exactly three already-consumed M19-A/M19-B/M20-A ZIPs required")
    committed = json.loads(manifest_path.read_text(encoding="utf-8"))
    rebuilt = freeze(archive_paths)  # asserts archives' SHA256 and 300 distinct org IDs
    if committed.get("type") != "PRIOR_CONSUMED_ONLY_NOT_TRANSFER":
        raise ValueError("Fresh / transfer cohort is forbidden")
    if committed.get("live_provider_authorized") is not False or committed.get("permission_to_merge") is not False:
        raise ValueError("Frozen source manifest must explicitly prohibit promotion")
    if (
        committed.get("selected_list_sha256") != EXPECTED_SHA
        or rebuilt["selected_list_sha256"] != EXPECTED_SHA
        or committed.get("selected_per_cohort") != rebuilt["selected_per_cohort"]
    ):
        raise ValueError("Selected list changed from M24 immutable development cohort")
    profiles: list[dict[str, Any]] = []
    for spec, path in zip(SOURCES, archive_paths):
        group = spec[0]
        selected = committed["selected_per_cohort"][group]
        with zipfile.ZipFile(path) as archive:
            candidate_profiles = {
                str(item["organisation_number"]): item
                for item in parse_jsonl(archive.read("baseline-out/work/profiles.jsonl"))
            }
        for org in selected:
            item = candidate_profiles[org]
            if str(item.get("website") or "").strip():
                raise ValueError("M24 selection incorrectly included seeded company")
            if not str(item.get("name") or "").strip() or not str(item.get("municipality") or "").strip():
                raise ValueError("Incomplete BRREG identity in frozen pilot")
            profiles.append(item)
    if len(profiles) != MAX_BATCH or len({str(row["organisation_number"]) for row in profiles}) != MAX_BATCH:
        raise ValueError("M26 must process exactly 20 distinct consumed companies")
    assert hashlib.sha256("\n".join(str(p["organisation_number"]) for p in profiles).encode()).hexdigest() == EXPECTED_SHA
    return profiles


def run_one(
    profile: dict[str, Any],
    *,
    key: str,
    search_fn: Callable[..., Any] = execute_bounded_search,
    fetch_fn: Callable[..., Any] = fetch_bounded_homepage,
) -> dict[str, Any]:
    """Attempt only one search and at most one independently verified homepage.

    The per-entity conservative reserved ledger is incremented BEFORE each
    network attempt; unknown results never become claims.
    """
    org = str(profile["organisation_number"])
    slots = SiteSlotBudget()
    slots.reserve_search()
    result = search_fn(profile, api_key=key, timeout_seconds=8.0)
    item: dict[str, Any] = {
        "organisation_number": org,
        "status": "abstained",
        "site_logical_requests_reserved": slots.used,
        "conservative_charge_reserved": slots.conservative_charge,
        "published_claims": 0,
        "manual_review_required": True,
    }
    if result.status != "ok_transient_candidates_only" or result.payload is None:
        item["status"] = result.status
        return item

    query = tavily_basic_search_body(profile)["query"]
    candidates = normalize_tavily_results(result.payload, query=query)
    selection = choose_search_candidate(profile, candidates)
    chosen = selection.get("selected")
    if not chosen:
        item["status"] = "no_candidate_qualified_for_independent_fetch"
        return item

    url = normalize_homepage(chosen.get("url"))
    if not url:
        item["status"] = "invalid_candidate_url"
        return item
    # Consume the two independent GET reservations before the robots/homepage
    # fetch; the provider response can never shortcut the first-party gate.
    slots.reserve_homepage()
    item["site_logical_requests_reserved"] = slots.used
    item["conservative_charge_reserved"] = slots.conservative_charge
    page, metrics = fetch_fn(
        url, source_type="experiment_search_nominated_company_homepage", timeout=6.0
    )
    if not isinstance(metrics, dict) or not 0 <= int(metrics.get("requests") or 0) <= 2:
        item["status"] = "independent_fetch_budget_violation"
        return item
    if page.get("status") != "available":
        item["status"] = "first_party_page_unavailable"
        return item

    proof = offline_screen(profile, result.payload, page)
    if not proof["independent_exact_site_eligible"]:
        item["status"] = "first_party_identity_rejected"
        return item

    value = page.get("value") or {}
    final_url = normalize_homepage(value.get("final_url"))
    if not final_url or not _registered_domain(url) or _registered_domain(url) != _registered_domain(final_url):
        item["status"] = "cross_domain_redirect_rejected"
        return item

    # Even stricter than M23: for *this pilot* require the precise target
    # organisation number on an independently fetched page, never just a
    # similarly named parent company's title/address.
    if not _page_contains_org_number(profile, page):
        item["status"] = "exact_org_number_missing_from_fetched_page"
        return item

    item["status"] = "manual_exact_org_site_review_required"
    item["first_party_site_url"] = final_url
    item["first_party_sha256"] = value.get("content_sha256")
    item["identity_check"] = "m23_independent_page_guard_plus_exact_org"
    # Intentionally no provider URL/title/snippet/rank/query/body/score.
    return item


def run_pilot(
    profiles: list[dict[str, Any]],
    *,
    live: bool,
    api_key: str = "",
    search_fn: Callable[..., Any] = execute_bounded_search,
    fetch_fn: Callable[..., Any] = fetch_bounded_homepage,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if len(profiles) != MAX_BATCH:
        raise ValueError("Pilot must use exactly 20 frozen development records")
    orgs = [str(p.get("organisation_number") or "") for p in profiles]
    if (len(set(orgs)) != MAX_BATCH or
            hashlib.sha256("\n".join(orgs).encode()).hexdigest() != EXPECTED_SHA):
        raise ValueError("Pilot must preserve M24's exact frozen IDs and ordering")
    if not live and api_key:
        # A preview never needs credentials, even if accidentally supplied.
        api_key = ""
    if live and not api_key.strip():
        raise ValueError("TAVILY_API_KEY is missing; no requests started")
    started = clock()
    rows = []
    aborted = False
    reason = None
    for profile in profiles:
        if not live:
            rows.append({
                "organisation_number": str(profile["organisation_number"]),
                "status": "dry_run_no_network",
                "site_logical_requests_reserved": 0,
                "conservative_charge_reserved": 0,
                "published_claims": 0,
            })
            continue
        if clock() - started > MAX_PILOT_WALL_SECONDS - PER_COMPANY_MIN_REMAINING_SECONDS:
            aborted = True
            reason = "pilot_time_guard"
            break
        item = run_one(profile, key=api_key, search_fn=search_fn, fetch_fn=fetch_fn)
        rows.append(item)
        if item["status"] in ABORT_PROVIDER_STATUSES or item["status"] == "independent_fetch_budget_violation":
            aborted = True
            reason = "provider_or_budget_failure"
            break
    charged = sum(item["conservative_charge_reserved"] for item in rows)
    logical = sum(item["site_logical_requests_reserved"] for item in rows)
    if logical > MAX_LOGICAL_REQUESTS or charged > MAX_CONSERVATIVE_CHARGE:
        raise ValueError("Global development-pilot request ceiling violated")
    return {
        "schema": "m26_consumed_development_manual_review_only",
        "type": "PREVIOUSLY_CONSUMED_NOT_FRESH",
        "selection_sha256": EXPECTED_SHA,
        "requested_companies": MAX_BATCH,
        "attempted_companies": len(rows) if live else 0,
        "aborted": aborted,
        "abort_reason": reason,
        "logical_requests_reserved": logical,
        "conservative_charge_reserved": charged,
        "conservative_dev_20_charge_ceiling": MAX_CONSERVATIVE_CHARGE,
        "manually_reviewable_exact_org_sites": sum(
            row["status"] == "manual_exact_org_site_review_required" for row in rows
        ),
        "published_company_claims": 0,
        "verified_new_sites_published": 0,
        "independent_manual_audit_completed": False,
        "third_party_cost_usd_confirmed": 0 if not live else None,
        "qualified_v8_modified": False,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m19-a", required=True, type=Path)
    parser.add_argument("--m19-b", required=True, type=Path)
    parser.add_argument("--m20-a", required=True, type=Path)
    parser.add_argument(
        "--manifest", type=Path,
        default=ROOT / "evaluation" / "v10_m24_consumed_dev_20.json"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "out" / "private-m26-pilot-report.json"
    )
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--confirm-pay-as-you-go-off", action="store_true")
    parser.add_argument("--confirm-credits-at-least-20", action="store_true")
    parser.add_argument("--confirm-server-side-use", action="store_true")
    args = parser.parse_args()
    if args.execute_live and not all((
        args.confirm_pay_as_you_go_off,
        args.confirm_credits_at_least_20,
        args.confirm_server_side_use,
    )):
        parser.error("Live pilot requires explicit no-paid-billing, credit and server-side-use confirmations")
    if not args.output.resolve().is_relative_to((ROOT / "out").resolve()):
        parser.error("Reports must stay under git-ignored out/; do not publish provider analysis")
    profiles = load_consumed_cohort(
        [args.m19_a, args.m19_b, args.m20_a], args.manifest
    )
    key = os.environ.get("TAVILY_API_KEY", "") if args.execute_live else ""
    if args.execute_live and not key:
        parser.error("TAVILY_API_KEY missing from the runner's private environment")
    report = run_pilot(profiles, live=args.execute_live, api_key=key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "M26 private consumed-only pilot report saved; "
        f"attempted={report['attempted_companies']}, "
        f"manual-review candidates={report['manually_reviewable_exact_org_sites']}, "
        f"aborted={report['aborted']}. No claims published."
    )
    return 0 if not report["aborted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
