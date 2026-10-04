from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from norway_company_agent.canonical_projection import validate_canonical_projection
from norway_company_agent.output_contract import validate_contract_object
from norway_company_agent.synthesis import validate_company_synthesis

TRACKED_CLAIMS = (
    "company_description",
    "registered_purpose",
    "registration_date",
    "registered_address",
    "registered_contact_email",
    "registered_phone",
    "registered_mobile",
    "external.contact_email",
    "official_website",
)
TRACKED_CANONICAL = (
    "website.description",
    "company.registered_purpose",
    "company.registration_date",
    "company.registered_address",
    "company.contact.email",
    "company.contact.phone",
    "company.contact.mobile",
    "website.contact_email",
    "website.official",
)
BASELINE_COMPANY_COVERAGE = {
    "company_description": 14,
    "registered_purpose": 0,
    "registration_date": 0,
    "registered_address": 0,
    "registered_contact_email": 0,
    "registered_phone": 0,
    "registered_mobile": 0,
    "external.contact_email": 4,
    "official_website": 8,
}


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _company_count(rows: list[dict[str, Any]], field: str) -> int:
    return sum(
        1
        for row in rows
        if any(
            claim.get("field") == field and claim.get("availability") == "available"
            for claim in row.get("claims") or []
        )
    )


def _canonical_company_count(rows: list[dict[str, Any]], field: str) -> int:
    return sum(
        1
        for row in rows
        if any(
            fact.get("canonical_field") == field and fact.get("availability") == "available"
            for fact in row.get("canonical_facts") or []
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--run-report", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    rows = _rows(args.input)
    report = json.loads(args.run_report.read_text(encoding="utf-8"))
    claim_coverage = {field: _company_count(rows, field) for field in TRACKED_CLAIMS}
    canonical_coverage = {field: _canonical_company_count(rows, field) for field in TRACKED_CANONICAL}
    net_gain = {
        field: claim_coverage[field] - BASELINE_COMPANY_COVERAGE[field]
        for field in BASELINE_COMPANY_COVERAGE
    }

    contract_errors = []
    canonical_errors = []
    synthesis_errors = []
    for row in rows:
        org = str(row.get("organisation_number") or "")
        contract_errors.extend(f"{org}: {error}" for error in validate_contract_object(row))
        canonical_errors.extend(f"{org}: {error}" for error in validate_canonical_projection(row))
        synthesis_errors.extend(f"{org}: {error}" for error in validate_company_synthesis(row))

    terminal_states: dict[str, int] = {}
    for row in rows:
        state = str((row.get("run") or {}).get("terminal_status") or "")
        terminal_states[state] = terminal_states.get(state, 0) + 1

    request_budget = report.get("request_budget") or {}
    runtime = report.get("runtime") or {}
    source_policy = report.get("source_policy") or {}
    operations = {
        "logical_requests": request_budget.get("observed_logical_requests"),
        "conservative_request_charge": request_budget.get("observed_conservative_challenge_request_charge"),
        "theoretical_conservative_request_ceiling": request_budget.get("theoretical_challenge_request_charge_ceiling"),
        "third_party_cost_usd": source_policy.get("third_party_cost_usd"),
        "runtime_seconds": runtime.get("wall_runtime_seconds"),
        "request_latency_p50_ms": (runtime.get("request_latency_ms") or {}).get("p50"),
        "request_latency_p95_ms": (runtime.get("request_latency_ms") or {}).get("p95"),
        "search_api_requests": source_policy.get("search_api_requests", 0),
    }
    summary = {
        "schema_version": "signalpost-phase1-e2e-summary-v1",
        "harness_revision": 2,
        "companies": len(rows),
        "unique_companies": len({str(row.get("organisation_number") or "") for row in rows}),
        "terminal_states": terminal_states,
        "claim_company_coverage": claim_coverage,
        "canonical_company_coverage": canonical_coverage,
        "baseline_company_coverage": BASELINE_COMPANY_COVERAGE,
        "net_company_gain": net_gain,
        "quality": {
            "contract_errors": contract_errors,
            "canonical_errors": canonical_errors,
            "synthesis_errors": synthesis_errors,
        },
        "operations": operations,
        "passed": (
            len(rows) == 100
            and terminal_states.get("completed") == 100
            and not contract_errors
            and not canonical_errors
            and not synthesis_errors
            and (operations.get("conservative_request_charge") or 0) <= 2000
            and (operations.get("theoretical_conservative_request_ceiling") or 0) <= 2000
            and float(operations.get("third_party_cost_usd") or 0.0) == 0.0
            and int(operations.get("search_api_requests") or 0) == 0
        ),
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["passed"]:
        raise SystemExit("Phase 1 end-to-end summary failed")


if __name__ == "__main__":
    main()
