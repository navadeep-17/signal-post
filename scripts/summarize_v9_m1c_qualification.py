#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _review_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    review: list[dict[str, Any]] = []
    for row in rows:
        evidence = row.get("evidence") or {}
        candidate = evidence.get("website_model_search_candidate") or {}
        if not isinstance(candidate, dict) or candidate.get("status") != "available":
            continue
        value = candidate.get("value") or {}
        identity = value.get("identity_assessment") or {}
        if not identity.get("publishable"):
            continue
        content_hash = str(candidate.get("content_sha256") or value.get("content_sha256") or "")
        review.append(
            {
                "organisation_number": str(row.get("organisation_number") or ""),
                "legal_name": row.get("name") or ((row.get("canonical_profile") or {}).get("company") or {}).get("legal_name"),
                "municipality": row.get("municipality"),
                "verified_url": value.get("final_url") or candidate.get("source_url"),
                "identity_status": identity.get("status"),
                "identity_score": identity.get("score"),
                "identity_method": identity.get("method"),
                "identity_reasons": identity.get("reasons") or [],
                "content_sha256": content_hash or None,
                "manual_wrong_company_review": "PENDING",
            }
        )
    review.sort(key=lambda item: item["organisation_number"])
    return review


def summarize(
    *,
    cohort_report: dict[str, Any],
    discovery_report: dict[str, Any],
    output_rows: list[dict[str, Any]],
    max_external_cost_usd: float,
    expected_queries: int = 20,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if max_external_cost_usd < 0:
        raise ValueError("max_external_cost_usd cannot be negative")
    queried = int(discovery_report.get("queried_unresolved_profiles") or 0)
    counts = discovery_report.get("counts") or {}
    verified = int(counts.get("verified_sites") or 0)
    provider_errors = int(counts.get("provider_errors") or 0)
    operations = discovery_report.get("operations") or {}
    cost = float(operations.get("estimated_third_party_cost_usd") or 0.0)
    review = _review_rows(output_rows)

    hard_failures: list[str] = []
    if int(cohort_report.get("selected_unresolved") or 0) != expected_queries:
        hard_failures.append("cohort did not contain the expected unresolved company count")
    if cohort_report.get("model_or_search_called") is not False:
        hard_failures.append("cohort preparation unexpectedly called a model/search provider")
    if queried != expected_queries:
        hard_failures.append(f"model search queried {queried}, expected {expected_queries}")
    if provider_errors:
        hard_failures.append(f"provider_errors={provider_errors}")
    if cost > max_external_cost_usd:
        hard_failures.append(f"estimated provider cost {cost:.6f} exceeds declared ceiling {max_external_cost_usd:.6f}")
    if discovery_report.get("raw_provider_response_persisted") is not False:
        hard_failures.append("raw provider response persistence boundary failed")
    if discovery_report.get("provider_response_text_persisted") is not False:
        hard_failures.append("provider response text persistence boundary failed")
    if discovery_report.get("quarantined_candidate_pages_persisted") is not False:
        hard_failures.append("quarantined candidate page persistence boundary failed")
    if len(review) != verified:
        hard_failures.append(f"verified-site report/output mismatch: report={verified}, review_rows={len(review)}")
    for item in review:
        if not str(item.get("verified_url") or "").startswith(("http://", "https://")):
            hard_failures.append(f"verified row missing URL for {item['organisation_number']}")
        if len(str(item.get("content_sha256") or "")) != 64:
            hard_failures.append(f"verified row missing destination hash for {item['organisation_number']}")
        if item.get("identity_status") not in {"exact", "high_confidence"}:
            hard_failures.append(f"verified row lacks exact/high-confidence identity for {item['organisation_number']}")

    if hard_failures:
        decision = "HARD_FAIL"
    elif verified >= 5:
        decision = "PROVISIONAL_GO_PENDING_MANUAL_WRONG_COMPANY_AUDIT"
    elif verified >= 3:
        decision = "HOLD_PENDING_MANUAL_AUDIT"
    else:
        decision = "NO_GO_LOW_YIELD"

    summary = {
        "schema_version": "signalpost-v9-m1c-qualification-summary-v1",
        "decision": decision,
        "hard_failures": hard_failures,
        "fresh_pool_companies_touched": int(cohort_report.get("fresh_cohort_consumed_by_this_step") or 0),
        "selected_unresolved": int(cohort_report.get("selected_unresolved") or 0),
        "queried_unresolved_profiles": queried,
        "verified_sites": verified,
        "verified_site_rate": round(verified / queried, 4) if queried else 0.0,
        "manual_review_rows": len(review),
        "manual_wrong_company_review_required": bool(review),
        "provider_errors": provider_errors,
        "provider_requests": int(operations.get("provider_requests") or 0),
        "web_search_tool_calls": int(operations.get("web_search_tool_calls") or 0),
        "independent_crawl_requests": int(operations.get("independent_crawl_requests") or 0),
        "estimated_third_party_cost_usd": cost,
        "declared_cost_ceiling_usd": max_external_cost_usd,
        "cost_within_ceiling": cost <= max_external_cost_usd,
        "provider_output_transient": (
            discovery_report.get("raw_provider_response_persisted") is False
            and discovery_report.get("provider_response_text_persisted") is False
        ),
        "quarantined_pages_not_persisted": discovery_report.get("quarantined_candidate_pages_persisted") is False,
        "go_threshold": ">=5 verified exact sites out of 20, zero wrong-company publications after manual audit",
        "hold_threshold": "3-4 verified exact sites out of 20",
        "no_go_threshold": "<3 verified exact sites out of 20",
        "important": (
            "PROVISIONAL_GO is never sufficient for promotion. Every accepted website must receive manual wrong-company review; "
            "any material wrong-company publication is an automatic NO-GO."
        ),
    }
    return summary, review


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize V9 M1c website-discovery qualification without replacing manual identity audit.")
    parser.add_argument("--cohort-report", required=True)
    parser.add_argument("--discovery-report", required=True)
    parser.add_argument("--output", required=True, help="Model-search output JSONL")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--manual-review", required=True)
    parser.add_argument("--max-external-cost-usd", type=float, required=True)
    parser.add_argument("--expected-queries", type=int, default=20)
    args = parser.parse_args()

    cohort = json.loads(Path(args.cohort_report).read_text(encoding="utf-8"))
    discovery = json.loads(Path(args.discovery_report).read_text(encoding="utf-8"))
    rows = read_jsonl(Path(args.output))
    summary, review = summarize(
        cohort_report=cohort,
        discovery_report=discovery,
        output_rows=rows,
        max_external_cost_usd=args.max_external_cost_usd,
        expected_queries=args.expected_queries,
    )
    Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.manual_review).write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in review),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["decision"] == "HARD_FAIL":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
