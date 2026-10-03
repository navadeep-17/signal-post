#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_contact import (  # noqa: E402
    attach_company_site_contact_email_observations,
)
from norway_company_agent.final_site_discovery import (  # noqa: E402
    _merge_secondary_page,
    fetch_bounded_homepage,
)
from norway_company_agent.zero_network_contact_recovery import (  # noqa: E402
    recover_secondary_contact_email_observations,
)

MAX_LOGICAL_REQUESTS_PER_SITE = 4


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _mark_reused_exact(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("status") != "available":
        return record
    value = record.get("value") or {}
    value["identity_assessment"] = {
        "status": "exact",
        "publishable": True,
        "score": 1.0,
        "method": "reused_previously_qualified_website_for_m5_screen",
    }
    record["value"] = value
    return record


def screen_profile(profile: dict[str, Any], *, timeout: float) -> tuple[dict[str, Any], dict[str, Any]]:
    org = str(profile.get("organisation_number") or "")
    verified_url = str(profile.get("website") or "").strip()
    metrics = {"logical_requests": 0, "bytes": 0, "latencies_ms": []}

    primary, primary_ops = fetch_bounded_homepage(
        verified_url,
        source_type="v9_m5_reused_verified_company_website",
        timeout=timeout,
    )
    metrics["logical_requests"] += int(primary_ops.get("requests") or 0)
    metrics["bytes"] += int(primary_ops.get("bytes") or 0)
    metrics["latencies_ms"].extend(int(v) for v in primary_ops.get("latencies_ms") or [])
    primary = _mark_reused_exact(primary)

    result: dict[str, Any] = {
        "organisation_number": org,
        "verified_website": verified_url,
        "homepage_status": primary.get("status"),
        "identity_links": [],
        "secondary_attempted": False,
        "primary_contact_emails": [],
        "incremental_secondary_contact_emails": [],
    }
    if primary.get("status") != "available":
        return result, metrics

    row = {
        "organisation_number": org,
        "evidence": {"website": primary},
        "external_observations": [],
    }
    attach_company_site_contact_email_observations(row)
    result["primary_contact_emails"] = sorted(
        {
            str(item.get("contact_email") or "")
            for item in row.get("external_observations") or []
            if isinstance(item, dict) and item.get("contact_email")
        }
    )

    identity_links = list(((primary.get("value") or {}).get("identity_links") or []))
    result["identity_links"] = identity_links[:8]
    if identity_links and metrics["logical_requests"] + 2 <= MAX_LOGICAL_REQUESTS_PER_SITE:
        secondary_url = str(identity_links[0])
        result["secondary_attempted"] = True
        secondary, secondary_ops = fetch_bounded_homepage(
            secondary_url,
            source_type="v9_m5_reused_secondary_identity_page",
            timeout=timeout,
        )
        metrics["logical_requests"] += int(secondary_ops.get("requests") or 0)
        metrics["bytes"] += int(secondary_ops.get("bytes") or 0)
        metrics["latencies_ms"].extend(int(v) for v in secondary_ops.get("latencies_ms") or [])
        if _merge_secondary_page(primary, secondary):
            row["evidence"]["website"] = primary
            recovered = recover_secondary_contact_email_observations(row)
            result["incremental_secondary_contact_emails"] = [
                {
                    "contact_email": item.get("contact_email"),
                    "source_url": item.get("source_url"),
                    "content_sha256": item.get("content_sha256"),
                    "strategy": item.get("strategy"),
                    "network_requests_added": (item.get("metrics") or {}).get("network_requests_added"),
                }
                for item in recovered
            ]

    assert metrics["logical_requests"] <= MAX_LOGICAL_REQUESTS_PER_SITE, (result, metrics)
    return result, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="V9 M5 reused-site zero-network secondary contact recovery screen.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=6.0)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    profiles = read_jsonl(Path(args.profiles))
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    total_requests = 0
    total_bytes = 0
    attempted = 0

    for profile in profiles:
        if attempted >= args.limit:
            break
        if not str(profile.get("website") or "").strip():
            counts["missing_verified_url"] += 1
            continue
        attempted += 1
        row, metrics = screen_profile(profile, timeout=args.timeout)
        rows.append(row)
        total_requests += int(metrics.get("logical_requests") or 0)
        total_bytes += int(metrics.get("bytes") or 0)
        if row.get("homepage_status") == "available":
            counts["homepage_available"] += 1
        if row.get("identity_links"):
            counts["companies_with_secondary_identity_link"] += 1
        if row.get("secondary_attempted"):
            counts["secondary_attempted"] += 1
        if row.get("primary_contact_emails"):
            counts["companies_with_primary_contact_email"] += 1
        incremental = row.get("incremental_secondary_contact_emails") or []
        if incremental:
            counts["companies_with_incremental_secondary_email"] += 1
            counts["incremental_secondary_emails"] += len(incremental)

    write_jsonl(Path(args.output), rows)
    report = {
        "schema_version": "signalpost-v9-m5-zero-network-contact-screen-v1",
        "input_profiles": len(profiles),
        "verified_sites_attempted": attempted,
        "counts": dict(sorted(counts.items())),
        "operations": {
            "development_screen_logical_requests": total_requests,
            "development_screen_request_ceiling": attempted * MAX_LOGICAL_REQUESTS_PER_SITE,
            "bytes": total_bytes,
            "production_requests_added_by_recovery": 0,
            "third_party_api_cost_usd": 0.0,
        },
        "production_integration": False,
        "qualification": "reused_sites_only_no_fresh_cohort_consumed",
        "claim_boundary": (
            "Recovery itself is zero-network and only reads the exact URL/hash retained as the H1c secondary identity page. "
            "This development screen re-fetches reused already-qualified sites solely to measure prospective yield."
        ),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
