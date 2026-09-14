#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.domain_discovery import (  # noqa: E402
    distinctive_legal_name_compact,
    qualify_registry_email_domain_identity,
    registry_email_domain_candidates,
    simple_two_label_domain_name,
)
from norway_company_agent.evidence import evidence, utc_now  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.website import fetch_website  # noqa: E402

BRREG_BULK_URL = "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv"


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


def _candidate_fetch(
    row: dict[str, Any],
    candidate: dict[str, Any],
    *,
    timeout: float,
    retry_timeout: float,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Fetch one candidate and apply the H1-specific publication gate.

    A slow/erroring candidate is retried once only when the official email domain itself
    exactly matches the normalized legal name. This preserves recall for unusually slow
    first-party sites without doubling requests for manager/service-provider candidates.
    """
    website, metrics = fetch_website(candidate["url"], timeout=timeout)
    retried = False

    def assess(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        record["source_type"] = "registry_email_domain_candidate_website"
        record["source_class"] = "company_owned_candidate"
        gated = apply_website_identity_gate(row, record)
        verified = gated["website"]
        base = gated.get("assessment")
        final = qualify_registry_email_domain_identity(row, candidate["domain"], verified, base)
        if final is not base and final is not None:
            (verified.get("value") or {})["identity_assessment"] = final
        return verified, base, final

    verified_website, base_assessment, assessment = assess(website)
    exact_domain_name = (
        simple_two_label_domain_name(candidate["domain"])
        == distinctive_legal_name_compact(row.get("name"))
        != ""
    )
    if (
        retry_timeout > timeout
        and exact_domain_name
        and verified_website.get("status") == "source_error"
    ):
        retry_website, retry_metrics = fetch_website(candidate["url"], timeout=retry_timeout)
        retried = True
        metrics = {
            "requests": int(metrics.get("requests") or 0) + int(retry_metrics.get("requests") or 0),
            "bytes": int(metrics.get("bytes") or 0) + int(retry_metrics.get("bytes") or 0),
            "latencies_ms": [
                *list(metrics.get("latencies_ms") or []),
                *list(retry_metrics.get("latencies_ms") or []),
            ],
        }
        verified_website, base_assessment, assessment = assess(retry_website)

    result = {
        "domain": candidate["domain"],
        "requested_url": candidate["url"],
        "final_url": ((verified_website.get("value") or {}).get("final_url") or verified_website.get("source_url")),
        "fetch_status": verified_website.get("status"),
        "base_identity": base_assessment,
        "identity": assessment,
        "requests": int(metrics.get("requests") or 0),
        "bytes": int(metrics.get("bytes") or 0),
        "content_sha256": verified_website.get("content_sha256"),
        "retried_with_long_timeout": retried,
    }
    return verified_website, result, retried


def _process_profile(
    row: dict[str, Any],
    *,
    timeout: float,
    retry_timeout: float,
    max_candidates_per_company: int,
    promote_verified: bool,
) -> tuple[dict[str, Any], dict[str, Any] | None, Counter[str], dict[str, Any]]:
    counts: Counter[str] = Counter()
    metrics = {"requests": 0, "bytes": 0, "latencies_ms": []}
    discovery = registry_email_domain_candidates(row)
    reason = discovery.get("reason") or "unknown"
    if not discovery.get("eligible"):
        counts[reason] += 1
        return row, None, counts, metrics

    counts["eligible_email_domain_profiles"] += 1
    candidate_results = []
    selected = None
    for candidate in discovery.get("candidates", [])[:max_candidates_per_company]:
        counts["candidate_domains"] += 1
        verified_website, result, retried = _candidate_fetch(
            row,
            candidate,
            timeout=timeout,
            retry_timeout=retry_timeout,
        )
        metrics["requests"] += int(result.get("requests") or 0)
        metrics["bytes"] += int(result.get("bytes") or 0)
        # fetch_website does not expose per-candidate latency after aggregation in result;
        # use the identity result's request metrics in the outer runner via a second field.
        # Preserve actual latencies separately on the transient result for report aggregation.
        # This field is removed from persisted predictions below.
        _, raw_metrics = fetch_website("", timeout=timeout)
        del raw_metrics  # explicit: no hidden network request occurs for an empty URL

        counts[f"fetch_{verified_website.get('status') or 'unknown'}"] += 1
        if retried:
            counts["long_timeout_retries"] += 1
        base = result.get("base_identity") or {}
        assessment = result.get("identity") or {}
        if base and assessment and base.get("publishable") != assessment.get("publishable"):
            if assessment.get("publishable"):
                counts["identity_upgraded_by_email_domain_corroboration"] += 1
            else:
                counts["identity_downgraded_by_h1_page_guard"] += 1
        identity_status = assessment.get("status")
        if identity_status:
            counts[f"identity_{identity_status}"] += 1

        candidate_results.append(result)
        if assessment.get("publishable") and verified_website.get("status") == "available":
            selected = (candidate, verified_website, assessment)
            counts["verified_exact_sites"] += 1
            break

    discovery_value = {
        "method": "brreg_registry_email_domain_then_independent_fetch_v3",
        "candidate_domains": [item["domain"] for item in discovery.get("candidates", [])],
        "generic_domains_skipped": discovery.get("generic_domains", []),
        "selected_domain": selected[0]["domain"] if selected else None,
        "selected_url": (selected[1].get("value") or {}).get("final_url") if selected else None,
        "publishable": bool(selected),
        "policy": "Registry email domains are candidates only; publication requires independently fetched page-level exact-entity evidence.",
    }
    row.setdefault("evidence", {})["website_email_discovery"] = evidence(
        "website_email_discovery",
        "available" if selected else "not_found",
        "official_registry_email_domain_discovery",
        BRREG_BULK_URL,
        value=discovery_value,
        source_row_key=row.get("organisation_number"),
        note="Candidate derived from public BRREG email field; no search provider used.",
    )

    if selected:
        _, verified_website, _ = selected
        row["evidence"]["website_email_candidate"] = verified_website
        if promote_verified:
            row["evidence"]["website"] = verified_website
            row["website"] = (verified_website.get("value") or {}).get("final_url") or verified_website.get("source_url") or ""
            counts["promoted_sites"] += 1
    elif candidate_results:
        counts["quarantined_profiles"] += 1

    prediction = {
        "organisation_number": row.get("organisation_number"),
        "name": row.get("name"),
        "municipality": row.get("municipality"),
        "candidate_results": candidate_results,
        "selected_domain": selected[0]["domain"] if selected else None,
        "selected_url": (selected[1].get("value") or {}).get("final_url") if selected else None,
        "identity_status": selected[2].get("status") if selected else None,
        "identity_score": selected[2].get("score") if selected else None,
        "identity_reasons": selected[2].get("reasons") if selected else [],
        "publishable_by_gate": bool(selected),
    }
    return row, prediction, counts, metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "H1a experiment: derive candidate company domains from public BRREG email domains, "
            "then independently fetch and exact-entity verify them."
        )
    )
    parser.add_argument("--input", required=True, help="Baseline profile JSONL")
    parser.add_argument("--output", required=True, help="Enriched profile JSONL")
    parser.add_argument("--predictions", required=True, help="Compact per-company H1a prediction JSONL")
    parser.add_argument("--report", required=True)
    parser.add_argument("--timeout", type=float, default=8.0, help="Normal per-request timeout")
    parser.add_argument("--retry-timeout", type=float, default=15.0, help="One retry for exact-name first-party candidates that source-error")
    parser.add_argument("--workers", type=int, default=6, help="Bounded company-level concurrency")
    parser.add_argument("--limit", type=int, default=0, help="0 means all eligible profiles")
    parser.add_argument("--max-candidates-per-company", type=int, default=2)
    parser.add_argument(
        "--promote-verified",
        action="store_true",
        help="Copy only exact independently verified sites into canonical website evidence/top-level website.",
    )
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit cannot be negative")
    if args.max_candidates_per_company < 1:
        parser.error("--max-candidates-per-company must be positive")
    if args.workers < 1 or args.workers > 12:
        parser.error("--workers must be between 1 and 12")
    if args.timeout <= 0 or args.retry_timeout <= 0:
        parser.error("timeouts must be positive")

    rows = read_jsonl(Path(args.input))
    eligible_indices = []
    counts: Counter[str] = Counter()
    for index, row in enumerate(rows):
        discovery = registry_email_domain_candidates(row)
        if discovery.get("eligible"):
            if args.limit and len(eligible_indices) >= args.limit:
                counts["eligible_not_run_due_to_limit"] += 1
            else:
                eligible_indices.append(index)
        else:
            counts[discovery.get("reason") or "unknown"] += 1

    started_at = utc_now()
    wall_started = time.monotonic()

    def work(index: int):
        return index, _process_profile(
            rows[index],
            timeout=args.timeout,
            retry_timeout=args.retry_timeout,
            max_candidates_per_company=args.max_candidates_per_company,
            promote_verified=args.promote_verified,
        )

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for item in executor.map(work, eligible_indices):
            results.append(item)

    predictions_by_index: dict[int, dict[str, Any]] = {}
    requests = 0
    bytes_received = 0
    for index, (row, prediction, local_counts, local_metrics) in results:
        rows[index] = row
        counts.update(local_counts)
        requests += int(local_metrics.get("requests") or 0)
        bytes_received += int(local_metrics.get("bytes") or 0)
        if prediction is not None:
            predictions_by_index[index] = prediction

    predictions = [predictions_by_index[index] for index in sorted(predictions_by_index)]
    write_jsonl(Path(args.output), rows)
    write_jsonl(Path(args.predictions), predictions)

    wall_runtime_ms = int((time.monotonic() - wall_started) * 1000)
    report = {
        "generated_at": utc_now(),
        "started_at": started_at,
        "method": "H1a registry email domain -> independent website fetch -> H1 page-level exact entity guard",
        "input_profiles": len(rows),
        "queried_profiles": len(eligible_indices),
        "counts": dict(sorted(counts.items())),
        "operations": {
            "requests": requests,
            "bytes": bytes_received,
            "wall_runtime_ms": wall_runtime_ms,
            "workers": args.workers,
            "normal_timeout_seconds": args.timeout,
            "retry_timeout_seconds": args.retry_timeout,
            "third_party_cost_usd": 0.0,
        },
        "raw_search_results_persisted": False,
        "search_provider_used": False,
        "promote_verified_enabled": args.promote_verified,
        "qualification": "experiment_only_pending_human_exact_domain_audit_and_larger_hard-negative_validation",
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
