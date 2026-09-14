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
from norway_company_agent.refresh_contract import (  # noqa: E402
    group_refresh_events,
    validate_refresh_change,
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_refresh_events(path: Path | None) -> list[dict]:
    if path is None:
        return []
    body = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(body, dict):
        events = body.get("events", [])
    elif isinstance(body, list):
        events = body
    else:
        raise ValueError("Refresh report must be a JSON object with events[] or a JSON array")
    if not isinstance(events, list) or not all(isinstance(item, dict) for item in events):
        raise ValueError("Refresh events must be a list of objects")
    return events


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
    parser.add_argument(
        "--refresh-report",
        help="Optional JSON refresh report containing events[] from run_refresh_replay.py.",
    )
    args = parser.parse_args()

    envelopes = read_jsonl(Path(args.input))
    if len(envelopes) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} internal envelopes, received {len(envelopes)}")

    envelope_orgs = [str(item.get("organisation_number") or "") for item in envelopes]
    if len(envelope_orgs) != len(set(envelope_orgs)):
        raise SystemExit("Internal envelopes contain duplicate organisation numbers")
    expected_orgs = set(envelope_orgs)

    try:
        refresh_events = read_refresh_events(Path(args.refresh_report) if args.refresh_report else None)
        changes_by_org = group_refresh_events(refresh_events, expected_organisation_numbers=expected_orgs)
    except ValueError as exc:
        raise SystemExit(f"Invalid refresh report: {exc}") from exc

    projected = [
        project_terminal_envelope(
            envelope,
            third_party_cost_usd=0.0,
            changes=changes_by_org.get(str(envelope.get("organisation_number") or ""), []),
        )
        for envelope in envelopes
    ]
    validation_errors = []
    change_validation_errors = []
    for item in projected:
        org = item.get("organisation_number")
        for error in validate_contract_object(item):
            validation_errors.append({"organisation_number": org, "error": error})
        for change in item.get("changes") or []:
            for error in validate_refresh_change(change, expected_org=str(org or "")):
                change_validation_errors.append(
                    {
                        "organisation_number": org,
                        "field": change.get("field"),
                        "error": error,
                    }
                )

    orgs = [item["organisation_number"] for item in projected]
    attached_change_count = sum(len(item.get("changes") or []) for item in projected)
    checks = {
        "exact_expected_count": len(projected) == args.expected_count,
        "unique_organisation_numbers": len(orgs) == len(set(orgs)),
        "all_contract_objects_valid": not validation_errors,
        "all_refresh_changes_valid": not change_validation_errors,
        "refresh_events_attached_exactly_once": attached_change_count == len(refresh_events),
        "zero_third_party_cost": all(float(item["operations"]["third_party_cost_usd"]) == 0.0 for item in projected),
    }
    report = {
        "input_envelopes": len(envelopes),
        "projected_objects": len(projected),
        "refresh_report_used": bool(args.refresh_report),
        "refresh_events": len(refresh_events),
        "profiles_with_changes": sum(1 for item in projected if item.get("changes")),
        "attached_changes": attached_change_count,
        "checks": checks,
        "passed": all(checks.values()),
        "validation_errors": validation_errors,
        "change_validation_errors": change_validation_errors,
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
