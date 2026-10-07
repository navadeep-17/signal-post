#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from build_v2_product import read_jsonl  # noqa: E402
from norway_company_agent.canonical_projection import (  # noqa: E402
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.careers_contract import project_careers_page_claims  # noqa: E402
from norway_company_agent.external_precision_guard import project_external_precision_guard  # noqa: E402
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.synthesis import build_company_synthesis, validate_company_synthesis  # noqa: E402

MIN_NEW_CAREERS_COMPANIES = 1


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _claim_key(claim: dict[str, Any]) -> str:
    return json.dumps(claim, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _claims_by_key(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _claim_key(claim): claim
        for claim in (row.get("claims") or [])
        if isinstance(claim, dict)
    }


def _profile_index(path: Path) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(path)
    index = {
        str(row.get("organisation_number") or ""): row
        for row in rows
        if row.get("organisation_number")
    }
    if len(index) != len(rows):
        raise ValueError("profiles contain missing or duplicate organisation numbers")
    return index


def _evidence_index(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in (row.get("evidence") or [])
        if isinstance(item, dict) and item.get("id")
    }


def _careers_evidence_defects(row: dict[str, Any], claim: dict[str, Any]) -> list[str]:
    defects: list[str] = []
    evidence = _evidence_index(row)
    refs = [str(value) for value in (claim.get("evidence_ids") or []) if str(value)]
    if not refs:
        return ["missing_evidence_ids"]
    for ref in refs:
        item = evidence.get(ref)
        if item is None:
            defects.append(f"missing_evidence:{ref}")
            continue
        for field in ("source_url", "retrieved_at", "claim_span", "extraction_method"):
            if not str(item.get(field) or "").strip():
                defects.append(f"{ref}:missing_{field}")
        digest = str(item.get("content_sha256") or "")
        if len(digest) != 64:
            defects.append(f"{ref}:invalid_content_sha256")
        proof = item.get("identity_proof")
        if not isinstance(proof, dict):
            defects.append(f"{ref}:missing_identity_proof")
        else:
            if proof.get("publishable") is not True:
                defects.append(f"{ref}:identity_not_publishable")
            if not str(proof.get("homepage_url") or "").startswith(("http://", "https://")):
                defects.append(f"{ref}:identity_homepage_url_missing")
            if str(proof.get("homepage_content_sha256") or "") != digest:
                defects.append(f"{ref}:identity_hash_mismatch")
            if proof.get("same_snapshot_homepage_declaration") is not True:
                defects.append(f"{ref}:same_snapshot_guard_missing")
    return defects


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline-output", type=Path, required=True)
    p.add_argument("--profiles", type=Path, required=True)
    p.add_argument("--challenger-output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--manual-audit", type=Path, required=True)
    args = p.parse_args()

    baseline = read_jsonl(args.baseline_output)
    profiles = _profile_index(args.profiles)
    if len(baseline) != 100:
        raise ValueError(f"expected 100 baseline companies, got {len(baseline)}")
    baseline_orgs = [str(row.get("organisation_number") or "") for row in baseline]
    if len(set(baseline_orgs)) != 100 or set(baseline_orgs) != set(profiles):
        raise ValueError("baseline/profile company sets differ")

    challenger: list[dict[str, Any]] = []
    manual: list[dict[str, Any]] = []
    errors: list[str] = []
    total_added = 0
    total_lost = 0
    careers_added = 0
    careers_companies: set[str] = set()
    job_before = 0
    job_after = 0
    evidence_defects: list[dict[str, Any]] = []

    for row in baseline:
        org = str(row.get("organisation_number") or "")
        profile = profiles[org]
        before = _claims_by_key(row)
        job_before += sum(
            1 for claim in before.values()
            if claim.get("field") == "external.job_posting"
        )

        projected = project_careers_page_claims(row, profile)
        guarded = project_external_precision_guard(projected)
        item = project_canonical_profile(guarded)
        item["synthesis"] = build_company_synthesis(item)

        for error in validate_contract_object(item):
            errors.append(f"{org}:contract:{error}")
        for error in validate_canonical_projection(item):
            errors.append(f"{org}:canonical:{error}")
        for error in validate_company_synthesis(item):
            errors.append(f"{org}:synthesis:{error}")

        after = _claims_by_key(item)
        job_after += sum(
            1 for claim in after.values()
            if claim.get("field") == "external.job_posting"
        )

        added_keys = set(after) - set(before)
        lost_keys = set(before) - set(after)
        total_added += len(added_keys)
        total_lost += len(lost_keys)

        if lost_keys:
            errors.append(f"{org}:lost_existing_claims:{len(lost_keys)}")

        for key in sorted(added_keys):
            claim = after[key]
            field = str(claim.get("field") or "")
            if field != "external.careers_page":
                errors.append(f"{org}:unexpected_new_claim_field:{field}")
                continue
            careers_added += 1
            careers_companies.add(org)
            defects = _careers_evidence_defects(item, claim)
            if defects:
                evidence_defects.append({
                    "organisation_number": org,
                    "value": claim.get("value"),
                    "defects": defects,
                })
            traces = [
                _evidence_index(item).get(str(ref))
                for ref in (claim.get("evidence_ids") or [])
                if _evidence_index(item).get(str(ref))
            ]
            manual.append({
                "organisation_number": org,
                "field": field,
                "value": claim.get("value"),
                "signal_type": claim.get("signal_type"),
                "claim_scope": claim.get("claim_scope"),
                "evidence": traces,
                "manual_review_finalized": False,
            })

        challenger.append(item)

    if job_after != job_before:
        errors.append(f"job_posting_count_changed:{job_before}->{job_after}")
    if evidence_defects:
        errors.append(f"careers_evidence_defects:{len(evidence_defects)}")

    new_careers_companies = len(careers_companies)
    if errors:
        decision = "BLOCKED"
    elif new_careers_companies >= MIN_NEW_CAREERS_COMPANIES:
        decision = "MANUAL_AUDIT_REQUIRED"
    else:
        decision = "HOLD_NO_REAL_CAREERS_TRANSFER"

    report = {
        "milestone": "M18",
        "screen": "offline_replay_same_acquisition_careers_projection",
        "companies": 100,
        "machine_decision": decision,
        "minimum_new_careers_companies": MIN_NEW_CAREERS_COMPANIES,
        "new_careers_claims": careers_added,
        "new_careers_companies": new_careers_companies,
        "new_careers_organisation_numbers": sorted(careers_companies),
        "total_new_claims": total_added,
        "total_lost_claims": total_lost,
        "job_postings_before": job_before,
        "job_postings_after": job_after,
        "network_requests_added_by_replay": 0,
        "search_api_requests_added_by_replay": 0,
        "third_party_cost_usd_added_by_replay": 0.0,
        "evidence_defects": evidence_defects,
        "validation_errors": errors,
        "manual_review_rows": len(manual),
        "manual_review_finalized": False,
        "publication_semantics": (
            "external.careers_page / hiring.careers_page is careers/hiring presence only; "
            "no active vacancy or job posting is inferred."
        ),
        "production_promotion_authorized": False,
        "fresh_qualification_authorized": False,
        "builderr_score_claimed": False,
    }

    _write_jsonl(args.challenger_output, challenger)
    _write_jsonl(args.manual_audit, manual)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if decision == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
