#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FIELD_FAMILIES = {
    "company_description": {"company_description"},
    "workforce": {"external.workforce_snapshot"},
    "revenue": {"financial.revenue"},
    "roles": {"roles"},
    "locations": {"locations"},
    "verified_websites": {"official_website"},
    "contact_emails": {"external.contact_email"},
    "social_profiles": {"external.profile_handle"},
    "job_postings": {"external.job_posting"},
    "company_authored_updates": {"external.company_update"},
    "registry_changes": {"official_registry_change"},
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _available_claims(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [claim for claim in (row.get("claims") or []) if claim.get("availability") == "available"]


def _company_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {name: 0 for name in FIELD_FAMILIES}
    for row in rows:
        fields = {str(claim.get("field") or "") for claim in _available_claims(row)}
        for name, accepted_fields in FIELD_FAMILIES.items():
            counts[name] += int(bool(fields & accepted_fields))
    return counts


def _website_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        org = str(row.get("organisation_number") or "")
        for claim in _available_claims(row):
            if claim.get("field") != "official_website":
                continue
            value = claim.get("value")
            url = value.get("url") if isinstance(value, dict) else value
            result[org] = {
                "organisation_number": org,
                "url": url,
                "evidence_ids": list(claim.get("evidence_ids") or []),
            }
            break
    return result


def summarize(output_path: Path, report_path: Path) -> dict[str, Any]:
    rows = read_jsonl(output_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    counts = _company_counts(rows)
    request_budget = report.get("request_budget") or {}
    runtime = report.get("runtime") or {}
    return {
        "companies": len(rows),
        **counts,
        "total_claims": sum(len(row.get("claims") or []) for row in rows),
        "evidence_count": sum(len(row.get("evidence") or []) for row in rows),
        "observed_logical_requests": int(request_budget.get("observed_logical_requests") or 0),
        "observed_conservative_requests": int(request_budget.get("observed_conservative_challenge_request_charge") or 0),
        "theoretical_conservative_ceiling": int(request_budget.get("theoretical_challenge_request_charge_ceiling") or 0),
        "runtime_seconds": float(runtime.get("wall_runtime_seconds") or 0.0),
        "contract_errors": len(report.get("contract_errors") or []),
        "change_errors": len(report.get("change_errors") or []),
        "budget_errors": len(report.get("budget_errors") or []),
        "canonical_errors": len(((report.get("canonical_projection") or {}).get("validation_errors") or [])),
        "synthesis_errors": len(((report.get("synthesis") or {}).get("validation_errors") or [])),
        "passed": bool(report.get("passed")),
        "websites": _website_map(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare V5 and V6 on the exact same company cohort.")
    parser.add_argument("--baseline-output", required=True)
    parser.add_argument("--baseline-report", required=True)
    parser.add_argument("--candidate-output", required=True)
    parser.add_argument("--candidate-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--new-websites", required=True)
    args = parser.parse_args()

    baseline = summarize(Path(args.baseline_output), Path(args.baseline_report))
    candidate = summarize(Path(args.candidate_output), Path(args.candidate_report))

    base_websites = baseline.pop("websites")
    candidate_websites = candidate.pop("websites")
    new_orgs = sorted(set(candidate_websites) - set(base_websites))
    lost_orgs = sorted(set(base_websites) - set(candidate_websites))
    changed_orgs = sorted(
        org for org in set(base_websites) & set(candidate_websites)
        if base_websites[org].get("url") != candidate_websites[org].get("url")
    )

    metric_names = [
        *FIELD_FAMILIES.keys(),
        "total_claims",
        "evidence_count",
        "observed_logical_requests",
        "observed_conservative_requests",
        "runtime_seconds",
    ]
    delta = {
        name: round(float(candidate.get(name) or 0) - float(baseline.get(name) or 0), 3)
        for name in metric_names
    }

    comparison = {
        "baseline": baseline,
        "candidate": candidate,
        "delta": delta,
        "website_transfer": {
            "new_count": len(new_orgs),
            "lost_count": len(lost_orgs),
            "changed_count": len(changed_orgs),
            "new_organisation_numbers": new_orgs,
            "lost_organisation_numbers": lost_orgs,
            "changed_organisation_numbers": changed_orgs,
        },
    }
    Path(args.output).write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with Path(args.new_websites).open("w", encoding="utf-8") as handle:
        for org in new_orgs:
            handle.write(json.dumps(candidate_websites[org], ensure_ascii=False, separators=(",", ":")) + "\n")

    print(json.dumps(comparison, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
