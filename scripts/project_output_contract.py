#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.output_contract import (  # noqa: E402
    project_terminal_envelope,
    validate_contract_object,
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Project internal Signalpost terminal envelopes into OUTPUT_CONTRACT.md JSONL.")
    parser.add_argument("--input", required=True, help="Internal terminal envelope JSONL")
    parser.add_argument("--output", required=True, help="Contract-shaped JSONL")
    parser.add_argument("--report", required=True)
    parser.add_argument("--expected-count", type=int, default=100)
    args = parser.parse_args()

    envelopes = read_jsonl(Path(args.input))
    if len(envelopes) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} internal envelopes, received {len(envelopes)}")

    projected = [project_terminal_envelope(envelope, third_party_cost_usd=0.0) for envelope in envelopes]
    validation_errors = []
    for item in projected:
        for error in validate_contract_object(item):
            validation_errors.append({"organisation_number": item.get("organisation_number"), "error": error})

    orgs = [item["organisation_number"] for item in projected]
    checks = {
        "exact_expected_count": len(projected) == args.expected_count,
        "unique_organisation_numbers": len(orgs) == len(set(orgs)),
        "all_contract_objects_valid": not validation_errors,
        "zero_third_party_cost": all(float(item["operations"]["third_party_cost_usd"]) == 0.0 for item in projected),
    }
    report = {
        "input_envelopes": len(envelopes),
        "projected_objects": len(projected),
        "checks": checks,
        "passed": all(checks.values()),
        "validation_errors": validation_errors,
        "claims": sum(len(item["claims"]) for item in projected),
        "evidence_items": sum(len(item["evidence"]) for item in projected),
        "errors": sum(len(item["errors"]) for item in projected),
        "third_party_cost_usd": 0.0,
    }
    if not report["passed"]:
        raise SystemExit(json.dumps(report, ensure_ascii=False, indent=2))

    write_jsonl(Path(args.output), projected)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
