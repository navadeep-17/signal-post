#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from norway_company_agent.company_site_activity import probe_company_activity
from norway_company_agent.external_footprint import validate_observation


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure H2b dated company-owned activity yield without modifying the production runner."
    )
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--observations", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=6.0)
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    profiles = read_jsonl(Path(args.profiles))
    results: dict[str, tuple[list[dict[str, Any]], dict[str, Any]]] = {}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(probe_company_activity, profile, timeout=args.timeout): str(profile["organisation_number"])
            for profile in profiles
        }
        for future in as_completed(futures):
            org = futures[future]
            results[org] = future.result()

    observations: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    validation_errors: list[dict[str, str]] = []
    status_counts: Counter[str] = Counter()
    total_requests = 0
    total_bytes = 0

    for profile in profiles:
        org = str(profile["organisation_number"])
        rows, metrics = results[org]
        requests = int(metrics.get("requests") or 0)
        if requests > 4:
            raise RuntimeError(f"H2b probe exceeded 4 logical requests for {org}: {requests}")
        total_requests += requests
        total_bytes += int(metrics.get("bytes") or 0)
        status_counts[str(metrics.get("status") or "unknown")] += 1
        observations.extend(rows)

        website = ((profile.get("evidence") or {}).get("website") or {})
        value = website.get("value") or {}
        identity = value.get("identity_assessment") or {}
        for item in rows:
            errors = validate_observation(item)
            validation_errors.extend(
                {
                    "organisation_number": org,
                    "observation_id": str(item.get("id") or ""),
                    "error": error,
                }
                for error in errors
            )
            audit.append(
                {
                    "organisation_number": org,
                    "legal_name": profile.get("name"),
                    "verified_website": value.get("final_url") or website.get("source_url"),
                    "website_identity_method": identity.get("method"),
                    "website_identity_score": identity.get("score"),
                    "activity_page": item.get("source_url"),
                    "title": item.get("title"),
                    "published_at": item.get("published_at"),
                    "item_url": item.get("item_url"),
                    "content_sha256": item.get("content_sha256"),
                    "observation_id": item.get("id"),
                    "claim_scope": (item.get("metrics") or {}).get("claim_scope"),
                }
            )

    observations.sort(key=lambda row: (str(row.get("organisation_number") or ""), str(row.get("published_at") or ""), str(row.get("id") or "")))
    audit.sort(key=lambda row: (str(row.get("organisation_number") or ""), str(row.get("published_at") or ""), str(row.get("observation_id") or "")))

    write_jsonl(Path(args.observations), observations)
    write_jsonl(Path(args.audit), audit)

    companies_with_activity = len({str(item.get("organisation_number") or "") for item in observations})
    publishable_sites = sum(
        1
        for profile in profiles
        if (((profile.get("evidence") or {}).get("website") or {}).get("status") == "available")
        and bool(((((profile.get("evidence") or {}).get("website") or {}).get("value") or {}).get("identity_assessment") or {}).get("publishable"))
    )
    report = {
        "profiles": len(profiles),
        "publishable_verified_sites": publishable_sites,
        "observations": len(observations),
        "companies_with_activity": companies_with_activity,
        "company_activity_reach_over_all_profiles": round(companies_with_activity / len(profiles), 6) if profiles else 0.0,
        "company_activity_reach_over_verified_sites": round(companies_with_activity / publishable_sites, 6) if publishable_sites else 0.0,
        "status_counts": dict(sorted(status_counts.items())),
        "experimental_logical_requests": total_requests,
        "experimental_bytes": total_bytes,
        "validation_errors": validation_errors,
        "passed": not validation_errors,
        "claim_boundary": "Only explicitly dated items listed on a verified company-owned activity page; article bodies and external platforms are not fetched.",
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if validation_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
