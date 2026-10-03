#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from norway_company_agent.targeted_careers_probe import probe_targeted_careers_page


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--max-added-logical-requests", type=int, default=80)
    args = parser.parse_args()

    rows = read_jsonl(args.profiles)
    facts: list[dict[str, Any]] = []
    site_audit: list[dict[str, Any]] = []
    requests = 0
    bytes_received = 0
    errors = 0
    eligible = 0
    started = time.monotonic()

    for profile in rows:
        if requests + 2 > args.max_added_logical_requests:
            break
        fact, metrics = probe_targeted_careers_page(profile, timeout=args.timeout)
        if not metrics.get("eligible"):
            continue
        eligible += 1
        requests += int(metrics.get("requests") or 0)
        bytes_received += int(metrics.get("bytes") or 0)
        errors += len(metrics.get("errors") or [])
        audit = {
            "organisation_number": str(profile.get("organisation_number") or ""),
            "candidate_url": metrics.get("candidate_url"),
            "requests": metrics.get("requests"),
            "errors": metrics.get("errors") or [],
            "qualified": bool(fact),
        }
        site_audit.append(audit)
        if fact:
            facts.append(
                {
                    "organisation_number": str(profile.get("organisation_number") or ""),
                    "fact_type": "careers_signal",
                    "source_url": fact["url"],
                    "title": fact["title"],
                    "marker": fact["marker"],
                    "content_sha256": fact["content_sha256"],
                    "evidence_span": fact["evidence_span"],
                    "claim_scope": fact["claim_scope"],
                }
            )

    report = {
        "schema": "signalpost.v7.m2b.targeted_careers_probe.v1",
        "companies": len(rows),
        "exact_verified_sites_eligible": eligible,
        "careers_signal_companies": len({row["organisation_number"] for row in facts}),
        "careers_signals": len(facts),
        "logical_requests_added": requests,
        "conservative_request_charge_added": requests * 2,
        "bytes_received": bytes_received,
        "errors": errors,
        "wall_runtime_seconds": round(time.monotonic() - started, 3),
        "third_party_api_cost_usd": 0.0,
        "wrong_company_publications": 0,
        "publication_boundary": "experiment only; no production claims are emitted",
        "site_audit": site_audit,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_jsonl(args.facts, facts)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
