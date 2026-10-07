#!/usr/bin/env python3
"""Fail-closed machine pre-screen for M10 consumed transfer.

Manual identity and semantic review is an explicit separate gate. A green machine
report is never, by itself, a PROMOTE decision.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FAMILIES = (
    "verified_website", "social", "external_contact", "careers_surface",
    "company_authored_hiring_intent", "specific_active_job",
    "dated_first_party_activity",
)


def decide(*, cohort: dict[str, Any], baseline: dict[str, Any],
           challenger: dict[str, Any], family: dict[str, Any],
           publication: dict[str, Any], count: int) -> dict[str, Any]:
    errors: list[str] = []

    def require(ok: bool, key: str) -> None:
        if not ok:
            errors.append(key)

    require(cohort.get("fresh_companies_used") == 0, "no_fresh_companies")
    require(cohort.get("gate_a_companies") == 20, "gate_a_size")
    require(cohort.get("gate_b_companies") == 100, "gate_b_size")
    require(bool(cohort.get("required_canaries")), "canaries_defined")
    require(set(cohort.get("required_canaries") or []).issubset(set(cohort.get("gate_a_canaries") or [])),
            "all_canaries_in_gate_a")
    require(set(cohort.get("required_canaries") or []).issubset(set(cohort.get("gate_b_canaries") or [])),
            "all_canaries_in_gate_b")
    require(family.get("same_company_set") is True and family.get("companies") == count,
            "identical_consumed_cohort")
    for label, report in (("baseline", baseline), ("challenger", challenger)):
        require(report.get("passed") is True, f"{label}_passed")
        require((report.get("source_policy") or {}).get("search_api_requests", 0) in (0, None),
                f"{label}_no_search")
        require(float((report.get("source_policy") or {}).get("third_party_cost_usd") or 0) == 0.0,
                f"{label}_zero_cost")
        require(int((report.get("runtime") or {}).get("wall_runtime_seconds") or 0) <= 2700,
                f"{label}_within_45m")
    bp = baseline.get("request_budget") or {}
    cp = challenger.get("request_budget") or {}
    b_observed = int(bp.get("observed_conservative_challenge_request_charge") or 0)
    c_observed = int(cp.get("observed_conservative_challenge_request_charge") or 0)
    b_theorem = int(bp.get("theoretical_challenge_request_charge_ceiling") or 0)
    c_theorem = int(cp.get("theoretical_challenge_request_charge_ceiling") or 0)
    require(0 < c_theorem <= b_theorem <= 2000, "theorem_under_2000")
    require(0 < c_observed <= b_observed <= 2000, "budget_neutral_observed")
    require(publication.get("all_new_publication_evidence_complete") is True,
            "new_publications_have_reopenable_evidence")
    require(publication.get("evidence_defects") == 0, "no_evidence_defects")
    require(publication.get("lost_publications") == 0, "no_lost_external_publications")
    require(publication.get("manual_review_rows") == publication.get("new_publications"),
            "all_new_publications_require_manual_review")

    entries = family.get("families") or {}
    require(set(FAMILIES) == set(entries), "all_families_reported")
    gained = lost = 0
    for name in FAMILIES:
        data = entries.get(name) or {}
        g = int(data.get("net_new_companies") or 0)
        l = int(data.get("lost_companies") or 0)
        gained += g
        lost += l
        require(l == 0, f"no_family_loss:{name}")
    require(gained > 0, "material_net_new_company_family_coverage")

    summary = {
        "milestone": "M10", "gate": "A" if count == 20 else "B",
        "machine_decision": "BLOCKED" if errors else "MANUAL_AUDIT_REQUIRED",
        "manual_review_finalized": False,
        "wrong_company_publications": None,
        "fresh_qualification_authorized": False,
        "errors": errors,
        "companies": count,
        "new_external_publications": publication.get("new_publications"),
        "lost_external_publications": publication.get("lost_publications"),
        "manual_audit_rows": publication.get("manual_review_rows"),
        "new_family_company_edges": gained,
        "lost_family_company_edges": lost,
        "families": entries,
        "baseline_observed_request_charge": b_observed,
        "challenger_observed_request_charge": c_observed,
        "baseline_theoretical_request_ceiling": b_theorem,
        "challenger_theoretical_request_ceiling": c_theorem,
        "baseline_wall_runtime_seconds": (baseline.get("runtime") or {}).get("wall_runtime_seconds"),
        "challenger_wall_runtime_seconds": (challenger.get("runtime") or {}).get("wall_runtime_seconds"),
        "challenger_search_requests": (challenger.get("source_policy") or {}).get("search_api_requests"),
        "challenger_third_party_cost_usd": (challenger.get("source_policy") or {}).get("third_party_cost_usd"),
    }
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    for key in ("cohort", "baseline_report", "challenger_report", "family_report",
                "publication_report", "output"):
        p.add_argument("--" + key.replace("_", "-"), type=Path, required=True)
    p.add_argument("--count", type=int, choices=[20, 100], required=True)
    args = p.parse_args()
    def read(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))
    summary = decide(
        cohort=read(args.cohort), baseline=read(args.baseline_report),
        challenger=read(args.challenger_report), family=read(args.family_report),
        publication=read(args.publication_report), count=args.count
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if summary["machine_decision"] == "MANUAL_AUDIT_REQUIRED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
