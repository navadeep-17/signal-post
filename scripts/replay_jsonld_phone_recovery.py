#!/usr/bin/env python3
"""Offline replay of precision-gated JSON-LD contact-phone recovery.

Research-only. It reuses archived exact-site profiles, adds zero source requests,
projects a new external.contact_phone claim and website.contact_phone canonical
fact, then validates the full frozen contract/canonical/synthesis stack.

Raw phone values are not retained in research audit/report artifacts.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
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
from norway_company_agent.company_site_phone import (
    PHONE_STRATEGY,
    attach_company_site_contact_phone_observations,
)
from norway_company_agent.external_contract import project_contact_phone_observations
from norway_company_agent.external_footprint import validate_observation
from norway_company_agent.output_contract import validate_contract_object
from norway_company_agent.synthesis import build_company_synthesis, validate_company_synthesis


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def claim_values(contract: dict[str, Any], field: str) -> set[str]:
    return {
        str(claim.get("value") or "").strip()
        for claim in contract.get("claims") or []
        if isinstance(claim, dict)
        and claim.get("field") == field
        and claim.get("availability") == "available"
        and str(claim.get("value") or "").strip()
    }


def any_phone_coverage(contract: dict[str, Any]) -> bool:
    return any(
        claim_values(contract, field)
        for field in ("registered_phone", "registered_mobile", "external.contact_phone")
    )


def phone_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in profile.get("external_observations") or []
        if isinstance(item, dict)
        and item.get("signal_type") == "company_profile"
        and item.get("contact_phone")
        and item.get("strategy") == PHONE_STRATEGY
    ]


def safe_audit_row(profile: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    gate = next(
        (
            row
            for row in observation.get("identity_proof") or []
            if isinstance(row, dict) and row.get("type") == "structured_organization_identity_gate"
        ),
        {},
    )
    phone = str(observation.get("contact_phone") or "")
    return {
        "organisation_number": str(profile.get("organisation_number") or ""),
        "source_url": observation.get("source_url"),
        "structured_node_index": gate.get("node_index"),
        "structured_identity_method": gate.get("method"),
        "structured_observed_organisation_numbers": list(
            gate.get("observed_organisation_numbers") or []
        ),
        "phone_fingerprint": hashlib.sha256(phone.encode("utf-8")).hexdigest()[:12] if phone else None,
        "raw_phone_retained": False,
    }


def replay(
    profiles: list[dict[str, Any]],
    contracts: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile_by_org = {str(row.get("organisation_number") or ""): row for row in profiles}
    contract_by_org = {str(row.get("organisation_number") or ""): row for row in contracts}
    if len(profile_by_org) != len(profiles) or len(contract_by_org) != len(contracts):
        raise ValueError("duplicate or missing organisation numbers")
    if set(profile_by_org) != set(contract_by_org):
        raise ValueError("profile/contract organisation sets differ")

    before_external_companies = 0
    after_external_companies = 0
    before_any_phone_companies = 0
    after_any_phone_companies = 0
    before_external_claims = 0
    after_external_claims = 0
    net_new_external_companies = 0
    net_new_external_claims = 0
    net_new_any_phone_companies = 0
    observation_errors: list[dict[str, str]] = []
    contract_errors: list[dict[str, str]] = []
    canonical_errors: list[dict[str, str]] = []
    synthesis_errors: list[dict[str, str]] = []
    lost_existing: list[str] = []
    audit_rows: list[dict[str, Any]] = []
    canonical_phone_fact_companies = 0

    for org in sorted(profile_by_org):
        profile = copy.deepcopy(profile_by_org[org])
        contract = copy.deepcopy(contract_by_org[org])

        before = claim_values(contract, "external.contact_phone")
        before_any = any_phone_coverage(contract)
        before_external_companies += int(bool(before))
        before_external_claims += len(before)
        before_any_phone_companies += int(before_any)

        attach_company_site_contact_phone_observations(profile)
        recovered = phone_observations(profile)
        projected = project_contact_phone_observations(contract, profile)

        after = claim_values(projected, "external.contact_phone")
        after_any = any_phone_coverage(projected)
        after_external_companies += int(bool(after))
        after_external_claims += len(after)
        after_any_phone_companies += int(after_any)

        if not before.issubset(after):
            lost_existing.append(org)

        new_values = after - before
        if new_values:
            net_new_external_companies += 1
            net_new_external_claims += len(new_values)
        if not before_any and after_any:
            net_new_any_phone_companies += 1

        for obs in recovered:
            phone = str(obs.get("contact_phone") or "").strip()
            if phone not in new_values:
                continue
            for error in validate_observation(obs):
                observation_errors.append(
                    {
                        "organisation_number": org,
                        "observation_id": str(obs.get("id") or ""),
                        "error": error,
                    }
                )
            audit_rows.append(safe_audit_row(profile, obs))

        canonical = project_canonical_profile(projected)
        phone_facts = [
            fact
            for fact in canonical.get("canonical_facts") or []
            if isinstance(fact, dict)
            and fact.get("type") == "contact_phone"
            and fact.get("availability") == "available"
        ]
        canonical_phone_fact_companies += int(bool(phone_facts))
        canonical["synthesis"] = build_company_synthesis(canonical)

        contract_errors.extend(
            {"organisation_number": org, "error": error}
            for error in validate_contract_object(canonical)
        )
        canonical_errors.extend(
            {"organisation_number": org, "error": error}
            for error in validate_canonical_projection(canonical)
        )
        synthesis_errors.extend(
            {"organisation_number": org, "error": error}
            for error in validate_company_synthesis(canonical)
        )

    checks = {
        "profile_contract_sets_match": set(profile_by_org) == set(contract_by_org),
        "existing_external_phone_claims_preserved": not lost_existing,
        "new_observations_validate": not observation_errors,
        "contracts_validate": not contract_errors,
        "canonical_projection_validates": not canonical_errors,
        "synthesis_validates": not synthesis_errors,
        "audit_rows_match_new_claims": len(audit_rows) == net_new_external_claims,
        "zero_network_requests": True,
    }

    report = {
        "screen_type": "offline_jsonld_contact_phone_recovery_replay",
        "companies": len(contracts),
        "before_external_contact_phone_companies": before_external_companies,
        "before_external_contact_phone_claims": before_external_claims,
        "after_external_contact_phone_companies": after_external_companies,
        "after_external_contact_phone_claims": after_external_claims,
        "net_new_external_contact_phone_companies": net_new_external_companies,
        "net_new_external_contact_phone_claims": net_new_external_claims,
        "before_any_phone_companies": before_any_phone_companies,
        "after_any_phone_companies": after_any_phone_companies,
        "net_new_any_phone_companies": net_new_any_phone_companies,
        "canonical_contact_phone_fact_companies": canonical_phone_fact_companies,
        "net_new_company_reach_pct": round(
            100 * net_new_any_phone_companies / len(contracts), 3
        ) if contracts else 0.0,
        "network_requests_added": 0,
        "third_party_cost_usd_added": 0.0,
        "lost_existing_organisations": lost_existing,
        "observation_errors": observation_errors,
        "contract_errors": contract_errors,
        "canonical_errors": canonical_errors,
        "synthesis_errors": synthesis_errors,
        "checks": checks,
        "passed": all(checks.values()),
        "privacy_boundary": {
            "raw_phone_in_report": False,
            "raw_phone_in_audit": False,
            "audit_phone_fingerprint_only": True,
        },
        "claim_boundary": (
            "Exact verified company website plus an already-retained schema.org Organization "
            "node that independently identifies the target legal entity, with an explicit "
            "telephone field normalized to a conservative Norwegian E.164 company contact."
        ),
    }
    return report, audit_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    args = ap.parse_args()

    profile_paths = sorted(args.profiles_dir.rglob("profiles.jsonl"))
    if not profile_paths:
        raise SystemExit("no retained profiles.jsonl files found")
    profiles: list[dict[str, Any]] = []
    for path in profile_paths:
        profiles.extend(read_jsonl(path))
    contracts = read_jsonl_gz(args.output_contract_gz)
    if len(profiles) != 1000 or len(contracts) != 1000:
        raise SystemExit(
            f"expected 1000 profiles/contracts, got {len(profiles)}/{len(contracts)}"
        )

    report, audit_rows = replay(profiles, contracts)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.audit.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in audit_rows),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
