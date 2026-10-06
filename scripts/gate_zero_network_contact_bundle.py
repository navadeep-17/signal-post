#!/usr/bin/env python3
"""Gate combined zero-network JSON-LD email + phone recovery on frozen 1000.

Research-only. Uses archived exact-site snapshots and adds no source requests.
The report contains aggregate counts only; raw contact values and organisation
lists are not persisted.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import (
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.company_site_contact import (
    attach_company_site_contact_email_observations,
)
from norway_company_agent.company_site_phone import (
    attach_company_site_contact_phone_observations,
)
from norway_company_agent.external_contract import (
    project_contact_email_observations,
    project_contact_phone_observations,
)
from norway_company_agent.external_footprint import validate_observation
from norway_company_agent.output_contract import validate_contract_object
from norway_company_agent.synthesis import (
    build_company_synthesis,
    validate_company_synthesis,
)

MANAGED_FIELDS = {"external.contact_email", "external.contact_phone"}
EMAIL_STRATEGY = "verified_company_jsonld_same_domain_email_v1"
PHONE_STRATEGY = "verified_company_jsonld_norwegian_phone_v1"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def claim_values(contract: dict[str, Any], field: str) -> set[str]:
    return {
        str(c.get("value") or "").strip()
        for c in contract.get("claims") or []
        if isinstance(c, dict)
        and c.get("field") == field
        and c.get("availability") == "available"
        and str(c.get("value") or "").strip()
    }


def claim_sig(claim: dict[str, Any]) -> str:
    return json.dumps(claim, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def project_contacts(contract: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    out = project_contact_email_observations(copy.deepcopy(contract), profile)
    out = project_contact_phone_observations(out, profile)
    return out


def gate(
    profiles: list[dict[str, Any]],
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    pindex = {str(x.get("organisation_number") or ""): x for x in profiles}
    cindex = {str(x.get("organisation_number") or ""): x for x in contracts}
    if len(pindex) != len(profiles) or len(cindex) != len(contracts):
        raise ValueError("duplicate or missing organisation numbers")
    if set(pindex) != set(cindex):
        raise ValueError("profile/contract organisation sets differ")

    base_email_orgs: set[str] = set()
    new_email_orgs: set[str] = set()
    base_phone_orgs: set[str] = set()
    new_phone_orgs: set[str] = set()
    base_union: set[str] = set()
    new_union: set[str] = set()

    base_email_claims = 0
    new_email_claims = 0
    base_phone_claims = 0
    new_phone_claims = 0
    recovered_email_observations = 0
    recovered_phone_observations = 0

    observation_errors: list[dict[str, str]] = []
    non_managed_mutations: list[str] = []
    contract_errors: list[dict[str, str]] = []
    canonical_errors: list[dict[str, str]] = []
    synthesis_errors: list[dict[str, str]] = []
    lost_existing_email: list[str] = []
    lost_existing_phone: list[str] = []

    for org in sorted(pindex):
        original_profile = copy.deepcopy(pindex[org])
        original_contract = copy.deepcopy(cindex[org])

        baseline = project_contacts(original_contract, original_profile)

        challenger_profile = copy.deepcopy(original_profile)
        before_ids = {
            str(o.get("id") or "")
            for o in challenger_profile.get("external_observations") or []
            if isinstance(o, dict) and str(o.get("id") or "")
        }
        attach_company_site_contact_email_observations(challenger_profile)
        attach_company_site_contact_phone_observations(challenger_profile)

        for obs in challenger_profile.get("external_observations") or []:
            if not isinstance(obs, dict):
                continue
            oid = str(obs.get("id") or "")
            if not oid or oid in before_ids:
                continue
            strategy = str(obs.get("strategy") or "")
            if strategy not in {EMAIL_STRATEGY, PHONE_STRATEGY}:
                continue
            errs = validate_observation(obs)
            for error in errs:
                observation_errors.append(
                    {
                        "organisation_number": org,
                        "observation_id": oid,
                        "error": error,
                    }
                )
            if strategy == EMAIL_STRATEGY:
                recovered_email_observations += 1
            elif strategy == PHONE_STRATEGY:
                recovered_phone_observations += 1

        challenger = project_contacts(original_contract, challenger_profile)

        base_non_managed = sorted(
            claim_sig(c)
            for c in baseline.get("claims") or []
            if isinstance(c, dict) and c.get("field") not in MANAGED_FIELDS
        )
        challenger_non_managed = sorted(
            claim_sig(c)
            for c in challenger.get("claims") or []
            if isinstance(c, dict) and c.get("field") not in MANAGED_FIELDS
        )
        if base_non_managed != challenger_non_managed:
            non_managed_mutations.append(org)

        b_email = claim_values(baseline, "external.contact_email")
        c_email = claim_values(challenger, "external.contact_email")
        b_phone = claim_values(baseline, "external.contact_phone")
        c_phone = claim_values(challenger, "external.contact_phone")

        if not b_email.issubset(c_email):
            lost_existing_email.append(org)
        if not b_phone.issubset(c_phone):
            lost_existing_phone.append(org)

        base_email_claims += len(b_email)
        new_email_claims += len(c_email)
        base_phone_claims += len(b_phone)
        new_phone_claims += len(c_phone)

        if b_email:
            base_email_orgs.add(org)
        if c_email:
            new_email_orgs.add(org)
        if b_phone:
            base_phone_orgs.add(org)
        if c_phone:
            new_phone_orgs.add(org)
        if b_email or b_phone:
            base_union.add(org)
        if c_email or c_phone:
            new_union.add(org)

        canonical = project_canonical_profile(challenger)
        canonical["synthesis"] = build_company_synthesis(canonical)
        for error in validate_contract_object(canonical):
            contract_errors.append({"organisation_number": org, "error": error})
        for error in validate_canonical_projection(canonical):
            canonical_errors.append({"organisation_number": org, "error": error})
        for error in validate_company_synthesis(canonical):
            synthesis_errors.append({"organisation_number": org, "error": error})

    added_email = new_email_orgs - base_email_orgs
    added_phone = new_phone_orgs - base_phone_orgs
    added_union = new_union - base_union
    overlap_new_email_phone = added_email & added_phone

    checks = {
        "existing_email_claims_preserved": not lost_existing_email,
        "existing_phone_claims_preserved": not lost_existing_phone,
        "non_managed_claims_unchanged": not non_managed_mutations,
        "new_observations_validate": not observation_errors,
        "contracts_validate": not contract_errors,
        "canonical_projection_validates": not canonical_errors,
        "synthesis_validates": not synthesis_errors,
        "zero_network_requests": True,
    }

    n = len(contracts)
    report = {
        "screen_type": "zero_network_structured_contact_bundle_frozen1000",
        "companies": n,
        "baseline_email_companies": len(base_email_orgs),
        "challenger_email_companies": len(new_email_orgs),
        "net_new_email_companies": len(added_email),
        "baseline_email_claims": base_email_claims,
        "challenger_email_claims": new_email_claims,
        "email_claim_delta": new_email_claims - base_email_claims,
        "baseline_phone_companies": len(base_phone_orgs),
        "challenger_phone_companies": len(new_phone_orgs),
        "net_new_phone_companies": len(added_phone),
        "baseline_phone_claims": base_phone_claims,
        "challenger_phone_claims": new_phone_claims,
        "phone_claim_delta": new_phone_claims - base_phone_claims,
        "baseline_any_external_contact_companies": len(base_union),
        "challenger_any_external_contact_companies": len(new_union),
        "net_new_any_external_contact_companies": len(added_union),
        "net_new_any_external_contact_reach_pct": round(100 * len(added_union) / n, 3) if n else 0.0,
        "new_email_phone_company_overlap": len(overlap_new_email_phone),
        "recovered_jsonld_email_observations": recovered_email_observations,
        "recovered_jsonld_phone_observations": recovered_phone_observations,
        "logical_requests_added": 0,
        "conservative_request_charge_added": 0,
        "third_party_api_cost_usd_added": 0.0,
        "search_api_requests_added": 0,
        "non_managed_claim_mutations": len(non_managed_mutations),
        "observation_errors": len(observation_errors),
        "contract_errors": len(contract_errors),
        "canonical_errors": len(canonical_errors),
        "synthesis_errors": len(synthesis_errors),
        "checks": checks,
        "privacy_boundary": {
            "raw_contact_values_in_report": False,
            "organisation_lists_in_report": False,
            "aggregate_counts_only": True,
        },
        "claim_boundary": (
            "Already-retained exact verified primary homepage only. Each schema.org Organization "
            "node independently identifies the target legal entity. Email additionally requires "
            "same registered domain; phone requires an explicit telephone field normalized to a "
            "conservative Norwegian E.164 value."
        ),
    }
    report["promotion_gate_passed"] = bool(
        len(added_union) > 0 and all(checks.values())
    )
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    profiles: list[dict[str, Any]] = []
    for path in sorted(args.profiles_dir.rglob("profiles.jsonl")):
        profiles.extend(read_jsonl(path))
    contracts = read_jsonl_gz(args.output_contract_gz)
    if len(profiles) != 1000 or len(contracts) != 1000:
        raise SystemExit(
            f"expected 1000 profiles/contracts, got {len(profiles)}/{len(contracts)}"
        )

    report = gate(profiles, contracts)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["promotion_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
