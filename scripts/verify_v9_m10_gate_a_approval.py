#!/usr/bin/env python3
"""Fail-closed validation of an explicitly reviewed, exact-sha Gate A transfer result.

This verifier only unlocks a consumed Gate B *experiment*. It does not authorize
release, fresh qualification or automatic production promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON object expected")
    return value


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(f"M10 Gate B locked: {reason}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(org: str, field: str, value: object) -> tuple[str, str, str]:
    return org, field, json.dumps(value, ensure_ascii=False, sort_keys=True)


def verify(approval_file: Path, artifact: Path, frozen_consumed: Path) -> dict:
    a = read_json(approval_file)
    cohort = read_json(artifact / "cohort-report.json")
    family = read_json(artifact / "family-transfer.json")
    pub = read_json(artifact / "publication-audit.json")
    machine = read_json(artifact / "m10-gate-a-machine-result.json")
    manual = read_jsonl(artifact / "manual-audit-required.jsonl")
    ga = read_jsonl(artifact / "gate-a-consumed-20.jsonl")
    gb = read_jsonl(artifact / "gate-b-consumed-100.jsonl")
    source = read_jsonl(frozen_consumed)

    require(a.get("schema") == "v9_m10_gate_a_manual_review_v1", "wrong approval schema")
    require(a.get("reviewer") and a.get("human_signoff_claimed") is False, "reviewer must be explicitly identified without impersonation")
    require(a.get("manual_review_finalized") is True, "manual review not finalized")
    require(a.get("gate_b_consumed_eval_authorized") is True, "consumed Gate B not approved")
    require(a.get("gate_b_fresh_eval_authorized") is False, "fresh qualification may not be approved")
    require(a.get("gate_b_production_promotion_authorized") is False, "production must not be approved")
    require(a.get("gate_a_run_id") == 37565180008, "unapproved source run")
    require(a.get("gate_a_artifact_id") == 11458838045, "unapproved source artifact")
    require(a.get("gate_a_artifact_digest") == "sha256:928e9ff4f11eb2ad078b0455c66e574c6c6bb7ec6e2ef2a8ccce123a73808e9f", "artifact digest mismatch")
    require(a.get("gate_a_challenger_sha") == "2848ed505103b3cbb0a3bf8d6313ee1ba7a25ecf", "unexpected challenger")
    require(a.get("gate_a_baseline_sha") == "72f1bf2892ec1c1e35674aa383433c9a37afdaca", "unexpected V8 baseline")
    require((artifact / "challenger-sha.txt").read_text().strip() == a["gate_a_challenger_sha"], "challenger SHA not from approved Gate A")
    require((artifact / "baseline-sha.txt").read_text().strip() == a["gate_a_baseline_sha"], "baseline SHA not frozen V8")
    require(machine.get("machine_decision") == "MANUAL_AUDIT_REQUIRED" and machine.get("errors") == [], "Gate A machine gate is not green")
    require(machine.get("manual_review_finalized") is False, "machine cannot self-approve")
    require(machine.get("fresh_qualification_authorized") is False, "fresh qualification was not locked")
    require(machine.get("companies") == 20, "Gate A cohort size")
    require(machine.get("new_family_company_edges") == 7 and machine.get("lost_family_company_edges") == 0, "Gate A family delta regression")
    require(machine.get("new_external_publications") == 11 and machine.get("lost_external_publications") == 0, "Gate A publication delta regression")
    require(machine.get("challenger_third_party_cost_usd") == 0.0 and machine.get("challenger_search_requests") == 0, "Gate A zero-cost constraint")
    require(int(machine.get("challenger_theoretical_request_ceiling") or 2001) <= 2000, "Gate A request theorem")
    require(pub.get("evidence_defects") == 0 and pub.get("all_new_publication_evidence_complete") is True, "Gate A evidence defects")
    require(pub.get("manual_review_rows") == 11 and pub.get("new_publications") == 11, "Gate A manual row count")
    require(a.get("wrong_company_publications") == 0 and a.get("semantic_overclaims") == 0, "manual precision did not clear")
    require(a.get("all_publications_claim_scoped") is True, "claim scope not approved")
    require(len(manual) == 11, "manual evidence rows absent")

    approved = a.get("approved_publications") or []
    require(len(approved) == 11, "approval must enumerate exactly 11 publications")
    actual_set = {
        signature(row["organisation_number"], row["field"], row["value"])
        for row in manual
    }
    approved_set = {
        signature(row["organisation_number"], row["field"], row["value"])
        for row in approved
    }
    require(len(actual_set) == len(approved_set) == 11 and actual_set == approved_set, "approval does not match exact publication values")
    require(all(row.get("verdict") == "APPROVED_AS_SCOPED" and row.get("rationale") for row in approved), "individual approval missing")
    require(all(all(row.get("checks", {}).values()) for row in manual), "unresolved evidence check")
    require(all(row.get("manual_exact_entity_review_required") is True and row.get("manual_semantic_scope_review_required") is True for row in manual), "manual review marking missing")
    require(cohort.get("fresh_companies_used") == 0 and cohort.get("source_manifest_companies") == 1000, "frozen source cohort invalid")
    require(cohort.get("gate_a_companies") == 20 and cohort.get("gate_b_companies") == 100, "frozen Gate A/B cohort sizes invalid")
    require(family.get("same_company_set") is True and family.get("companies") == 20, "Gate A baseline vs challenger cohort mismatch")
    require(sha256(artifact / "gate-a-consumed-20.jsonl") == cohort.get("gate_a_manifest_sha256") == a.get("gate_a_manifest_sha256"), "Gate A manifest digest")
    require(sha256(artifact / "gate-b-consumed-100.jsonl") == cohort.get("gate_b_manifest_sha256") == a.get("gate_b_manifest_sha256"), "Gate B manifest digest")
    require(sha256(frozen_consumed) == cohort.get("source_manifest_sha256") == a.get("consumed_source_sha256"), "frozen consumed source digest")
    a_org = [str(row.get("organisation_number") or "") for row in ga]
    b_org = [str(row.get("organisation_number") or "") for row in gb]
    source_org = [str(row.get("organisation_number") or "") for row in source]
    require(len(a_org) == len(set(a_org)) == 20, "Gate A duplicate company")
    require(len(b_org) == len(set(b_org)) == 100, "Gate B duplicate company")
    require(len(source_org) == len(set(source_org)) == 1000, "consumed source duplicate company")
    require(set(a_org).issubset(set(b_org)) and set(b_org).issubset(set(source_org)), "Gate B escaped frozen consumed source")
    require(set(cohort.get("required_canaries") or []).issubset(set(a_org)), "Gate A canaries absent")
    require(set(cohort.get("required_canaries") or []).issubset(set(b_org)), "Gate B canaries absent")
    return {
        "screen_type": "v9_m10_manual_review_gate_b_eligibility",
        "decision": "CONSUMED_GATE_B_AUTHORIZED_ONLY",
        "source_gate_a_run": a["gate_a_run_id"],
        "fixed_challenger_sha": a["gate_a_challenger_sha"],
        "fixed_baseline_sha": a["gate_a_baseline_sha"],
        "manual_publications_approved_as_scoped": 11,
        "wrong_company_publications": 0,
        "semantic_overclaims": 0,
        "gate_b_companies": 100,
        "gate_b_manifest_sha256": a["gate_b_manifest_sha256"],
        "fresh_companies_used": 0,
        "fresh_qualification_authorized": False,
        "production_promotion_authorized": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--approval", required=True, type=Path)
    p.add_argument("--artifact", required=True, type=Path)
    p.add_argument("--frozen-consumed", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    args = p.parse_args()
    result = verify(args.approval, args.artifact, args.frozen_consumed)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
