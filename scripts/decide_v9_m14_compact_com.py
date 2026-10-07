#!/usr/bin/env python3
"""M14 consumed single-token compact-.com decision gate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_measurement import FAMILY_FIELDS  # noqa: E402

MIN_TREATED_VERIFIED_WEBSITE_GAINS = 2


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON object expected")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{path}: JSON objects expected")
    return rows


def _index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        org = str(row.get("organisation_number") or "")
        if len(org) != 9 or not org.isdigit() or org in out:
            raise ValueError(f"invalid/duplicate organisation number {org!r}")
        out[org] = row
    return out


def _available_fields(row: dict[str, Any]) -> set[str]:
    return {
        str(claim.get("field") or "")
        for claim in (row.get("claims") or [])
        if isinstance(claim, dict)
        and claim.get("availability") == "available"
        and claim.get("value") not in (None, "")
    }


def _family_presence(row: dict[str, Any]) -> dict[str, bool]:
    fields = _available_fields(row)
    return {
        family: bool(fields.intersection(family_fields))
        for family, family_fields in FAMILY_FIELDS.items()
    }


def decide(
    *,
    cohort_report: dict[str, Any],
    cohort_audit: list[dict[str, Any]],
    baseline_report: dict[str, Any],
    challenger_report: dict[str, Any],
    baseline_rows: list[dict[str, Any]],
    challenger_rows: list[dict[str, Any]],
    family_report: dict[str, Any],
    publication_report: dict[str, Any],
    manual_publications: list[dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []

    def require(ok: bool, reason: str) -> None:
        if not ok:
            errors.append(reason)

    baseline = _index(baseline_rows)
    challenger = _index(challenger_rows)
    cohort = {
        str(row.get("organisation_number") or ""): str(row.get("bucket") or "")
        for row in cohort_audit
    }

    require(len(cohort) == len(cohort_audit), "cohort_audit_unique")
    require(set(baseline) == set(challenger) == set(cohort), "identical_selected_cohort")
    require(len(baseline) == 100, "exact_100_company_cohort")
    require(cohort_report.get("selected_companies") == 100, "cohort_report_100")
    require(cohort_report.get("treated_companies") == 20, "exact_20_treated")
    require(cohort_report.get("control_companies") == 80, "exact_80_controls")
    require(cohort_report.get("fresh_companies_used") == 0, "no_fresh_companies")
    require(not any(
        bool(row.get("previous_search_development"))
        or bool(row.get("m10_positive_canary"))
        or bool(row.get("m12_researched"))
        or bool(row.get("builderr_public_practice"))
        for row in cohort_audit
    ), "all_researched_and_practice_sets_excluded")

    for label, report in (("baseline", baseline_report), ("challenger", challenger_report)):
        require(report.get("passed") is True, f"{label}_passed")
        require(
            float((report.get("runtime") or {}).get("wall_runtime_seconds") or 999999) <= 2700,
            f"{label}_within_45m",
        )
        budget = report.get("request_budget") or {}
        require(
            int(budget.get("theoretical_challenge_request_charge_ceiling") or 999999) <= 2000,
            f"{label}_theorem_under_2000",
        )
        require(
            int(budget.get("observed_conservative_challenge_request_charge") or 999999) <= 2000,
            f"{label}_observed_under_2000",
        )
        policy = report.get("source_policy") or {}
        require(float(policy.get("third_party_cost_usd") or 0.0) == 0.0, f"{label}_zero_external_api_cost")

    b_budget = baseline_report.get("request_budget") or {}
    c_budget = challenger_report.get("request_budget") or {}
    require(
        int(c_budget.get("theoretical_challenge_request_charge_ceiling") or 999999)
        <= int(b_budget.get("theoretical_challenge_request_charge_ceiling") or -1),
        "request_theorem_not_increased",
    )

    require(family_report.get("same_company_set") is True, "same_company_set")
    require(family_report.get("companies") == 100, "family_report_100")
    families = family_report.get("families") or {}
    require(set(families) == set(FAMILY_FIELDS), "all_seven_families_reported")

    total_gains = 0
    total_losses = 0
    for family in FAMILY_FIELDS:
        item = families.get(family) or {}
        total_gains += int(item.get("net_new_companies") or 0)
        losses = int(item.get("lost_companies") or 0)
        total_losses += losses
        require(losses == 0, f"no_family_loss:{family}")

    require(publication_report.get("evidence_defects") == 0, "zero_evidence_defects")
    require(
        publication_report.get("all_new_publication_evidence_complete") is True,
        "all_new_publications_have_reopenable_evidence",
    )
    require(publication_report.get("lost_publications") == 0, "zero_lost_publications")
    require(
        publication_report.get("manual_review_rows") == publication_report.get("new_publications"),
        "every_new_publication_has_manual_row",
    )
    require(
        len(manual_publications) == int(publication_report.get("manual_review_rows") or 0),
        "manual_queue_count_matches",
    )
    require(
        all(
            bool(row.get("checks"))
            and all((row.get("checks") or {}).values())
            for row in manual_publications
        ),
        "every_manual_row_machine_check_green",
    )

    treated = {org for org, bucket in cohort.items() if bucket == "m14_single_token_compact_com"}
    controls = {org for org, bucket in cohort.items() if bucket == "m14_multi_token_control"}
    require(len(treated) == 20, "audit_exact_20_treated")
    require(len(controls) == 80, "audit_exact_80_controls")

    treated_edges: list[dict[str, str]] = []
    control_edges: list[dict[str, str]] = []
    treated_website_gains: set[str] = set()

    for org in sorted(baseline):
        before = _family_presence(baseline[org])
        after = _family_presence(challenger[org])
        for family in FAMILY_FIELDS:
            if not before[family] and after[family]:
                item = {"organisation_number": org, "family": family}
                if org in treated:
                    treated_edges.append(item)
                    if family == "verified_website":
                        treated_website_gains.add(org)
                elif org in controls:
                    control_edges.append(item)

    publication_orgs = [str(row.get("organisation_number") or "") for row in manual_publications]
    treated_publications = sum(org in treated for org in publication_orgs)
    control_publications = sum(org in controls for org in publication_orgs)

    require(not control_edges, "zero_control_family_gains")
    require(control_publications == 0, "zero_control_publications")
    require(total_losses == 0, "zero_total_family_losses")
    require(treated_publications == len(manual_publications), "all_new_publications_on_treated_holdout")

    website_gain_count = len(treated_website_gains)
    if errors:
        machine_decision = "BLOCKED"
    elif website_gain_count < MIN_TREATED_VERIFIED_WEBSITE_GAINS:
        machine_decision = "HOLD_COMPACT_COM_YIELD_BELOW_BAR"
    elif treated_publications == 0 or not treated_edges:
        machine_decision = "HOLD_NO_MATERIAL_TRANSFER"
    else:
        machine_decision = "MANUAL_AUDIT_REQUIRED"

    return {
        "milestone": "M14",
        "screen": "consumed_single_token_compact_com",
        "machine_decision": machine_decision,
        "errors": errors,
        "companies": len(baseline),
        "treated_companies": len(treated),
        "control_companies": len(controls),
        "total_new_family_company_edges": total_gains,
        "total_lost_family_company_edges": total_losses,
        "treated_new_family_company_edges": len(treated_edges),
        "control_new_family_company_edges": len(control_edges),
        "treated_verified_website_gains": website_gain_count,
        "treated_verified_website_organisation_numbers": sorted(treated_website_gains),
        "new_external_publications": int(publication_report.get("new_publications") or 0),
        "lost_external_publications": int(publication_report.get("lost_publications") or 0),
        "treated_new_publications": treated_publications,
        "control_new_publications": control_publications,
        "minimum_treated_verified_website_gains": MIN_TREATED_VERIFIED_WEBSITE_GAINS,
        "manual_review_finalized": False,
        "wrong_company_publications": None,
        "fresh_qualification_authorized": False,
        "production_promotion_authorized": False,
        "builderr_official_score_proven": False,
        "baseline_observed_request_charge": int(
            b_budget.get("observed_conservative_challenge_request_charge") or 0
        ),
        "challenger_observed_request_charge": int(
            c_budget.get("observed_conservative_challenge_request_charge") or 0
        ),
        "baseline_theoretical_request_ceiling": int(
            b_budget.get("theoretical_challenge_request_charge_ceiling") or 0
        ),
        "challenger_theoretical_request_ceiling": int(
            c_budget.get("theoretical_challenge_request_charge_ceiling") or 0
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    for name in (
        "cohort_report", "cohort_audit", "baseline_report", "challenger_report",
        "baseline_output", "challenger_output", "family_report",
        "publication_report", "manual_publications", "output",
    ):
        p.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    args = p.parse_args()
    result = decide(
        cohort_report=read_json(args.cohort_report),
        cohort_audit=read_jsonl(args.cohort_audit),
        baseline_report=read_json(args.baseline_report),
        challenger_report=read_json(args.challenger_report),
        baseline_rows=read_jsonl(args.baseline_output),
        challenger_rows=read_jsonl(args.challenger_output),
        family_report=read_json(args.family_report),
        publication_report=read_json(args.publication_report),
        manual_publications=read_jsonl(args.manual_publications),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if result["machine_decision"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
