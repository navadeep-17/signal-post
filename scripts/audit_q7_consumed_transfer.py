#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.evidence_visibility import audit_contract_rows  # noqa: E402
from norway_company_agent.support_contract import (  # noqa: E402
    SUPPORT_AWARD_EXTRACTION_METHOD,
    project_support_award_evidence_provenance,
)

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
MAX_CLAIM_DELTA_DETAILS = 50


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


def _covered_organisations(rows: list[dict[str, Any]], field: str) -> set[str]:
    return {
        str(row.get("organisation_number") or "")
        for row in rows
        if _available_claims(row, field)
    }


def _company_coverage_delta(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> dict[str, dict[str, list[str]]]:
    result: dict[str, dict[str, list[str]]] = {}
    for field in COVERAGE_FIELDS:
        before = _covered_organisations(baseline_rows, field)
        after = _covered_organisations(candidate_rows, field)
        gained = sorted(after - before)
        lost = sorted(before - after)
        if gained or lost:
            result[field] = {
                "gained_organisations": gained,
                "lost_organisations": lost,
            }
    return result


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


def _claim_detail(key: str, count: int) -> dict[str, Any]:
    org, field, value_json = key.split("|", 2)
    try:
        value: Any = json.loads(value_json)
    except json.JSONDecodeError:
        value = value_json
    return {
        "organisation_number": org,
        "field": field,
        "value": value,
        "count": count,
    }


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
        "added_claim_details": [
            _claim_detail(key, count)
            for key, count in sorted(added.items())[:MAX_CLAIM_DELTA_DETAILS]
        ],
        "removed_claim_details": [
            _claim_detail(key, count)
            for key, count in sorted(removed.items())[:MAX_CLAIM_DELTA_DETAILS]
        ],
        "details_truncated": (
            len(added) > MAX_CLAIM_DELTA_DETAILS or len(removed) > MAX_CLAIM_DELTA_DETAILS
        ),
    }


def apply_current_zero_network_provenance(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply only current deterministic provenance backfills that require no source fetch.

    The frozen Q4 candidate predates the support-evidence provenance repair merged in PR #110.
    Q7 should judge the current main bundle, so this normalizes that frozen artifact through
    the merged final-contract backfill without changing claims, source evidence, or requests.
    """

    normalized: list[dict[str, Any]] = []
    support_method_rows_added = 0
    changed_organisations: set[str] = set()

    for original in rows:
        row = deepcopy(original)
        org = str(row.get("organisation_number") or "")
        before = {
            str(item.get("id")): str(item.get("extraction_method") or "")
            for item in row.get("evidence") or []
            if isinstance(item, dict) and item.get("id")
        }
        projected = project_support_award_evidence_provenance(row)
        after = {
            str(item.get("id")): str(item.get("extraction_method") or "")
            for item in projected.get("evidence") or []
            if isinstance(item, dict) and item.get("id")
        }
        for evidence_id, method in after.items():
            if before.get(evidence_id, "") == "" and method == SUPPORT_AWARD_EXTRACTION_METHOD:
                support_method_rows_added += 1
                changed_organisations.add(org)
        normalized.append(projected)

    return normalized, {
        "applied": True,
        "network_requests_added": 0,
        "claim_semantics_changed": False,
        "support_extraction_method": SUPPORT_AWARD_EXTRACTION_METHOD,
        "support_evidence_rows_with_method_added": support_method_rows_added,
        "organisations_changed": sorted(changed_organisations),
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
    apply_current_provenance: bool = False,
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

    normalization = {
        "applied": False,
        "network_requests_added": 0,
        "claim_semantics_changed": False,
        "support_evidence_rows_with_method_added": 0,
        "organisations_changed": [],
    }
    measured_candidate_rows = candidate_rows
    if apply_current_provenance:
        measured_candidate_rows, normalization = apply_current_zero_network_provenance(candidate_rows)

    baseline_coverage = coverage(baseline_rows)
    candidate_coverage = coverage(measured_candidate_rows)
    evidence_before = audit_contract_rows(baseline_rows)
    evidence_after = audit_contract_rows(measured_candidate_rows)
    claim_delta = _inventory_delta(
        claim_inventory(baseline_rows),
        claim_inventory(measured_candidate_rows),
    )
    forbidden = _forbidden_publications(measured_candidate_rows, forbidden_map or {})

    return {
        "status": "MEASURED_CONSUMED_ONLY",
        "fresh_qualification": False,
        "companies": len(measured_candidate_rows),
        "same_company_set": True,
        "candidate_zero_network_normalization": normalization,
        "coverage": {
            "baseline": baseline_coverage,
            "candidate": candidate_coverage,
            "delta": {
                field: candidate_coverage[field] - baseline_coverage[field]
                for field in COVERAGE_FIELDS
            },
            "company_level_changes": _company_coverage_delta(
                baseline_rows,
                measured_candidate_rows,
            ),
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
    parser.add_argument("--apply-current-zero-network-provenance", action="store_true")
    parser.add_argument("--require-candidate-core-evidence", action="store_true")
    parser.add_argument("--require-candidate-provenance-complete", action="store_true")
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
            apply_current_provenance=args.apply_current_zero_network_provenance,
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
    if args.require_candidate_provenance_complete and (
        candidate_evidence["identity_proof_visible"] != candidate_evidence["identity_sensitive_claims"]
        or candidate_evidence["extraction_method_visible"] != candidate_evidence["identity_sensitive_claims"]
        or report["evidence_visibility"]["candidate_issue_count"] != 0
    ):
        return 1
    if args.require_no_forbidden and report["known_wrong_company_publications"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
