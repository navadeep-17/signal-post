#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_activity import probe_company_activity  # noqa: E402
from norway_company_agent.external_footprint import validate_observation  # noqa: E402

OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE = 5
FINAL_SITE_REQUEST_CEILING = 4
ACTIVITY_FETCH_REQUESTS_IF_INTEGRATED = 2


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _verified_website(profile: dict[str, Any]) -> bool:
    website = ((profile.get("evidence") or {}).get("website") or {})
    identity = ((website.get("value") or {}).get("identity_assessment") or {})
    return website.get("status") == "available" and bool(identity.get("publishable"))


def _site_logical_requests(profile: dict[str, Any]) -> int:
    total = int((profile.get("run_metrics") or {}).get("logical_requests") or 0)
    return max(0, total - OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE)


def _promotion_compatible(profile: dict[str, Any]) -> bool:
    if not _verified_website(profile):
        return False
    site_requests = _site_logical_requests(profile)
    return site_requests + ACTIVITY_FETCH_REQUESTS_IF_INTEGRATED <= FINAL_SITE_REQUEST_CEILING


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark H2b dated company activity on fresh production profiles.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--observations-output", required=True)
    parser.add_argument("--audit-output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=6.0)
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    profiles = _read_jsonl(Path(args.profiles))
    eligible = [profile for profile in profiles if _promotion_compatible(profile)]

    results: dict[str, tuple[list[dict[str, Any]], dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(probe_company_activity, profile, timeout=args.timeout): str(profile.get("organisation_number") or "")
            for profile in eligible
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    observations: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    validation_errors: list[dict[str, str]] = []
    status_counts: Counter[str] = Counter()
    experimental_requests = 0
    experimental_bytes = 0

    by_org = {str(profile.get("organisation_number") or ""): profile for profile in profiles}
    for org in sorted(results):
        rows, metrics = results[org]
        status_counts[str(metrics.get("status") or "unknown")] += 1
        experimental_requests += int(metrics.get("requests") or 0)
        experimental_bytes += int(metrics.get("bytes") or 0)
        profile = by_org[org]
        website = ((profile.get("evidence") or {}).get("website") or {})
        website_value = website.get("value") or {}
        if rows:
            observations.extend(rows)
        for observation in rows:
            for error in validate_observation(observation):
                validation_errors.append(
                    {"organisation_number": org, "observation_id": str(observation.get("id") or ""), "error": error}
                )
            audit.append(
                {
                    "organisation_number": org,
                    "legal_name": profile.get("name"),
                    "verified_website": website_value.get("final_url") or website.get("source_url"),
                    "production_site_logical_requests": _site_logical_requests(profile),
                    "selected_activity_url": metrics.get("selected_activity_url"),
                    "activity_source_url": observation.get("source_url"),
                    "title": observation.get("title"),
                    "published_at": observation.get("published_at"),
                    "item_url": observation.get("item_url"),
                    "content_sha256": observation.get("content_sha256"),
                    "observation_id": observation.get("id"),
                    "claim_scope": (observation.get("metrics") or {}).get("claim_scope"),
                }
            )

    observations.sort(key=lambda row: (str(row.get("organisation_number") or ""), str(row.get("published_at") or ""), str(row.get("id") or "")))
    audit.sort(key=lambda row: (str(row.get("organisation_number") or ""), str(row.get("published_at") or ""), str(row.get("observation_id") or "")))

    _write_jsonl(Path(args.observations_output), observations)
    _write_jsonl(Path(args.audit_output), audit)

    verified = [profile for profile in profiles if _verified_website(profile)]
    report = {
        "passed": not validation_errors,
        "profiles": len(profiles),
        "verified_websites": len(verified),
        "promotion_compatible_verified_websites": len(eligible),
        "probed_companies": len(results),
        "companies_with_dated_activity": len({str(item.get("organisation_number") or "") for item in observations}),
        "dated_activity_observations": len(observations),
        "status_counts": dict(sorted(status_counts.items())),
        "experimental_logical_requests": experimental_requests,
        "experimental_bytes": experimental_bytes,
        "third_party_cost_usd": 0.0,
        "validation_errors": validation_errors,
        "promotion_model": {
            "current_site_request_ceiling": FINAL_SITE_REQUEST_CEILING,
            "integrated_activity_page_cost": ACTIVITY_FETCH_REQUESTS_IF_INTEGRATED,
            "requires_homepage_link_capture_during_existing_fetch": True,
            "final_request_ceiling_increase_required": False,
        },
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if validation_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
