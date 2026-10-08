#!/usr/bin/env python3
"""M24 zero-network, human-review-only pilot prerequisite checker.

This NEVER authorises, starts, or implements a live provider request. An
attestation is a *self-reported* claim with evidence references, not proof
of rights. The approver still must inspect source documents independently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PARENT = "200f056a5a60cad23610a3958b6bec62dfb624a5"
EXPECTED_LIST_SHA = "3967c2a4b16e6645d3426168d32511944c5e196d19e147b65924925c69c6360e"
COHORT_COUNTS = {"m19_a": 7, "m19_b": 7, "m20_a": 6}
REQUIREMENTS = {
    "competition_use": "Provider permission for the student competition",
    "public_results": "Permission/interpretation for third-party aggregate reporting under Tavily Terms 3.2(x)",
    "evaluator_key": "Written agreement on API key use by an independent evaluator under Terms section 2",
    "free_account": "Verified account is on no-charge Researcher Free, with no overage/upgrade",
    "credit_reserve": "Verified account has at least 100 unspent basic-search credits for the pilot/batch",
    "bounded_runtime": "Worst-case full evaluator path proven within 2400 seconds for 100 companies",
    "request_theorem": "Code-level proof of at most 2000 conservative charged requests for 100 companies",
    "owner_precision": "Independent page proof and existing wrong-owner veto retained",
}

def reject_sensitive_attestation(data: Any) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            lk = key.lower()
            if any(x in lk for x in ("secret", "password", "credential", "api_key", "api-key", "bearer", "token")):
                raise ValueError("Attestation cannot contain credentials/secrets/tokens")
            reject_sensitive_attestation(value)
    elif isinstance(data, list):
        for child in data:
            reject_sensitive_attestation(child)

def check_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("schema") != "v10_m24_consumed_dev_20_v1":
        raise ValueError("Incorrect frozen manifest schema")
    if manifest.get("qualified_v8_sha") != PARENT:
        raise ValueError("Source is not exact qualified V8 parent")
    if manifest.get("type") != "PRIOR_CONSUMED_ONLY_NOT_TRANSFER":
        raise ValueError("Attempt to relabel development cohort as fresh/transfer")
    if manifest.get("live_provider_authorized") is not False:
        raise ValueError("Development cohort must explicitly prohibit live API calls")
    if manifest.get("permission_to_merge") is not False:
        raise ValueError("Development cohort cannot authorise merge")
    groups = manifest.get("selected_per_cohort")
    if not isinstance(groups, dict) or set(groups) != set(COHORT_COUNTS):
        raise ValueError("Cohort names differ from frozen M24")
    ordered = []
    for group, n in COHORT_COUNTS.items():
        subset = groups[group]
        if not isinstance(subset, list) or len(subset) != n:
            raise ValueError(f"Wrong frozen cohort allocation: {group}")
        for org in subset:
            if not isinstance(org, str) or len(org) != 9 or not org.isascii() or not org.isdecimal():
                raise ValueError("Org number must be a 9-character ASCII string")
            ordered.append(org)
    if len(ordered) != len(set(ordered)) or len(ordered) != manifest.get("count") or len(ordered) != 20:
        raise ValueError("Not exactly 20 unique consumed entities")
    computed = hashlib.sha256("\n".join(ordered).encode()).hexdigest()
    if computed != EXPECTED_LIST_SHA or manifest.get("selected_list_sha256") != computed:
        raise ValueError("Frozen selected IDs/order changed")
    return {"count": len(ordered), "sha256": computed, "frozen": True}

def evaluate(manifest: dict[str, Any], attestation: dict[str, Any] | None = None) -> dict[str, Any]:
    frozen = check_manifest(manifest)
    if attestation is not None:
        reject_sensitive_attestation(attestation)
        if not isinstance(attestation, dict):
            raise ValueError("Attestation must be JSON object")
    attest = attestation or {}
    evidence = attest.get("evidence") or {}
    if not isinstance(evidence, dict):
        raise ValueError("Attestation evidence must be object")
    missing = []
    declared = []
    for code, label in REQUIREMENTS.items():
        item = evidence.get(code)
        if not isinstance(item, dict) or item.get("verified") is not True or not isinstance(item.get("reference"), str) or not item["reference"].strip():
            missing.append(code)
        else:
            # This records only that a human supplied a citation.
            # It does NOT fetch, validate, or legally interpret that citation.
            declared.append(code)
    return {
        "schema": "v10_m24_nonexecuting_pilot_preflight_v1",
        "qualified_v8_sha": PARENT,
        "frozen_development_count": frozen["count"],
        "frozen_selection_sha256": frozen["sha256"],
        "self_reported_evidence_items": declared,
        "missing_or_unattested_items": missing,
        "manual_independent_review_required": True,
        "self_reported_requirements_complete": not missing,
        "provider_permission_independently_verified": False,
        "run_production_code_request_ceiling_proven": False,
        "real_provider_runtime_measured": False,
        "external_requests_performed": 0,
        "live_provider_authorized": False,
        "fresh_evaluation_authorized": False,
        "production_promotion_authorized": False,
        "decision": "BLOCKED_PENDING_INDEPENDENT_PROVIDER_AND_ENGINEERING_REVIEW"
    }

def main() -> None:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--manifest", type=Path, required=True)
    a.add_argument("--attestation", type=Path, help="Optional local self-reported documentary reference file (never an API key)")
    a.add_argument("--output", type=Path, required=True)
    args = a.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    attestation = json.loads(args.attestation.read_text(encoding="utf-8")) if args.attestation else None
    report = evaluate(manifest, attestation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"M24 pilot gate: {report['decision']}; missing {len(report['missing_or_unattested_items'])}/{len(REQUIREMENTS)}; provider requests=0")

if __name__ == "__main__":
    main()
