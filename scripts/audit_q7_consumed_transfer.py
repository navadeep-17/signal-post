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

from norway_company_agent.evidence_visibility import audit_contract_rows  # noqa: E402

COVERAGE_FIELDS = (
    "official_website",
    "external.profile_handle",
    "social_links",
    "external.contact_email",
    "external.careers_page",
    "external.job_posting",
    "external.company_update",
    "external.workforce_snapshot",
    "official.support_award",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            rows.append(value)
    return rows


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _row_index(rows: list[dict[str, Any]], *, label: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        org = str(row.get("organisation_number") or "").strip()
        if not org:
            raise ValueError(f"{label}: row missing organisation_number")
        if org in index:
            raise ValueError(f"{label}: duplicate organisation_number {org}")
        index[org] = row
    return index


def _available_claims(row: dict[str, Any], field: str | None = None) -> list[dict[str, Any]]:
    result = []
    for claim in row.get("claims") or []:
        if not isinstance(claim, dict) or claim.get("availability") != "available":
            continue
        if field is not None and claim.get("field") != field:
            continue
        result.append(claim)
    return result


def coverage(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        field: sum(bool(_available_claims(row, field)) for row in rows)
        for field in COVERAGE_FIELDS
    }


def _claim_key(org: str, claim: dict[str, Any]) -> str:
    value = json.dumps(claim.get("value"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{org}|{claim.get('field')}|{value}"


def claim_inventory(rows: list[dict[str, Any]]) -> Counter[str]:
    inventory: Counter[str] = Counter()
    for row in rows:
        org = str(row.get("organisation_number") or "")
        for claim in _available_claims(row):
            inventory[_claim_key(org, claim)] += 1
    return inventory


def _field_from_claim_key(key: str) -> str:
    parts = key.split("|", 2)
    return parts[1] if len(parts) > 1 else "unknown"


def _inventory_delta(before: Counter[str], after: Counter[str]) -> dict[str, Any]:
    added = after - before
    removed = before - after
    added_by_field = Counter()
    removed_by_field = Counter()
    for key, count in added.items():
        added_by_field[_field_from_claim_key(key)] += count
    for key, count in removed.items():
        removed_by_field[_field_from_claim_key(key)] += count
    return {
        "added_claims": sum(added.values()),
        "removed_claims": sum(removed.values()),
        "added_by_field": dict(sorted(added_by_field.items())),
        "removed_by_field": dict(sorted(removed_by_field.items())),
    }


def _run_metrics(report: dict[str, Any]) -> dict[str, Any]:
    request_budget = report.get("request_budget") or {}
    runtime = report.get("runtime") or {}
    source_policy = report.get("source_policy") or {}
    return {
        "passed": bool(report.get("passed")),
        "observed_conservative_requests": request_budget.get("observed_conservative_challenge_request_charge"),
        "theoretical_conservative_ceiling": request_budget.get("theoretical_challenge_request_charge_ceiling"),
        "wall_runtime_seconds": runtime.get("wall_runtime_seconds"),
        "third_party_cost_usd": source_policy.get("third_party_cost_usd"),
    }


def _forbidden_publications(
    rows: list[dict[str, Any]],
    forbidden_map: dict[str, list[str]],
) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for row in rows:
        org = str(row.get("organisation_number") or "")
        forbidden = [str(value).casefold() for value in forbidden_map.get(org, []) if value]
        if not forbidden:
            continue
        for claim in _available_claims(row):
            rendered = json.dumps(claim.get("value"), ensure_ascii=False, sort_keys=True).casefold()
            for needle in forbidden:
                if needle in rendered:
                    violations.append(
                        {
                            "organisation_number": org,
                            "field": str(claim.get("field") or "unknown"),
                            "forbidden_text": needle,
                        }
                    )
    return violations


def build_transfer_report(
    baseline_rows: list[dict[str, Any]],
    baseline_report: dict[str, Any],
    candidate_rows: list[dict[str, Any]],
    candidate_report: dict[str, Any],
    *,
    forbidden_map: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    before_index = _row_index(baseline_rows, label="baseline")
    after_index = _row_index(candidate_rows, label="candidate")
    if set(before_index) != set(after_index):
        missing = sorted(set(before_index) - set(after_index))
        added = sorted(set(after_index) - set(before_index))
        raise ValueError(
            "baseline/candidate organisation sets differ: "
            f"missing_from_candidate={missing[:10]} added_in_candidate={added[:10]}"
        )

    baseline_coverage = coverage(baseline_rows)
    candidate_coverage = coverage(candidate_rows)
    evidence_before = audit_contract_rows(baseline_rows)
    evidence_after = audit_contract_rows(candidate_rows)
    claim_delta = _inventory_delta(claim_inventory(baseline_rows), claim_inventory(candidate_rows))
    forbidden = _forbidden_publications(candidate_rows, forbidden_map or {})

    return {
        "status": "MEASURED_CONSUMED_ONLY",
        "fresh_qualification": False,
        "companies": len(candidate_rows),
        "same_company_set": True,
        "coverage": {
            "baseline": baseline_coverage,
            "candidate": candidate_coverage,
            "delta": {
                field: candidate_coverage[field] - baseline_coverage[field]
                for field in COVERAGE_FIELDS
            },
        },
        "claim_delta": claim_delta,
        "evidence_visibility": {
            "baseline": {
                key: evidence_before[key]
                for key in (
                    "available_claims",
                    "core_evidence_complete_claims",
                    "reopenable_source_claims",
                    "identity_sensitive_claims",
                    "identity_proof_visible",
                    "extraction_method_visible",
                )
            },
            "candidate": {
                key: evidence_after[key]
                for key in (
                    "available_claims",
                    "core_evidence_complete_claims",
                    "reopenable_source_claims",
                    "identity_sensitive_claims",
                    "identity_proof_visible",
                    "extraction_method_visible",
                )
            },
            "candidate_issue_count": len(evidence_after["issues"]),
        },
        "run_metrics": {
            "baseline": _run_metrics(baseline_report),
            "candidate": _run_metrics(candidate_report),
        },
        "known_wrong_company_publications": forbidden,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare a candidate Signalpost run with a consumed baseline without network access."
    )
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--baseline-report", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--candidate-report", required=True)
    parser.add_argument("--forbidden-map", help="Optional JSON map of organisation number -> forbidden text/domain list")
    parser.add_argument("--output", required=True)
    parser.add_argument("--require-candidate-core-evidence", action="store_true")
    parser.add_argument("--require-no-forbidden", action="store_true")
    args = parser.parse_args(argv)

    try:
        baseline_rows = read_jsonl(Path(args.baseline))
        candidate_rows = read_jsonl(Path(args.candidate))
        baseline_report = read_json(Path(args.baseline_report))
        candidate_report = read_json(Path(args.candidate_report))
        forbidden_map: dict[str, list[str]] = {}
        if args.forbidden_map:
            raw_map = read_json(Path(args.forbidden_map))
            forbidden_map = {
                str(key): [str(item) for item in value]
                for key, value in raw_map.items()
                if isinstance(value, list)
            }
        report = build_transfer_report(
            baseline_rows,
            baseline_report,
            candidate_rows,
            candidate_report,
            forbidden_map=forbidden_map,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))

    candidate_evidence = report["evidence_visibility"]["candidate"]
    if args.require_candidate_core_evidence and (
        candidate_evidence["core_evidence_complete_claims"] != candidate_evidence["available_claims"]
        or candidate_evidence["reopenable_source_claims"] != candidate_evidence["available_claims"]
    ):
        return 1
    if args.require_no_forbidden and report["known_wrong_company_publications"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
