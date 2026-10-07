#!/usr/bin/env python3
"""M10 Gate B: distinguish reused Gate A canary gains from genuinely new transfer.

Read only the immutable retained A/B audit artifacts. No live website fetch,
no evaluator rerun, no new cohort, and no auto-promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FAMILIES = (
    "verified_website", "social", "external_contact", "careers_surface",
    "company_authored_hiring_intent", "specific_active_job",
    "dated_first_party_activity",
)


def load_json(path: Path) -> dict[str, Any]:
    item = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(item, dict):
        raise ValueError(f"{path}: JSON object required")
    return item


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{path}: all rows must be objects")
    return rows


def signature(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("organisation_number") or ""),
        str(row.get("field") or ""),
        json.dumps(row.get("value"), ensure_ascii=False, sort_keys=True),
    )


def index_publications(rows: list[dict[str, Any]], allowed_orgs: set[str]) -> dict[tuple[str, str, str], dict[str, Any]]:
    index = {}
    for row in rows:
        key = signature(row)
        if key in index:
            raise ValueError(f"duplicate publication signature: {key}")
        if key[0] not in allowed_orgs:
            raise ValueError(f"publication outside selected cohort: {key}")
        if (
            row.get("manual_exact_entity_review_required") is not True
            or row.get("manual_semantic_scope_review_required") is not True
            or not row.get("checks")
            or not all(value is True for value in row["checks"].values())
        ):
            raise ValueError(f"publication has incomplete identity/evidence checks: {key}")
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"missing publication evidence: {key}")
        if any(
            not isinstance(item, dict)
            or not isinstance(item.get("source_url"), str)
            or not item["source_url"].startswith(("https://", "http://"))
            or len(str(item.get("content_sha256") or "")) != 64
            for item in evidence
        ):
            raise ValueError(f"invalid retained source/hash: {key}")
        index[key] = row
    return index


def evidence_identity(row: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    return sorted(
        (
            str(ev.get("source_url") or ""),
            str(ev.get("content_sha256") or ""),
            str(ev.get("claim_span") or ""),
            str(ev.get("extraction_method") or ""),
        )
        for ev in row["evidence"]
    )


def _orgs(rows: list[dict[str, Any]], count: int) -> set[str]:
    orgs = [str(row.get("organisation_number") or "") for row in rows]
    if len(orgs) != count or len(set(orgs)) != count or any(len(x) != 9 or not x.isdigit() for x in orgs):
        raise ValueError(f"invalid locked {count}-company manifest")
    return set(orgs)


def _gains(report: dict[str, Any]) -> dict[str, int]:
    families = report.get("families") or {}
    if set(families) != set(FAMILIES):
        raise ValueError("all seven company families must be reported")
    return {f: int(families[f].get("net_new_companies") or 0) for f in FAMILIES}


def evaluate(
    *,
    gate_a_manifest: list[dict[str, Any]],
    gate_b_manifest: list[dict[str, Any]],
    gate_a_manual: list[dict[str, Any]],
    gate_b_manual: list[dict[str, Any]],
    gate_a_family: dict[str, Any],
    gate_b_family: dict[str, Any],
    gate_b_machine: dict[str, Any],
    gate_a_approval: dict[str, Any],
) -> dict[str, Any]:
    a_orgs = _orgs(gate_a_manifest, 20)
    b_orgs = _orgs(gate_b_manifest, 100)
    if not a_orgs <= b_orgs or len(b_orgs - a_orgs) != 80:
        raise ValueError("Gate B must contain exact Gate A 20 plus 80 more consumed organisations")
    if (
        gate_b_machine.get("machine_decision") != "MANUAL_AUDIT_REQUIRED"
        or gate_b_machine.get("errors") != []
        or gate_b_machine.get("companies") != 100
        or gate_b_machine.get("lost_external_publications") != 0
        or gate_b_machine.get("lost_family_company_edges") != 0
    ):
        raise ValueError("Gate B machine gate did not pass fail-closed structural checks")
    if not gate_a_approval.get("manual_review_finalized") or gate_a_approval.get("human_signoff_claimed") is not False:
        raise ValueError("Gate A approval must be explicit and attributed accurately")
    if gate_a_approval.get("gate_b_consumed_eval_authorized") is not True:
        raise ValueError("Gate A did not authorize consumed Gate B")
    if gate_a_approval.get("gate_b_production_promotion_authorized") is not False:
        raise ValueError("no production authorization permitted")
    canaries = {"999096298", "979943377", "927097532"}
    if not canaries <= a_orgs:
        raise ValueError("required consumed positive canaries missing from Gate A")

    a = index_publications(gate_a_manual, a_orgs)
    b = index_publications(gate_b_manual, b_orgs)
    approved = {signature(row) for row in (gate_a_approval.get("approved_publications") or [])}
    if approved != set(a) or len(approved) != len(a):
        raise ValueError("Gate A manual queue does not match scoped, explicit approval")
    if any(row.get("verdict") != "APPROVED_AS_SCOPED" for row in gate_a_approval.get("approved_publications") or []):
        raise ValueError("Gate A scoped approval has an unresolved publication")

    if gate_b_machine.get("new_external_publications") != len(b) or gate_b_machine.get("manual_audit_rows") != len(b):
        raise ValueError("Gate B count disagrees with retained manual publication queue")
    if not set(a) <= set(b):
        raise ValueError("Previously reviewed Gate A publication disappeared in Gate B; require regression audit")
    if any(evidence_identity(b[k]) != evidence_identity(a[k]) for k in a):
        raise ValueError("Previously-reviewed publication source/hash/claim span changed in Gate B")

    gains_a = _gains(gate_a_family)
    gains_b = _gains(gate_b_family)
    a_edges = sum(gains_a.values())
    b_edges = sum(gains_b.values())
    if a_edges < 1 or b_edges < 1:
        raise ValueError("expected positive previously-consumed coverage gains")
    if b_edges < a_edges:
        raise ValueError("net company-family gains regressed relative to Gate A")

    new_keys = set(b) - set(a)
    non_a = b_orgs - a_orgs
    holdout_keys = {key for key in new_keys if key[0] in non_a}
    all_b_new_on_canaries = all(key[0] in canaries for key in b)
    gain_delta = {family: gains_b[family] - gains_a[family] for family in FAMILIES}
    no_breadth = not holdout_keys and not new_keys and not any(gain_delta.values()) and all_b_new_on_canaries
    return {
        "screen": "v9_m10_gate_b_incremental_breadth_audit",
        "decision": (
            "HOLD_BREADTH_CANARY_ONLY"
            if no_breadth else "REVIEW_B_ONLY_TRANSFER_AND_FAMILY_DELTAS"
        ),
        "gate_a_companies": len(a_orgs),
        "gate_b_companies": len(b_orgs),
        "additional_gate_b_companies": len(non_a),
        "gate_a_scoped_approved_publications": len(a),
        "gate_b_publications": len(b),
        "identical_retained_gate_a_publications_in_gate_b": len(a),
        "gate_b_only_new_publication_tuples": len(new_keys),
        "additional_80_new_publication_tuples": len(holdout_keys),
        "gate_b_publications_all_from_forced_canaries": all_b_new_on_canaries,
        "gate_a_new_family_company_edges": a_edges,
        "gate_b_new_family_company_edges": b_edges,
        "per_family_gain_delta_b_minus_a": gain_delta,
        "gate_b_publication_signatures_requiring_new_manual_approval": [
            {"organisation_number": k[0], "field": k[1], "canonical_json_value": k[2]}
            for k in sorted(new_keys)
        ],
        "gate_b_scoped_manual_review_completed_for_reused_publications": len(a) == len(b),
        "evidence_hash_and_claim_span_stable_for_reused_publications": True,
        "fresh_qualification_authorized": False,
        "production_promotion_authorized": False,
        "builderr_hidden_recall_proven": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    for name in (
        "gate_a_manifest", "gate_b_manifest", "gate_a_manual", "gate_b_manual",
        "gate_a_family", "gate_b_family", "gate_b_machine", "gate_a_approval",
        "output",
    ):
        p.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    args = p.parse_args()
    approval = load_json(args.gate_a_approval)
    for filename, expected_key in (
        (args.gate_a_manifest, "gate_a_manifest_sha256"),
        (args.gate_b_manifest, "gate_b_manifest_sha256"),
    ):
        expected = str(approval.get(expected_key) or "")
        observed = hashlib.sha256(filename.read_bytes()).hexdigest()
        if not expected or expected != observed:
            raise ValueError(f"retained cohort manifest SHA-256 mismatch: {filename}")
    result = evaluate(
        gate_a_manifest=load_jsonl(args.gate_a_manifest),
        gate_b_manifest=load_jsonl(args.gate_b_manifest),
        gate_a_manual=load_jsonl(args.gate_a_manual),
        gate_b_manual=load_jsonl(args.gate_b_manual),
        gate_a_family=load_json(args.gate_a_family),
        gate_b_family=load_json(args.gate_b_family),
        gate_b_machine=load_json(args.gate_b_machine),
        gate_a_approval=load_json(args.gate_a_approval),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
