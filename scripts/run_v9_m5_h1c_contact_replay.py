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
    MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
    discover_final_website,
)
from norway_company_agent.zero_network_contact_recovery import (  # noqa: E402
    recover_secondary_contact_email_observations,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def replay(profile: dict[str, Any], *, timeout: float) -> tuple[dict[str, Any], dict[str, Any]]:
    row, site_metrics = discover_final_website(profile, timeout=timeout)
    website = ((row.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    selected = (
        website.get("status") == "available"
        and assessment.get("publishable") is True
        and str(site_metrics.get("selected_source") or "") == "h1c_deterministic_domain"
    )

    attach_company_site_contact_email_observations(row)
    primary_emails = sorted(
        {
            str(item.get("contact_email") or "")
            for item in row.get("external_observations") or []
            if isinstance(item, dict) and item.get("contact_email")
        }
    )
    recovered = recover_secondary_contact_email_observations(row) if selected else []

    output = {
        "organisation_number": str(row.get("organisation_number") or ""),
        "name": row.get("name"),
        "selected_source": site_metrics.get("selected_source"),
        "verified_website": (value.get("final_url") or website.get("source_url")) if selected else None,
        "publishable": bool(selected),
        "identity_score": assessment.get("score"),
        "identity_method": assessment.get("method"),
        "h1c_secondary_attempted": bool(site_metrics.get("h1c_secondary_attempted")),
        "h1c_secondary_verified": bool(site_metrics.get("h1c_secondary_verified")),
        "secondary_identity_page": value.get("secondary_identity_page"),
        "primary_contact_emails": primary_emails,
        "incremental_secondary_contact_emails": [
            {
                "contact_email": item.get("contact_email"),
                "source_url": item.get("source_url"),
                "content_sha256": item.get("content_sha256"),
                "strategy": item.get("strategy"),
                "network_requests_added": (item.get("metrics") or {}).get("network_requests_added"),
            }
            for item in recovered
        ],
        "site_logical_requests": int(site_metrics.get("requests") or 0),
    }
    assert output["site_logical_requests"] <= MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE, output
    return output, site_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay production H1c on reused V7-selected companies and measure M5 contact recovery.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--timeout", type=float, default=6.0)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    profiles = read_jsonl(Path(args.profiles))
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    requests = 0
    bytes_received = 0

    for profile in profiles:
        row, metrics = replay(profile, timeout=args.timeout)
        rows.append(row)
        requests += int(metrics.get("requests") or 0)
        bytes_received += int(metrics.get("bytes") or 0)
        if row["publishable"]:
            counts["currently_h1c_publishable"] += 1
        if row["h1c_secondary_attempted"]:
            counts["h1c_secondary_attempted"] += 1
        if row["h1c_secondary_verified"]:
            counts["h1c_secondary_verified"] += 1
        if row["secondary_identity_page"]:
            counts["retained_secondary_identity_page"] += 1
        if row["primary_contact_emails"]:
            counts["companies_with_primary_contact_email"] += 1
        incremental = row["incremental_secondary_contact_emails"]
        if incremental:
            counts["companies_with_incremental_secondary_email"] += 1
            counts["incremental_secondary_emails"] += len(incremental)

    write_jsonl(Path(args.output), rows)
    report = {
        "schema_version": "signalpost-v9-m5-h1c-contact-replay-v1",
        "reused_profiles": len(profiles),
        "counts": dict(sorted(counts.items())),
        "operations": {
            "logical_requests": requests,
            "request_ceiling": len(profiles) * MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
            "bytes": bytes_received,
            "production_requests_added_by_recovery": 0,
            "third_party_api_cost_usd": 0.0,
        },
        "production_integration": False,
        "qualification": "reused_v7_h1c_selected_only_no_fresh_cohort_consumed",
        "claim_boundary": (
            "The replay uses the actual production discover_final_website() H1c path. M5 only recovers a contact email when that path "
            "currently retains and verifies the exact secondary identity page; the recovery itself adds zero requests."
        ),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
