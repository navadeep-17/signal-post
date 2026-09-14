#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import terminal_envelope  # noqa: E402
from norway_company_agent.output_contract import project_terminal_envelope, validate_contract_object  # noqa: E402
from norway_company_agent.refresh import diff_datasets  # noqa: E402
from norway_company_agent.refresh_contract import group_refresh_events, validate_refresh_change  # noqa: E402

from run_refresh_replay import materialize  # noqa: E402


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Qualify refresh events inside final Signalpost contract objects.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    modules = set(manifest["modules"])
    base = manifest["profiles"]
    previous, old_fetcher = materialize(base, manifest["snapshots"]["old"], modules)
    current, new_fetcher = materialize(base, manifest["snapshots"]["new"], modules)
    raw_changes = diff_datasets(previous, current)

    orgs = {row["organisation_number"] for row in current}
    grouped = group_refresh_events(raw_changes, expected_organisation_numbers=orgs)
    started_at = str(manifest["snapshots"]["new"].get("retrieved_at") or "2026-08-02T00:00:00Z")
    completed_at = started_at
    projected = []
    validation_errors = []
    change_validation_errors = []
    for profile in current:
        org = profile["organisation_number"]
        envelope = terminal_envelope(
            profile,
            run_id="refresh-contract-qualification",
            modules=sorted(modules),
            started_at=started_at,
            completed_at=completed_at,
        )
        item = project_terminal_envelope(envelope, changes=grouped[org])
        projected.append(item)
        validation_errors.extend(
            {"organisation_number": org, "error": error}
            for error in validate_contract_object(item)
        )
        for change in item["changes"]:
            change_validation_errors.extend(
                {"organisation_number": org, "field": change.get("field"), "error": error}
                for error in validate_refresh_change(change, expected_org=org)
            )

    observed = {(item["organisation_number"], item["field"]) for item in raw_changes}
    expected = {(item["organisation_number"], item["field"]) for item in manifest.get("expected_changes", [])}
    rerun_changes = diff_datasets(current, current)
    rerun_grouped = group_refresh_events(rerun_changes, expected_organisation_numbers=orgs)
    provenance_complete = all(
        item.get("old_content_sha256")
        and item.get("new_content_sha256")
        and item.get("source_url")
        and item.get("retrieved_at")
        for item in raw_changes
    )
    previous_values_preserved = all(
        change.get("previous_value") is not None
        for item in projected
        for change in item["changes"]
    )
    checks = {
        "expected_changes_exact": observed == expected,
        "contract_objects_valid": not validation_errors,
        "change_objects_valid": not change_validation_errors,
        "all_changes_attached_once": sum(len(item["changes"]) for item in projected) == len(raw_changes),
        "provenance_complete": provenance_complete,
        "previous_values_preserved": previous_values_preserved,
        "idempotent_rerun_empty": rerun_changes == [] and all(not changes for changes in rerun_grouped.values()),
        "source_request_counts_stable": len(old_fetcher.requests) == len(new_fetcher.requests),
    }
    report = {
        "corpus": manifest.get("corpus"),
        "profiles": len(projected),
        "modules": sorted(modules),
        "old_requests": len(old_fetcher.requests),
        "new_requests": len(new_fetcher.requests),
        "expected_changes": len(expected),
        "observed_changes": len(observed),
        "attached_changes": sum(len(item["changes"]) for item in projected),
        "validation_errors": validation_errors,
        "change_validation_errors": change_validation_errors,
        "checks": checks,
        "qualification_passed": all(checks.values()),
    }

    write_jsonl(Path(args.output), projected)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["qualification_passed"] else 1)


if __name__ == "__main__":
    main()
