#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_careers import fetch_career_pages, workforce_observation  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract conservative hiring signals from exact verified company-owned careers pages.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--max-pages", type=int, default=2, choices=(1, 2))
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    profiles = read_jsonl(Path(args.profiles))
    rows: list[dict] = []
    counts = Counter()
    request_latencies: list[int] = []
    errors: list[dict] = []

    def work(profile: dict):
        pages, metrics = fetch_career_pages(
            profile,
            timeout=args.timeout,
            max_pages=args.max_pages,
        )
        return profile, pages, metrics, workforce_observation(profile, pages)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(work, profile) for profile in profiles]
        for future in as_completed(futures):
            profile, pages, metrics, observation = future.result()
            counts["requests"] += int(metrics.get("requests") or 0)
            counts["bytes"] += int(metrics.get("bytes") or 0)
            request_latencies.extend(int(value) for value in metrics.get("latencies_ms") or [])
            if pages:
                counts["companies_with_careers_pages"] += 1
                counts["career_pages"] += len(pages)
                counts["specific_internal_job_links"] += sum(len(page.get("specific_job_links") or []) for page in pages)
            for error in metrics.get("errors") or []:
                if len(errors) < 100:
                    errors.append({"organisation_number": profile.get("organisation_number"), **error})
            if observation:
                rows.append(observation)

    rows.sort(key=lambda item: item["organisation_number"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")

    ordered = sorted(request_latencies)
    percentile = lambda q: ordered[min(len(ordered) - 1, int((len(ordered) - 1) * q))] if ordered else None
    report = {
        "connector": "exact_company_site_careers_v1",
        "profiles": len(profiles),
        "observations": len(rows),
        "counts": dict(counts),
        "request_latency_ms": {"p50": percentile(0.5), "p95": percentile(0.95)},
        "third_party_cost_usd": 0.0,
        "search_api_requests": 0,
        "errors": errors,
        "claim_boundary": "Company-owned careers surface only. A generic careers page is a workforce snapshot, not proof of an active vacancy; specific internal job-link counts are descriptive and not independently verified vacancy totals.",
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
