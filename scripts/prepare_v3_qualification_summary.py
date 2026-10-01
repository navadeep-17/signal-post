#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(value)
    return rows


def prepare(
    *,
    run_report: dict[str, Any],
    audit: dict[str, Any],
    profiles: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if run_report.get("passed") is not True:
        raise ValueError("production run did not pass")
    if len(outputs) != 100 or len({str(row.get("organisation_number") or "") for row in outputs}) != 100:
        raise ValueError("qualification output must contain exactly 100 unique companies")
    if not all(((row.get("run") or {}).get("terminal_status") == "completed") for row in outputs):
        raise ValueError("not all terminal objects completed")
    request_charge = int((run_report.get("request_budget") or {}).get("observed_conservative_challenge_request_charge") or 0)
    runtime_seconds = float((run_report.get("runtime") or {}).get("wall_runtime_seconds") or 0.0)
    if request_charge > 2000:
        raise ValueError(f"request budget exceeded: {request_charge}")
    if runtime_seconds > 2400:
        raise ValueError(f"runtime budget exceeded: {runtime_seconds}")
    if float((run_report.get("source_policy") or {}).get("third_party_cost_usd") or 0.0) != 0.0:
        raise ValueError("third-party cost is not zero")
    if run_report.get("contract_errors") or run_report.get("change_errors"):
        raise ValueError("contract/change errors present")
    if audit.get("passed") is not True:
        raise ValueError("V3 annual-description audit did not pass")

    manual: list[dict[str, Any]] = []
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        for observation in profile.get("external_observations") or []:
            if not isinstance(observation, dict):
                continue
            if observation.get("signal_type") != "company_profile" or observation.get("platform") != "brreg":
                continue
            description = str(observation.get("company_description") or "").strip()
            if not description:
                continue
            manual.append(
                {
                    "organisation_number": org,
                    "name": profile.get("name"),
                    "description": description,
                    "evidence_span": observation.get("evidence_span"),
                    "source_url": observation.get("source_url"),
                    "effective_at": observation.get("effective_at"),
                    "content_sha256": observation.get("content_sha256"),
                    "strategy": observation.get("strategy"),
                }
            )

    summary = {
        "fresh_companies": 100,
        "selection_overlap": 0,
        "annual_description_observations": int(audit.get("annual_description_observations") or 0),
        "published_annual_description_claims": int(audit.get("published_annual_description_claims") or 0),
        "suppressed_by_stronger_description": int(audit.get("companies_suppressed_by_stronger_existing_description") or 0),
        "same_report_as_workforce": int(audit.get("companies_reusing_same_report_as_workforce") or 0),
        "manual_audit_rows": len(manual),
        "observed_challenge_request_charge": request_charge,
        "runtime_seconds": runtime_seconds,
        "production_passed": True,
        "audit_passed": True,
    }
    return manual, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare V3 qualification manual-audit rows and summary")
    parser.add_argument("--run-report", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manual-output", required=True)
    parser.add_argument("--summary-output", required=True)
    args = parser.parse_args()

    manual, summary = prepare(
        run_report=_read_json(Path(args.run_report)),
        audit=_read_json(Path(args.audit)),
        profiles=_read_jsonl(Path(args.profiles)),
        outputs=_read_jsonl(Path(args.output)),
    )
    manual_path = Path(args.manual_output)
    manual_path.parent.mkdir(parents=True, exist_ok=True)
    manual_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manual),
        encoding="utf-8",
    )
    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
