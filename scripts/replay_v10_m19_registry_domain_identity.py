#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import (  # noqa: E402
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.registry_domain_identity_recovery import (  # noqa: E402
    METHOD,
    project_registry_domain_composite_website,
)
from norway_company_agent.synthesis import (  # noqa: E402
    build_company_synthesis,
    validate_company_synthesis,
)

MIN_DEVELOPMENT_RECOVERIES = 2
MIN_TRANSFER_RECOVERIES = 1


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{lineno}: expected object")
        rows.append(item)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def profile_index(path: Path) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(path)
    index = {
        str(row.get("organisation_number") or ""): row
        for row in rows
        if row.get("organisation_number")
    }
    if len(index) != len(rows):
        raise ValueError("profile snapshot contains missing/duplicate organisation numbers")
    return index


def website_claim(row: dict[str, Any]) -> dict[str, Any] | None:
    rows = [
        claim
        for claim in (row.get("claims") or [])
        if isinstance(claim, dict) and claim.get("field") == "official_website"
    ]
    if len(rows) != 1:
        return None
    return rows[0]


def non_website_claims(row: dict[str, Any]) -> list[str]:
    return sorted(
        json.dumps(claim, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for claim in (row.get("claims") or [])
        if isinstance(claim, dict) and claim.get("field") != "official_website"
    )


def evidence_by_id(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in (row.get("evidence") or [])
        if isinstance(item, dict) and item.get("id")
    }


def recovered_evidence_defects(row: dict[str, Any], claim: dict[str, Any]) -> list[str]:
    defects: list[str] = []
    refs = [str(ref) for ref in (claim.get("evidence_ids") or []) if str(ref)]
    if len(refs) != 2:
        defects.append("expected_two_evidence_ids")
        return defects

    evidence = evidence_by_id(row)
    items = [evidence.get(ref) for ref in refs]
    if any(item is None for item in items):
        defects.append("missing_evidence")
        return defects

    company_items = [item for item in items if item.get("source_class") == "company_owned"]
    official_items = [item for item in items if item.get("source_class") == "official"]
    if len(company_items) != 1:
        defects.append("missing_unique_company_owned_evidence")
    if len(official_items) != 1:
        defects.append("missing_unique_official_registry_evidence")
    if not company_items or not official_items:
        return defects

    company = company_items[0]
    official = official_items[0]
    for item, prefix in ((company, "company"), (official, "official")):
        if not str(item.get("source_url") or "").startswith(("http://", "https://")):
            defects.append(f"{prefix}_source_url_missing")
        if len(str(item.get("content_sha256") or "")) != 64:
            defects.append(f"{prefix}_content_sha256_invalid")
        if not str(item.get("claim_span") or "").strip():
            defects.append(f"{prefix}_claim_span_missing")

    proof = company.get("identity_proof")
    if not isinstance(proof, dict):
        defects.append("composite_identity_proof_missing")
    else:
        if proof.get("method") != METHOD:
            defects.append("unexpected_identity_method")
        if proof.get("status") != "exact" or proof.get("publishable") is not True:
            defects.append("composite_identity_not_exact_publishable")
        for key in (
            "final_domain",
            "registry_declared_domain",
            "registry_email_domain",
        ):
            if not str(proof.get(key) or ""):
                defects.append(f"identity_{key}_missing")
        if (
            proof.get("final_domain")
            != proof.get("registry_declared_domain")
            or proof.get("final_domain") != proof.get("registry_email_domain")
        ):
            defects.append("identity_domains_do_not_agree")
        if not proof.get("substantive_legal_name_tokens"):
            defects.append("substantive_name_tokens_missing")

    if official.get("source_field") != "/hjemmeside + /epostadresse":
        defects.append("official_registry_source_field_mismatch")
    if official.get("extraction_method") != METHOD:
        defects.append("official_registry_method_mismatch")
    return defects


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline-output", type=Path, required=True)
    p.add_argument("--profiles", type=Path, required=True)
    p.add_argument("--challenger-output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--manual-audit", type=Path, required=True)
    p.add_argument(
        "--mode",
        choices=("development", "transfer_a", "transfer_b"),
        default="development",
    )
    p.add_argument("--minimum-recoveries", type=int)
    args = p.parse_args()
    minimum_recoveries = (
        int(args.minimum_recoveries)
        if args.minimum_recoveries is not None
        else (MIN_DEVELOPMENT_RECOVERIES if args.mode == "development" else MIN_TRANSFER_RECOVERIES)
    )
    if minimum_recoveries < 1:
        raise ValueError("minimum recoveries must be positive")

    baseline = read_jsonl(args.baseline_output)
    profiles = profile_index(args.profiles)
    if len(baseline) != 100:
        raise ValueError(f"expected 100 companies, got {len(baseline)}")
    orgs = [str(row.get("organisation_number") or "") for row in baseline]
    if len(set(orgs)) != 100 or set(orgs) != set(profiles):
        raise ValueError("baseline/profile company sets differ")

    challenger: list[dict[str, Any]] = []
    manual: list[dict[str, Any]] = []
    errors: list[str] = []
    evidence_defects: list[dict[str, Any]] = []
    recovered_orgs: list[str] = []
    baseline_available = 0
    challenger_available = 0

    for row in baseline:
        org = str(row.get("organisation_number") or "")
        profile = profiles[org]
        before_claim = website_claim(row)
        if before_claim is None:
            errors.append(f"{org}:expected_one_official_website_claim")
            challenger.append(row)
            continue
        baseline_available += int(before_claim.get("availability") == "available")

        projected = project_registry_domain_composite_website(row, profile)
        item = project_canonical_profile(projected)
        item["synthesis"] = build_company_synthesis(item)

        for error in validate_contract_object(item):
            errors.append(f"{org}:contract:{error}")
        for error in validate_canonical_projection(item):
            errors.append(f"{org}:canonical:{error}")
        for error in validate_company_synthesis(item):
            errors.append(f"{org}:synthesis:{error}")

        if non_website_claims(item) != non_website_claims(row):
            errors.append(f"{org}:non_website_claim_mutation")

        after_claim = website_claim(item)
        if after_claim is None:
            errors.append(f"{org}:challenger_missing_website_claim")
            challenger.append(item)
            continue
        challenger_available += int(after_claim.get("availability") == "available")

        recovered = (
            before_claim.get("availability") == "ambiguous"
            and before_claim.get("value") is None
            and after_claim.get("availability") == "available"
            and str(after_claim.get("value") or "").startswith(("http://", "https://"))
            and after_claim.get("signal_type") == "registry_domain_composite_identity_recovery"
        )
        unexpected_transition = (
            json.dumps(before_claim, sort_keys=True, ensure_ascii=False)
            != json.dumps(after_claim, sort_keys=True, ensure_ascii=False)
            and not recovered
        )
        if unexpected_transition:
            errors.append(f"{org}:unexpected_website_claim_transition")

        if recovered:
            recovered_orgs.append(org)
            defects = recovered_evidence_defects(item, after_claim)
            if defects:
                evidence_defects.append({
                    "organisation_number": org,
                    "defects": defects,
                })
            ev = evidence_by_id(item)
            manual.append({
                "organisation_number": org,
                "before": before_claim,
                "after": after_claim,
                "evidence": [
                    ev.get(str(ref))
                    for ref in (after_claim.get("evidence_ids") or [])
                    if ev.get(str(ref))
                ],
                "manual_review_finalized": False,
            })

        challenger.append(item)

    if evidence_defects:
        errors.append(f"evidence_defects:{len(evidence_defects)}")

    if errors:
        decision = "BLOCKED"
    elif len(recovered_orgs) < minimum_recoveries:
        decision = "SHELVE_LOW_YIELD"
    elif args.mode == "development":
        decision = "DEVELOPMENT_SIGNAL_REQUIRES_DISJOINT_TRANSFER"
    elif args.mode == "transfer_a":
        decision = "TRANSFER_A_MANUAL_AUDIT_REQUIRED"
    else:
        decision = "TRANSFER_B_MANUAL_AUDIT_REQUIRED"

    report = {
        "milestone": "M19",
        "screen": f"offline_{args.mode}_registry_domain_composite_identity",
        "companies": 100,
        "machine_decision": decision,
        "evaluation_mode": args.mode,
        "development_cohort_only": args.mode == "development",
        "minimum_recoveries": minimum_recoveries,
        "minimum_development_recoveries": MIN_DEVELOPMENT_RECOVERIES,
        "minimum_transfer_recoveries": MIN_TRANSFER_RECOVERIES,
        "baseline_available_website_companies": baseline_available,
        "challenger_available_website_companies": challenger_available,
        "net_new_verified_website_companies": len(recovered_orgs),
        "recovered_organisation_numbers": sorted(recovered_orgs),
        "manual_review_rows": len(manual),
        "manual_review_finalized": False,
        "evidence_defects": evidence_defects,
        "validation_errors": errors,
        "non_website_claim_mutations_allowed": False,
        "network_requests_added_by_replay": 0,
        "search_api_requests_added_by_replay": 0,
        "third_party_cost_usd_added_by_replay": 0.0,
        "fresh_companies_used": 0,
        "production_promotion_authorized": False,
        "fresh_qualification_authorized": False,
        "builderr_score_claimed": False,
        "transfer_requirement": (
            "Q8 development positives require disjoint consumed transfer. Transfer A positives require "
            "100% manual row review before the already-frozen Gate B may run. Transfer B positives still "
            "do not authorize fresh qualification or production without an explicit promotion decision."
        ),
    }

    write_jsonl(args.challenger_output, challenger)
    write_jsonl(args.manual_audit, manual)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if decision == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
