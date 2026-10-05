#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from norway_company_agent.discovery import qualify_search_discovered_website  # noqa: E402
from norway_company_agent.evidence import evidence, utc_now  # noqa: E402
from norway_company_agent.final_site_discovery import (  # noqa: E402
    _has_conflicting_explicit_org_number,
    fetch_bounded_homepage,
)
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.model_web_search import (  # noqa: E402
    DEFAULT_SEARCH_CONTEXT_SIZE,
    DEFAULT_WEB_SEARCH_MODEL,
    MAX_WEB_SEARCH_TOOL_CALLS,
    OPENAI_RESPONSES_ENDPOINT,
    choose_model_url_candidates,
    openai_web_search_candidates,
)
from run_search_discovery import percentile, read_jsonl, unresolved_for_search, write_jsonl  # noqa: E402

# OpenAI public Standard-mode prices checked 2026-10-05. The challenge's exact
# evaluator budget remains authoritative, so every live experiment must pass an
# explicit --max-external-api-cost-usd rather than assuming a Builderr dollar cap.
DEFAULT_WEB_SEARCH_USD_PER_CALL = 0.01
DEFAULT_INPUT_USD_PER_MILLION = 0.10
DEFAULT_OUTPUT_USD_PER_MILLION = 0.50
DEFAULT_MAX_PROVIDER_INPUT_TOKENS_PER_COMPANY = 50_000
DEFAULT_MAX_PROVIDER_OUTPUT_TOKENS_PER_COMPANY = 180


def _estimated_cost_usd(
    *,
    web_search_calls: int,
    input_tokens: int,
    output_tokens: int,
    web_search_usd_per_call: float,
    input_usd_per_million: float,
    output_usd_per_million: float,
) -> float:
    if min(
        web_search_calls,
        input_tokens,
        output_tokens,
        web_search_usd_per_call,
        input_usd_per_million,
        output_usd_per_million,
    ) < 0:
        raise ValueError("cost inputs cannot be negative")
    return round(
        web_search_calls * web_search_usd_per_call
        + (input_tokens / 1_000_000) * input_usd_per_million
        + (output_tokens / 1_000_000) * output_usd_per_million,
        6,
    )


def _preflight_cost_ceiling_usd(
    *,
    companies: int,
    max_input_tokens_per_company: int,
    max_output_tokens_per_company: int,
    web_search_usd_per_call: float,
    input_usd_per_million: float,
    output_usd_per_million: float,
) -> float:
    if companies < 1 or max_input_tokens_per_company < 0 or max_output_tokens_per_company < 0:
        raise ValueError("preflight cost inputs are invalid")
    return _estimated_cost_usd(
        web_search_calls=companies * MAX_WEB_SEARCH_TOOL_CALLS,
        input_tokens=companies * max_input_tokens_per_company,
        output_tokens=companies * max_output_tokens_per_company,
        web_search_usd_per_call=web_search_usd_per_call,
        input_usd_per_million=input_usd_per_million,
        output_usd_per_million=output_usd_per_million,
    )


def _conflict_quarantine(assessment: dict | None) -> dict:
    base = dict(assessment or {})
    return {
        **base,
        "status": "review",
        "score": min(float(base.get("score") or 0.8), 0.8),
        "publishable": False,
        "reasons": [
            *list(base.get("reasons") or []),
            "Q3 search candidate page contains an explicit organisation number for another entity without the target organisation number",
        ],
        "method": "q3_search_candidate_conflicting_org_guard_v1",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Q3 experiment: evaluator-reproducible OpenAI web-search URL nomination -> "
            "independent bounded crawl -> current exact-company publication gate."
        )
    )
    parser.add_argument("--input", required=True, help="Profile JSONL after the current baseline website path")
    parser.add_argument("--output", required=True, help="Experiment-enriched profile JSONL")
    parser.add_argument("--report", required=True)
    parser.add_argument("--limit", type=int, default=20, help="Maximum unresolved profiles to query")
    parser.add_argument("--provider-timeout", type=float, default=20.0)
    parser.add_argument("--crawl-timeout", type=float, default=8.0)
    parser.add_argument("--candidate-crawls", type=int, default=2, choices=range(1, 3), metavar="1..2")
    parser.add_argument("--provider-candidates", type=int, default=5, choices=range(1, 6), metavar="1..5")
    parser.add_argument("--search-context-size", default=DEFAULT_SEARCH_CONTEXT_SIZE, choices=("low", "medium", "high"))
    parser.add_argument("--min-interval", type=float, default=0.05)
    parser.add_argument("--promote-verified", action="store_true")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--model", default=os.environ.get("SIGNALPOST_WEB_SEARCH_MODEL", DEFAULT_WEB_SEARCH_MODEL))
    parser.add_argument("--max-external-api-cost-usd", type=float, required=True)
    parser.add_argument("--web-search-usd-per-call", type=float, default=DEFAULT_WEB_SEARCH_USD_PER_CALL)
    parser.add_argument("--input-usd-per-million", type=float, default=DEFAULT_INPUT_USD_PER_MILLION)
    parser.add_argument("--output-usd-per-million", type=float, default=DEFAULT_OUTPUT_USD_PER_MILLION)
    parser.add_argument(
        "--max-provider-input-tokens-per-company",
        type=int,
        default=DEFAULT_MAX_PROVIDER_INPUT_TOKENS_PER_COMPANY,
    )
    parser.add_argument(
        "--max-provider-output-tokens-per-company",
        type=int,
        default=DEFAULT_MAX_PROVIDER_OUTPUT_TOKENS_PER_COMPANY,
    )
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.provider_timeout <= 0 or args.crawl_timeout <= 0:
        parser.error("timeouts must be positive")
    if args.min_interval < 0:
        parser.error("--min-interval cannot be negative")
    if args.max_external_api_cost_usd <= 0:
        parser.error("--max-external-api-cost-usd must be positive and explicitly confirmed for the run")
    if min(args.web_search_usd_per_call, args.input_usd_per_million, args.output_usd_per_million) < 0:
        parser.error("declared provider prices cannot be negative")
    if args.max_provider_input_tokens_per_company < 1 or args.max_provider_output_tokens_per_company < 1:
        parser.error("provider token ceilings must be positive")

    preflight_cost_ceiling = _preflight_cost_ceiling_usd(
        companies=args.limit,
        max_input_tokens_per_company=args.max_provider_input_tokens_per_company,
        max_output_tokens_per_company=args.max_provider_output_tokens_per_company,
        web_search_usd_per_call=args.web_search_usd_per_call,
        input_usd_per_million=args.input_usd_per_million,
        output_usd_per_million=args.output_usd_per_million,
    )
    if preflight_cost_ceiling > args.max_external_api_cost_usd:
        parser.error(
            "Declared Q3 provider ceiling exceeds --max-external-api-cost-usd: "
            f"{preflight_cost_ceiling:.6f}>{args.max_external_api_cost_usd:.6f}"
        )

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        parser.error(f"Missing evaluator-reproducible model API key in environment variable {args.api_key_env}")

    rows = read_jsonl(Path(args.input))
    counts: Counter[str] = Counter()
    provider_latencies: list[int] = []
    provider_bytes = 0
    provider_requests = 0
    web_search_tool_calls = 0
    provider_input_tokens = 0
    provider_output_tokens = 0
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
        results, operation = openai_web_search_candidates(
            row,
            api_key,
            model=args.model,
            timeout=args.provider_timeout,
            max_candidates=args.provider_candidates,
            search_context_size=args.search_context_size,
        )
        provider_requests += 1
        provider_latencies.append(int(operation.get("latency_ms") or 0))
        provider_bytes += int(operation.get("bytes") or 0)
        tool_calls = int(operation.get("web_search_tool_calls") or 0)
        if tool_calls > MAX_WEB_SEARCH_TOOL_CALLS:
            raise RuntimeError(
                f"Model provider exceeded one-call web-search ceiling: {tool_calls}>{MAX_WEB_SEARCH_TOOL_CALLS}"
            )
        web_search_tool_calls += tool_calls
        input_tokens = int(operation.get("input_tokens") or 0)
        output_tokens = int(operation.get("output_tokens") or 0)
        if input_tokens > args.max_provider_input_tokens_per_company:
            raise RuntimeError(
                "Provider input/search-content token ceiling exceeded for one company: "
                f"{input_tokens}>{args.max_provider_input_tokens_per_company}"
            )
        if output_tokens > args.max_provider_output_tokens_per_company:
            raise RuntimeError(
                "Provider output token ceiling exceeded for one company: "
                f"{output_tokens}>{args.max_provider_output_tokens_per_company}"
            )
        provider_input_tokens += input_tokens
        provider_output_tokens += output_tokens
        observed_cost = _estimated_cost_usd(
            web_search_calls=web_search_tool_calls,
            input_tokens=provider_input_tokens,
            output_tokens=provider_output_tokens,
            web_search_usd_per_call=args.web_search_usd_per_call,
            input_usd_per_million=args.input_usd_per_million,
            output_usd_per_million=args.output_usd_per_million,
        )
        if observed_cost > args.max_external_api_cost_usd:
            raise RuntimeError(
                "Observed external API cost exceeded configured run budget: "
                f"{observed_cost:.6f}>{args.max_external_api_cost_usd:.6f}"
            )
        if operation.get("error"):
            counts["provider_errors"] += 1

        selected = choose_model_url_candidates(results, limit=args.candidate_crawls)
        discovery_summary = {
            "provider": "openai_responses_web_search",
            "provider_endpoint": OPENAI_RESPONSES_ENDPOINT,
            "model": args.model,
            "prompt_sha256": operation.get("prompt_sha256"),
            "provider_status": operation.get("status"),
            "search_context_size": args.search_context_size,
            "citation_url_count": len(results),
            "selected_candidate_count": len(selected),
            "web_search_tool_calls": tool_calls,
            "max_web_search_tool_calls": MAX_WEB_SEARCH_TOOL_CALLS,
            "web_search_required": True,
            "raw_provider_response_persisted": False,
            "provider_response_text_persisted": False,
            "provider_citation_titles_persisted": False,
            "retention_policy": (
                "Model/search output is transient URL nomination only. Identity and publication depend solely on independently fetched destination-page evidence."
            ),
        }

        if not selected:
            counts["abstained_before_crawl"] += 1
            row.setdefault("evidence", {})["website_model_search_discovery"] = evidence(
                "website_model_search_discovery",
                "not_found",
                "transient_model_web_search_q3",
                OPENAI_RESPONSES_ENDPOINT,
                value=discovery_summary,
                note="No untrusted model citation survived the bounded URL nomination filter.",
            )
            time.sleep(args.min_interval)
            continue

        verified_website: dict | None = None
        verified_assessment: dict | None = None
        independent_url: str | None = None
        attempted_crawls = 0

        for candidate in selected:
            attempted_crawls += 1
            website, web_ops = fetch_bounded_homepage(
                candidate["url"],
                source_type="model_search_discovered_company_website",
                timeout=args.crawl_timeout,
            )
            crawl_requests += int(web_ops.get("requests") or 0)
            crawl_bytes += int(web_ops.get("bytes") or 0)
            crawl_latencies.extend(int(value) for value in web_ops.get("latencies_ms", []) if value is not None)

            gated = apply_website_identity_gate(row, website)
            website = gated["website"]
            assessment = qualify_search_discovered_website(row, website, gated.get("assessment"))
            if assessment and assessment.get("publishable") and _has_conflicting_explicit_org_number(row, website):
                assessment = _conflict_quarantine(assessment)
            if assessment is not None:
                (website.get("value") or {})["identity_assessment"] = assessment

            website["source_type"] = "model_search_discovered_company_website"
            website["source_class"] = "company_owned_candidate"
            publishable = bool(assessment and assessment.get("publishable") and website.get("status") == "available")
            counts["independent_crawls"] += 1
            if publishable:
                verified_website = website
                verified_assessment = assessment
                independent_url = (website.get("value") or {}).get("final_url") or website.get("source_url")
                counts["verified_sites"] += 1
                break
            counts["quarantined_sites"] += 1
            time.sleep(args.min_interval)

        discovery_summary["independent_crawl_attempts"] = attempted_crawls
        discovery_summary["verified_after_independent_crawl"] = verified_website is not None
        if verified_website is not None:
            discovery_summary["independent_page_url"] = independent_url
            discovery_summary["independent_identity_status"] = (verified_assessment or {}).get("status")
            discovery_summary["independent_identity_score"] = (verified_assessment or {}).get("score")

        row.setdefault("evidence", {})["website_model_search_discovery"] = evidence(
            "website_model_search_discovery",
            "available" if verified_website is not None else "not_found",
            "transient_model_web_search_then_independent_bounded_crawl_q3",
            OPENAI_RESPONSES_ENDPOINT,
            value=discovery_summary,
            note="Model/search output was transient. Publication depends only on independently fetched exact-company page evidence.",
        )

        # Quarantined/ambiguous pages never enter target-company evidence. Only a page
        # independently proven to belong to the exact legal entity may be retained.
        if verified_website is not None:
            row["evidence"]["website_model_search_candidate"] = verified_website
            if args.promote_verified:
                row["evidence"]["website"] = verified_website
                row["website"] = independent_url or ""
                counts["promoted_sites"] += 1

        time.sleep(args.min_interval)

    write_jsonl(Path(args.output), rows)
    estimated_cost = _estimated_cost_usd(
        web_search_calls=web_search_tool_calls,
        input_tokens=provider_input_tokens,
        output_tokens=provider_output_tokens,
        web_search_usd_per_call=args.web_search_usd_per_call,
        input_usd_per_million=args.input_usd_per_million,
        output_usd_per_million=args.output_usd_per_million,
    )
    report = {
        "generated_at": utc_now(),
        "started_at": started_at,
        "method": "Q3 OpenAI web-search URL nomination -> independent bounded crawl -> current exact-company gate",
        "provider": "OpenAI Responses API web search",
        "provider_endpoint": OPENAI_RESPONSES_ENDPOINT,
        "model": args.model,
        "input_profiles": len(rows),
        "queried_unresolved_profiles": queried,
        "candidate_crawls_per_company_max": args.candidate_crawls,
        "counts": dict(sorted(counts.items())),
        "operations": {
            "provider_requests": provider_requests,
            "provider_bytes": provider_bytes,
            "provider_latency_p50_ms": percentile(provider_latencies, 0.50),
            "provider_latency_p95_ms": percentile(provider_latencies, 0.95),
            "web_search_tool_calls": web_search_tool_calls,
            "web_search_tool_calls_per_profile_ceiling": MAX_WEB_SEARCH_TOOL_CALLS,
            "provider_input_tokens": provider_input_tokens,
            "provider_output_tokens": provider_output_tokens,
            "independent_crawl_requests": crawl_requests,
            "independent_crawl_bytes": crawl_bytes,
            "independent_crawl_latency_p50_ms": percentile(crawl_latencies, 0.50),
            "independent_crawl_latency_p95_ms": percentile(crawl_latencies, 0.95),
            "declared_web_search_usd_per_call": args.web_search_usd_per_call,
            "declared_input_usd_per_million_tokens": args.input_usd_per_million,
            "declared_output_usd_per_million_tokens": args.output_usd_per_million,
            "preflight_external_api_cost_ceiling_usd": preflight_cost_ceiling,
            "configured_external_api_cost_budget_usd": args.max_external_api_cost_usd,
            "estimated_observed_third_party_cost_usd": estimated_cost,
            "wall_runtime_ms": int((time.monotonic() - wall_started) * 1000),
        },
        "raw_provider_response_persisted": False,
        "provider_response_text_persisted": False,
        "quarantined_candidate_pages_persisted": False,
        "promote_verified_enabled": args.promote_verified,
        "qualification": "experiment_only; production integration requires Builderr-supplied key/budget and fresh precision qualification",
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
