#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.evidence import evidence, utc_now  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.zero_cost_discovery import (  # noqa: E402
    deterministic_domain_candidates,
    fetch_candidate_homepage,
    qualify_deterministic_domain_identity,
)


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


def process_profile(profile: dict, *, timeout: float, max_candidates: int, promote: bool) -> tuple[dict, dict]:
    row = deepcopy(profile)
    plan = deterministic_domain_candidates(row, max_candidates=max_candidates)
    metrics = {
        "organisation_number": str(row.get("organisation_number") or ""),
        "eligible": plan["eligible"],
        "reason": plan["reason"],
        "candidate_attempts": 0,
        "requests": 0,
        "bytes": 0,
        "latencies_ms": [],
        "promoted": False,
        "selected_domain": None,
        "quarantined": 0,
    }
    if not plan["eligible"]:
        return row, metrics

    summaries = []
    for candidate in plan["candidates"]:
        metrics["candidate_attempts"] += 1
        website, ops = fetch_candidate_homepage(candidate["url"], timeout=timeout)
        metrics["requests"] += int(ops.get("requests") or 0)
        metrics["bytes"] += int(ops.get("bytes") or 0)
        metrics["latencies_ms"].extend(int(value) for value in (ops.get("latencies_ms") or []))

        gated = apply_website_identity_gate(row, website)
        website = gated["website"]
        assessment = qualify_deterministic_domain_identity(row, candidate["domain"], website, gated.get("assessment"))
        value = website.get("value") or {}
        if assessment is not None:
            value["identity_assessment"] = assessment
            website["value"] = value

        publishable = bool(assessment and assessment.get("publishable") and website.get("status") == "available")
        summaries.append({
            "domain": candidate["domain"],
            "strategy": candidate["strategy"],
            "website_status": website.get("status"),
            "identity_status": (assessment or {}).get("status"),
            "identity_score": (assessment or {}).get("score"),
            "publishable": publishable,
            "final_url": value.get("final_url") if publishable else None,
        })
        if publishable:
            metrics["selected_domain"] = candidate["domain"]
            metrics["promoted"] = bool(promote)
            row.setdefault("evidence", {})["website_discovery_zero_cost"] = evidence(
                "website_discovery_zero_cost",
                "available",
                "deterministic_legal_name_domain_guess",
                website.get("source_url") or candidate["url"],
                value={
                    "candidate_strategy": candidate["strategy"],
                    "candidate_domain": candidate["domain"],
                    "independent_page_url": value.get("final_url"),
                    "third_party_cost_usd": 0.0,
                },
                note="No search API used; deterministic .no candidate independently fetched and exact-entity gated.",
                content_sha256=website.get("content_sha256"),
            )
            row["evidence"]["website_discovered_zero_cost"] = website
            if promote:
                row["evidence"]["website"] = website
            break
        metrics["quarantined"] += 1

    if not metrics["selected_domain"]:
        row.setdefault("evidence", {})["website_discovery_zero_cost"] = evidence(
            "website_discovery_zero_cost",
            "not_found",
            "deterministic_legal_name_domain_guess",
            "https://data.brreg.no/enhetsregisteret/api/enheter",
            value={"attempts": summaries, "third_party_cost_usd": 0.0},
            note="No deterministic legal-name .no candidate passed independent exact-entity verification.",
        )
    return row, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Zero-cost deterministic .no discovery followed by independent exact-entity verification.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--max-candidates", type=int, default=2, choices=(1, 2))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0, help="0 means process every profile")
    parser.add_argument("--promote-verified", action="store_true")
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be positive")
    profiles = read_jsonl(Path(args.input))
    indexed = list(enumerate(profiles[: args.limit] if args.limit else profiles))
    output = list(profiles)
    started_at = utc_now()
    wall_start = time.monotonic()
    results: list[dict] = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                process_profile,
                profile,
                timeout=args.timeout,
                max_candidates=args.max_candidates,
                promote=args.promote_verified,
            ): index
            for index, profile in indexed
        }
        for future in as_completed(futures):
            index = futures[future]
            row, metrics = future.result()
            output[index] = row
            results.append(metrics)

    write_jsonl(Path(args.output), output)
    counts = Counter()
    latencies: list[int] = []
    for result in results:
        counts["eligible"] += int(bool(result["eligible"]))
        counts["candidate_attempts"] += result["candidate_attempts"]
        counts["requests"] += result["requests"]
        counts["bytes"] += result["bytes"]
        counts["promoted"] += int(bool(result["promoted"]))
        counts["verified_candidate"] += int(bool(result["selected_domain"]))
        counts["quarantined"] += result["quarantined"]
        latencies.extend(result["latencies_ms"])

    promoted = [
        {"organisation_number": item["organisation_number"], "domain": item["selected_domain"]}
        for item in results if item["selected_domain"]
    ]
    report = {
        "generated_at": utc_now(),
        "started_at": started_at,
        "strategy": "h1c_deterministic_legal_name_no_domain_v1",
        "input_profiles": len(profiles),
        "processed_profiles": len(indexed),
        "max_candidates_per_company": args.max_candidates,
        "workers": args.workers,
        "timeout_seconds": args.timeout,
        "wall_runtime_ms": int((time.monotonic() - wall_start) * 1000),
        "third_party_cost_usd": 0.0,
        "search_api_requests": 0,
        "counts": dict(counts),
        "request_latency_ms": {"p50": percentile(latencies, 0.5), "p95": percentile(latencies, 0.95)},
        "promotions": sorted(promoted, key=lambda item: item["organisation_number"]),
        "promote_verified_enabled": args.promote_verified,
        "policy": "A guessed domain is never evidence. Publication requires an independently fetched page to pass the normal website gate plus the H1c page-identity guard.",
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
