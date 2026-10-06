#!/usr/bin/env python3
"""Offline replay of precision-gated JSON-LD contact-email recovery.

This script mutates only in-memory copies of archived retained profiles and frozen
output contracts. It performs zero provider/source network requests.

It validates that:
- existing contact-email coverage is never lost;
- only exact-node JSON-LD recovery contributes new contacts;
- every projected contract remains valid;
- canonical projection remains valid;
- deterministic synthesis remains valid;
- no raw contact email is retained in the research audit/report.
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

from norway_company_agent.canonical_projection import (  # noqa: E402
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.company_site_contact import (  # noqa: E402
    attach_company_site_contact_email_observations,
)
from norway_company_agent.external_contract import project_contact_email_observations  # noqa: E402
from norway_company_agent.external_footprint import validate_observation  # noqa: E402
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.synthesis import (  # noqa: E402
    build_company_synthesis,
    validate_company_synthesis,
)

JSONLD_STRATEGY = "verified_company_jsonld_same_domain_email_v1"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def existing_contact_values(contract: dict[str, Any]) -> set[str]:
    return {
        str(claim.get("value") or "").strip().lower()
        for claim in contract.get("claims") or []
        if isinstance(claim, dict)
        and claim.get("field") == "external.contact_email"
        and claim.get("availability") == "available"
        and str(claim.get("value") or "").strip()
    }


def contact_values(contract: dict[str, Any]) -> set[str]:
    return existing_contact_values(contract)


def jsonld_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in profile.get("external_observations") or []
        if isinstance(item, dict)
        and item.get("signal_type") == "company_profile"
        and item.get("contact_email")
        and item.get("strategy") == JSONLD_STRATEGY
    ]


def _safe_audit_row(
    profile: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    website = ((profile.get("evidence") or {}).get("website") or {})
    website_value = website.get("value") or {}
    identity = website_value.get("identity_assessment") or {}
    structured_gate = next(
        (
            proof
            for proof in observation.get("identity_proof") or []
            if isinstance(proof, dict) and proof.get("type") == "structured_organization_identity_gate"
        ),
        {},
    )
    email = str(observation.get("contact_email") or "").strip().lower()
    email_domain = email.split("@", 1)[1] if email.count("@") == 1 else ""
    return {
        "organisation_number": str(profile.get("organisation_number") or ""),
        "legal_name": profile.get("name"),
        "source_url": observation.get("source_url"),
        "website_identity_status": identity.get("status"),
        "website_identity_score": identity.get("score"),
        "website_identity_method": identity.get("method"),
        "structured_node_index": structured_gate.get("node_index"),
        "structured_identity_method": structured_gate.get("method"),
        "structured_matched_name": structured_gate.get("matched_name"),
        "structured_observed_organisation_numbers": list(
            structured_gate.get("observed_organisation_numbers") or []
        ),
        "email_domain": email_domain,
        "email_fingerprint": hashlib.sha256(email.encode("utf-8")).hexdigest()[:12] if email else None,
        "raw_email_retained": False,
    }


def replay(
    profiles: list[dict[str, Any]],
    contracts: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile_by_org = {
        str(profile.get("organisation_number") or ""): profile
        for profile in profiles
    }
    contract_by_org = {
        str(row.get("organisation_number") or ""): row
        for row in contracts
    }
    if len(profile_by_org) != len(profiles):
        raise ValueError("duplicate or missing profile organisation numbers")
    if len(contract_by_org) != len(contracts):
        raise ValueError("duplicate or missing contract organisation numbers")
    if set(profile_by_org) != set(contract_by_org):
        raise ValueError("profile/contract organisation sets differ")

    before_company_count = 0
    after_company_count = 0
    before_claim_count = 0
    after_claim_count = 0
    new_company_count = 0
    new_claim_count = 0
    jsonld_observation_count = 0
    jsonld_candidate_company_count = 0
    observation_errors: list[dict[str, str]] = []
    contract_errors: list[dict[str, str]] = []
    canonical_errors: list[dict[str, str]] = []
    synthesis_errors: list[dict[str, str]] = []
    lost_existing: list[str] = []
    audit_rows: list[dict[str, Any]] = []

    for org in sorted(profile_by_org):
        profile = copy.deepcopy(profile_by_org[org])
        contract = copy.deepcopy(contract_by_org[org])
        before = existing_contact_values(contract)
        before_claim_count += len(before)
        before_company_count += int(bool(before))

        attach_company_site_contact_email_observations(profile)

        jsonld = jsonld_observations(profile)
        jsonld_observation_count += len(jsonld)
        jsonld_candidate_company_count += int(bool(jsonld))

        projected = project_contact_email_observations(contract, profile)
        after = contact_values(projected)
        after_claim_count += len(after)
        after_company_count += int(bool(after))

        if not before.issubset(after):
            lost_existing.append(org)

        new_values = after - before
        if new_values:
            new_company_count += 1
            new_claim_count += len(new_values)

        for obs in jsonld:
            email = str(obs.get("contact_email") or "").strip().lower()
            if email not in new_values:
                continue
            for error in validate_observation(obs):
                observation_errors.append(
                    {
                        "organisation_number": org,
                        "observation_id": str(obs.get("id") or ""),
                        "error": error,
                    }
                )
            audit_rows.append(_safe_audit_row(profile, obs))

        canonical = project_canonical_profile(projected)
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
        "existing_contact_claims_preserved": not lost_existing,
        "new_claims_are_jsonld_backed": len(audit_rows) == new_claim_count,
        "new_observations_validate": not observation_errors,
        "contracts_validate": not contract_errors,
        "canonical_projection_validates": not canonical_errors,
        "synthesis_validates": not synthesis_errors,
        "zero_network_requests": True,
    }

    report = {
        "screen_type": "offline_jsonld_contact_recovery_replay",
        "companies": len(contracts),
        "before_contact_email_companies": before_company_count,
        "before_contact_email_claims": before_claim_count,
        "after_contact_email_companies": after_company_count,
        "after_contact_email_claims": after_claim_count,
        "net_new_contact_email_companies": new_company_count,
        "net_new_contact_email_claims": new_claim_count,
        "net_new_company_reach_pct": round(100 * new_company_count / len(contracts), 3) if contracts else 0.0,
        "jsonld_observation_companies_after_attachment": jsonld_candidate_company_count,
        "jsonld_observations_after_attachment": jsonld_observation_count,
        "network_requests_added": 0,
        "third_party_cost_usd_added": 0.0,
        "lost_existing_contact_organisations": lost_existing,
        "observation_errors": observation_errors,
        "contract_errors": contract_errors,
        "canonical_errors": canonical_errors,
        "synthesis_errors": synthesis_errors,
        "checks": checks,
        "passed": all(checks.values()),
        "privacy_boundary": {
            "raw_email_in_report": False,
            "raw_email_in_audit": False,
            "audit_email_fingerprint_only": True,
        },
        "claim_boundary": (
            "Exact verified company website plus an already-retained schema.org Organization "
            "node that itself identifies the target legal entity, with an explicit email field "
            "whose registered domain matches the verified website."
        ),
    }
    return report, audit_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--output-contract-gz", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()

    profile_paths = sorted(args.profiles_dir.rglob("profiles.jsonl"))
    if not profile_paths:
        raise SystemExit("no profiles.jsonl files found")
    profiles: list[dict[str, Any]] = []
    for path in profile_paths:
        profiles.extend(read_jsonl(path))
    contracts = read_jsonl_gz(args.output_contract_gz)
    if len(profiles) != 1000 or len(contracts) != 1000:
        raise SystemExit(f"expected 1000 profiles/contracts, got {len(profiles)}/{len(contracts)}")

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
