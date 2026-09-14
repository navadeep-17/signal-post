#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.discovery import (  # noqa: E402
    build_company_search_query,
    choose_search_candidate,
    parse_serpapi_web_results,
    qualify_search_discovered_website,
)
from norway_company_agent.evidence import evidence, utc_now  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.website import fetch_website  # noqa: E402

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
USER_AGENT = "builderr-signalpost-poc/0.1 (+https://builderr.ai)"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
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


def serpapi_search(
    profile: dict,
    api_key: str,
    *,
    timeout: float,
    count: int,
) -> tuple[list[dict], dict]:
    """Run one live search and return normalized results for in-memory scoring only."""
    query = build_company_search_query(profile)
    params = {
        "engine": "google",
        "q": query,
        "google_domain": "google.no",
        "gl": "no",
        "hl": "no",
        "num": str(count),
        "no_cache": "true",
        "safe": "active",
        "api_key": api_key,
        "output": "json",
    }
    url = SERPAPI_ENDPOINT + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
            "User-Agent": USER_AGENT,
        },
    )
    started = time.monotonic()
    query_sha256 = hashlib.sha256(query.encode("utf-8")).hexdigest()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = int(response.status)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        payload = json.loads(raw)
        if payload.get("error"):
            return [], {
                "status": status,
                "latency_ms": elapsed_ms,
                "bytes": len(raw),
                "query_sha256": query_sha256,
                "error": "provider_error",
            }
        return parse_serpapi_web_results(payload, query=query), {
            "status": status,
            "latency_ms": elapsed_ms,
            "bytes": len(raw),
            "query_sha256": query_sha256,
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        return [], {
            "status": int(getattr(exc, "code", 0) or 0),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "bytes": 0,
            "query_sha256": query_sha256,
            "error": type(exc).__name__,
        }


def unresolved_for_search(profile: dict) -> bool:
    """H1b currently targets companies that still have no canonical website seed."""
    if str(profile.get("website") or "").strip():
        return False
    website = profile.get("evidence", {}).get("website") or {}
    value = website.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    return not (website.get("status") == "available" and assessment.get("publishable"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="H1b transient search discovery followed by independent exact-company site verification."
    )
    parser.add_argument("--input", required=True, help="Profile JSONL, ideally after baseline/H1a")
    parser.add_argument("--output", required=True, help="Enriched profile JSONL")
    parser.add_argument("--report", required=True)
    parser.add_argument("--limit", type=int, default=20, help="Maximum unresolved profiles to query")
    parser.add_argument("--count", type=int, default=10, choices=range(1, 11), metavar="1..10")
    parser.add_argument("--provider-timeout", type=float, default=10.0)
    parser.add_argument("--crawl-timeout", type=float, default=8.0)
    parser.add_argument("--min-interval", type=float, default=0.05)
    parser.add_argument("--promote-verified", action="store_true")
    parser.add_argument("--api-key-env", default="SERPAPI_API_KEY")
    parser.add_argument("--cost-env", default="SERPAPI_COST_PER_SEARCH_USD")
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.provider_timeout <= 0 or args.crawl_timeout <= 0:
        parser.error("timeouts must be positive")

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        parser.error(f"Missing API key in environment variable {args.api_key_env}")
    raw_cost = os.environ.get(args.cost_env, "").strip()
    if not raw_cost:
        parser.error(
            f"Missing declared marginal search cost in {args.cost_env}; set the USD cost per successful search for the exact account/plan used"
        )
    try:
        cost_per_search = float(raw_cost)
    except ValueError:
        parser.error(f"{args.cost_env} must be a numeric USD value")
    if cost_per_search < 0:
        parser.error(f"{args.cost_env} cannot be negative")

    rows = read_jsonl(Path(args.input))
    counts: Counter[str] = Counter()
    provider_latencies: list[int] = []
    provider_bytes = 0
    provider_requests = 0
    provider_successes = 0
    crawl_requests = 0
    crawl_bytes = 0
    crawl_latencies: list[int] = []
    queried = 0
    started_at = utc_now()
    wall_started = time.monotonic()

    for row in rows:
        if queried >= args.limit:
            break
        if not unresolved_for_search(row):
            counts["canonical_website_present_skipped"] += 1
            continue

        queried += 1
        results, operation = serpapi_search(row, api_key, timeout=args.provider_timeout, count=args.count)
        provider_requests += 1
        provider_latencies.append(int(operation.get("latency_ms") or 0))
        provider_bytes += int(operation.get("bytes") or 0)
        if operation.get("error"):
            counts["provider_errors"] += 1
        elif int(operation.get("status") or 0) == 200:
            provider_successes += 1

        decision = choose_search_candidate(row, results)
        selected = decision.get("selected")
        discovery_summary = {
            "provider": "serpapi_google",
            "provider_endpoint": SERPAPI_ENDPOINT,
            "query_sha256": operation["query_sha256"],
            "result_count": len(results),
            "selected_for_independent_crawl": bool(selected),
            "provider_status": operation["status"],
            "raw_search_results_persisted": False,
            "retention_policy": "Provider title/snippet/rank/query text and raw response are transient and are not persisted as company evidence.",
        }

        if not selected:
            counts["abstained_before_crawl"] += 1
            row.setdefault("evidence", {})["website_search_discovery"] = evidence(
                "website_search_discovery",
                "not_found",
                "transient_serpapi_search",
                SERPAPI_ENDPOINT,
                value=discovery_summary,
                note="No search result passed the crawl-candidate gate; provider result content was discarded.",
            )
            time.sleep(args.min_interval)
            continue

        website, web_ops = fetch_website(selected["url"], timeout=args.crawl_timeout)
        crawl_requests += int(web_ops.get("requests") or 0)
        crawl_bytes += int(web_ops.get("bytes") or 0)
        crawl_latencies.extend(int(value) for value in web_ops.get("latencies_ms", []) if value is not None)
        gated = apply_website_identity_gate(row, website)
        website = gated["website"]
        base_assessment = gated.get("assessment")
        assessment = qualify_search_discovered_website(row, website, base_assessment)
        if assessment is not base_assessment and assessment is not None:
            (website.get("value") or {})["identity_assessment"] = assessment

        website["source_type"] = "search_discovered_company_website"
        website["source_class"] = "company_owned_candidate"
        publishable = bool(assessment and assessment.get("publishable") and website.get("status") == "available")
        independent_url = (website.get("value") or {}).get("final_url") or website.get("source_url")
        row.setdefault("evidence", {})["website_search_discovery"] = evidence(
            "website_search_discovery",
            "available" if publishable else "not_found",
            "transient_serpapi_search_then_independent_crawl",
            SERPAPI_ENDPOINT,
            value={
                **discovery_summary,
                "independent_page_url": independent_url if publishable else None,
                "independent_identity_status": (assessment or {}).get("status"),
                "independent_identity_score": (assessment or {}).get("score"),
            },
            note="Search output was transient. Publication depends only on independently fetched exact-company page evidence.",
        )
        row["evidence"]["website_search_candidate"] = website
        counts["independent_crawls"] += 1
        if publishable:
            counts["verified_sites"] += 1
            if args.promote_verified:
                row["evidence"]["website"] = website
                row["website"] = independent_url or ""
                counts["promoted_sites"] += 1
        else:
            counts["quarantined_sites"] += 1
        time.sleep(args.min_interval)

    write_jsonl(Path(args.output), rows)
    declared_cost = round(provider_successes * cost_per_search, 6)
    report = {
        "generated_at": utc_now(),
        "started_at": started_at,
        "method": "H1b transient SerpApi candidate search -> independent crawl -> page-level exact-company gate",
        "provider": "SerpApi Google Search API",
        "provider_endpoint": SERPAPI_ENDPOINT,
        "input_profiles": len(rows),
        "queried_unresolved_profiles": queried,
        "counts": dict(sorted(counts.items())),
        "operations": {
            "provider_requests": provider_requests,
            "provider_successful_searches": provider_successes,
            "provider_bytes": provider_bytes,
            "provider_latency_p50_ms": percentile(provider_latencies, 0.50),
            "provider_latency_p95_ms": percentile(provider_latencies, 0.95),
            "independent_crawl_requests": crawl_requests,
            "independent_crawl_bytes": crawl_bytes,
            "independent_crawl_latency_p50_ms": percentile(crawl_latencies, 0.50),
            "independent_crawl_latency_p95_ms": percentile(crawl_latencies, 0.95),
            "third_party_cost_per_successful_search_usd": cost_per_search,
            "third_party_cost_usd": declared_cost,
            "wall_runtime_ms": int((time.monotonic() - wall_started) * 1000),
        },
        "raw_search_results_persisted": False,
        "promote_verified_enabled": args.promote_verified,
        "qualification": "experiment_only_pending_live_frozen_audit_and_provider-plan-rights_record",
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
