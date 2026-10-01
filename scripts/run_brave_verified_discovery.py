#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.discovery import build_company_search_query, parse_brave_web_results  # noqa: E402
from norway_company_agent.evidence import utc_now  # noqa: E402
from norway_company_agent.search_verified_discovery import (  # noqa: E402
    choose_search_nomination,
    evaluate_search_nomination,
    is_verified_website,
    query_hash,
)

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
USER_AGENT = "builderr-signalpost-poc/0.1 (+https://builderr.ai)"
DEFAULT_COST_PER_QUERY_USD = 0.005


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def brave_search(
    profile: dict[str, Any],
    api_key: str,
    *,
    timeout: float,
    count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Execute one Brave query; returned result content is for in-memory nomination only."""
    query = build_company_search_query(profile)
    params = {
        "q": query,
        "count": str(count),
        "country": "no",
        "search_lang": "nb",
        "safesearch": "moderate",
        "spellcheck": "0",
    }
    url = BRAVE_ENDPOINT + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
            "User-Agent": USER_AGENT,
            "X-Subscription-Token": api_key,
        },
    )
    started = time.monotonic()
    digest = query_hash(query)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = int(response.status)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        payload = json.loads(raw)
        return parse_brave_web_results(payload, query=query), {
            "status": status,
            "latency_ms": elapsed_ms,
            "bytes": len(raw),
            "query_sha256": digest,
            "error": None,
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        return [], {
            "status": int(getattr(exc, "code", 0) or 0),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "bytes": 0,
            "query_sha256": digest,
            "error": type(exc).__name__,
        }


def _audit_record(
    profile: dict[str, Any],
    *,
    operation: dict[str, Any],
    result_count: int,
    selected: bool,
    evaluation: dict[str, Any] | None,
) -> dict[str, Any]:
    """Persist no provider title/snippet/rank/query text; only bounded operational metadata."""
    return {
        "organisation_number": str(profile.get("organisation_number") or ""),
        "provider": "brave_search_api",
        "provider_endpoint": BRAVE_ENDPOINT,
        "query_sha256": operation.get("query_sha256"),
        "provider_status": int(operation.get("status") or 0),
        "provider_error": operation.get("error"),
        "result_count": int(result_count),
        "selected_for_independent_fetch": bool(selected),
        "independent_page_url": (evaluation or {}).get("selected_url"),
        "published": bool((evaluation or {}).get("publishable")),
        "identity_status": (evaluation or {}).get("identity_status"),
        "identity_method": (evaluation or {}).get("identity_method"),
        "raw_provider_results_persisted": False,
        "plaintext_query_persisted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "V6b experiment: Brave Search nominates at most one candidate; an independent page fetch "
            "and strict exact-company gate decide publication."
        )
    )
    parser.add_argument("--input", required=True, help="Retained V5 profiles.jsonl")
    parser.add_argument("--output", required=True, help="Profiles with search-verified promotions")
    parser.add_argument("--report", required=True, help="Experiment report JSON")
    parser.add_argument("--audit-output", help="Optional provider-content-free per-company audit JSONL")
    parser.add_argument("--limit", type=int, default=40, help="Maximum unresolved companies to query")
    parser.add_argument("--count", type=int, default=10, choices=range(1, 11), metavar="1..10")
    parser.add_argument("--provider-timeout", type=float, default=10.0)
    parser.add_argument("--crawl-timeout", type=float, default=6.0)
    parser.add_argument("--min-interval", type=float, default=0.05)
    parser.add_argument("--api-key-env", default="BRAVE_SEARCH_API_KEY")
    parser.add_argument("--cost-per-query-usd", type=float, default=DEFAULT_COST_PER_QUERY_USD)
    parser.add_argument("--max-provider-cost-usd", type=float, default=1.0)
    parser.add_argument("--max-added-conservative-requests", type=int, default=300)
    parser.add_argument("--request-charge-multiplier", type=int, default=2)
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.provider_timeout <= 0 or args.crawl_timeout <= 0:
        parser.error("timeouts must be positive")
    if args.cost_per_query_usd < 0 or args.max_provider_cost_usd < 0:
        parser.error("provider cost values cannot be negative")
    if args.max_added_conservative_requests < 1 or args.request_charge_multiplier < 1:
        parser.error("request limits must be positive")

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        parser.error(f"Missing Brave Search API key in {args.api_key_env}")

    rows = read_jsonl(Path(args.input))
    started_at = utc_now()
    wall_started = time.monotonic()
    counts: Counter[str] = Counter()
    provider_latencies: list[int] = []
    crawl_latencies: list[int] = []
    provider_requests = 0
    provider_bytes = 0
    crawl_requests = 0
    crawl_bytes = 0
    queried = 0
    audits: list[dict[str, Any]] = []

    # One search request + the current bounded independent page fetch (robots + HTML).
    worst_case_logical_per_attempt = 3
    worst_case_charge_per_attempt = worst_case_logical_per_attempt * args.request_charge_multiplier

    for row in rows:
        if queried >= args.limit:
            break
        if is_verified_website(row):
            counts["verified_site_present_skipped"] += 1
            continue

        next_cost = (provider_requests + 1) * args.cost_per_query_usd
        current_charge = (provider_requests + crawl_requests) * args.request_charge_multiplier
        if next_cost > args.max_provider_cost_usd:
            counts["provider_cost_cap_reached"] += 1
            break
        if current_charge + worst_case_charge_per_attempt > args.max_added_conservative_requests:
            counts["request_cap_reached"] += 1
            break

        queried += 1
        results, operation = brave_search(
            row,
            api_key,
            timeout=args.provider_timeout,
            count=args.count,
        )
        provider_requests += 1
        provider_bytes += int(operation.get("bytes") or 0)
        provider_latencies.append(int(operation.get("latency_ms") or 0))
        if operation.get("error"):
            counts["provider_errors"] += 1
            audits.append(
                _audit_record(
                    row,
                    operation=operation,
                    result_count=0,
                    selected=False,
                    evaluation=None,
                )
            )
            time.sleep(args.min_interval)
            continue

        decision = choose_search_nomination(row, results)
        selected = decision.get("selected")
        if not selected:
            counts["no_candidate_after_transient_search"] += 1
            audits.append(
                _audit_record(
                    row,
                    operation=operation,
                    result_count=len(results),
                    selected=False,
                    evaluation=None,
                )
            )
            time.sleep(args.min_interval)
            continue

        counts["independent_candidate_fetches"] += 1
        enriched, evaluation = evaluate_search_nomination(
            row,
            str(selected["url"]),
            timeout=args.crawl_timeout,
        )
        crawl_requests += int(evaluation.get("requests") or 0)
        crawl_bytes += int(evaluation.get("bytes") or 0)
        crawl_latencies.extend(int(value) for value in evaluation.get("latencies_ms") or [])
        row.clear()
        row.update(enriched)

        if evaluation.get("publishable"):
            counts["verified_search_promotions"] += 1
        else:
            counts["quarantined_after_independent_fetch"] += 1

        audits.append(
            _audit_record(
                row,
                operation=operation,
                result_count=len(results),
                selected=True,
                evaluation=evaluation,
            )
        )
        time.sleep(args.min_interval)

    write_jsonl(Path(args.output), rows)
    if args.audit_output:
        write_jsonl(Path(args.audit_output), audits)

    provider_cost = round(provider_requests * args.cost_per_query_usd, 6)
    added_logical_requests = provider_requests + crawl_requests
    added_conservative_charge = added_logical_requests * args.request_charge_multiplier
    report = {
        "generated_at": utc_now(),
        "started_at": started_at,
        "method": "V6b transient Brave nomination -> independent fetch -> strict exact-company publication gate",
        "input_profiles": len(rows),
        "queried_unresolved_profiles": queried,
        "counts": dict(sorted(counts.items())),
        "provider": {
            "name": "Brave Search API",
            "endpoint": BRAVE_ENDPOINT,
            "requests": provider_requests,
            "bytes": provider_bytes,
            "latency_p50_ms": percentile(provider_latencies, 0.50),
            "latency_p95_ms": percentile(provider_latencies, 0.95),
            "declared_cost_per_query_usd": args.cost_per_query_usd,
            "declared_cost_usd": provider_cost,
            "raw_results_persisted": False,
            "plaintext_queries_persisted": False,
        },
        "independent_fetch": {
            "logical_requests": crawl_requests,
            "bytes": crawl_bytes,
            "latency_p50_ms": percentile(crawl_latencies, 0.50),
            "latency_p95_ms": percentile(crawl_latencies, 0.95),
        },
        "budget": {
            "added_logical_requests": added_logical_requests,
            "request_charge_multiplier": args.request_charge_multiplier,
            "added_conservative_request_charge": added_conservative_charge,
            "max_added_conservative_requests": args.max_added_conservative_requests,
            "max_provider_cost_usd": args.max_provider_cost_usd,
            "provider_cost_within_cap": provider_cost <= args.max_provider_cost_usd,
            "request_charge_within_cap": added_conservative_charge <= args.max_added_conservative_requests,
        },
        "wall_runtime_seconds": round(time.monotonic() - wall_started, 3),
        "promotion_status": "experiment_only_pending_fresh_cohort_manual_identity_audit_and_evaluator_key_reproducibility",
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["budget"]["provider_cost_within_cap"] and report["budget"]["request_charge_within_cap"] else 1)


if __name__ == "__main__":
    main()
