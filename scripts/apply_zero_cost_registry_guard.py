#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.zero_cost_registry_guard import apply_registry_risk_guard  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply conservative registry-risk revalidation to H1c website promotions.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input))
    output: list[dict] = []
    counts = Counter()
    quarantined: list[dict] = []
    passed: list[dict] = []

    for row in rows:
        guarded, reasons = apply_registry_risk_guard(row)
        output.append(guarded)
        discovery = (guarded.get("evidence") or {}).get("website_discovery_zero_cost") or {}
        if discovery.get("status") != "available":
            continue
        counts["h1c_promotions_seen"] += 1
        value = discovery.get("value") or {}
        domain = value.get("candidate_domain")
        item = {
            "organisation_number": guarded.get("organisation_number"),
            "name": guarded.get("name"),
            "domain": domain,
            "reasons": reasons,
        }
        if reasons:
            counts["quarantined"] += 1
            quarantined.append(item)
        else:
            counts["passed"] += 1
            passed.append(item)

    write_jsonl(Path(args.output), output)
    report = {
        "strategy": "h1c_registry_risk_guard_v1",
        "third_party_cost_usd": 0.0,
        "search_api_requests": 0,
        "network_requests": 0,
        "counts": dict(counts),
        "passed": passed,
        "quarantined": quarantined,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
