#!/usr/bin/env python3
"""Gate the combined zero-network exact-site enrichment bundle on frozen contracts.

Research-only. Reuses already-retained exact homepage evidence; performs no network
access and does not alter the production runner.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import sys
from collections import Counter
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
from norway_company_agent.external_contract import (  # noqa: E402
    project_contact_email_observations,
    project_profile_handle_observations,
)
from norway_company_agent.external_footprint import validate_observation  # noqa: E402
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.synthesis import (  # noqa: E402
    build_company_synthesis,
    validate_company_synthesis,
)
from norway_company_agent.zero_network_social_recovery import (  # noqa: E402
    STRATEGY as SOCIAL_STRATEGY,
    attach_zero_network_social_recovery,
)

JSONLD_CONTACT_STRATEGY = "verified_company_jsonld_same_domain_email_v1"
MANAGED_FIELDS = {"social_links", "external.profile_handle", "external.contact_email"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _claim_sig(claim: dict[str, Any]) -> str:
    return json.dumps(claim, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _available_claims(contract: dict[str, Any], field: str) -> list[dict[str, Any]]:
    return [
        c
        for c in contract.get("claims") or []
        if isinstance(c, dict)
        and c.get("field") == field
        and c.get("availability") == "available"
    ]


def _project(contract: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    # Social projection owns careers normalization as part of its existing projector
    # composition. Contact projection manages only external.contact_email and therefore
    # composes losslessly on top.
    projected = project_profile_handle_observations(copy.deepcopy(contract), profile)
    projected = project_contact_email_observations(projected, profile)
    return projected


def gate(
    profiles: list[dict[str, Any]],
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    pindex = {str(p.get("organisation_number") or ""): p for p in profiles}
    cindex = {str(c.get("organisation_number") or ""): c for c in contracts}
    if len(pindex) != len(profiles) or len(cindex) != len(contracts):
        raise ValueError("duplicate or missing organisation numbers")
    if set(pindex) != set(cindex):
        raise ValueError("profile/contract organisation sets differ")

    baseline_contact: set[str] = set()
    challenger_contact: set[str] = set()
    baseline_social: set[str] = set()
    challenger_social: set[str] = set()
    baseline_union: set[str] = set()
    challenger_union: set[str] = set()

    baseline_contact_claims = 0
    challenger_contact_claims = 0
    baseline_social_claims = 0
    challenger_social_claims = 0

    new_contact_observations = 0
    new_social_observations = 0
    added_social_platforms: Counter[str] = Counter()
    observation_errors: list[dict[str, str]] = []
    non_managed_mutations: list[str] = []
    contract_errors: list[dict[str, str]] = []
    canonical_errors: list[dict[str, str]] = []
    synthesis_errors: list[dict[str, str]] = []
    area_before: Counter[str] = Counter()
    area_after: Counter[str] = Counter()

    for org in sorted(pindex):
        original_profile = copy.deepcopy(pindex[org])
        original_contract = copy.deepcopy(cindex[org])

        baseline = _project(original_contract, original_profile)

        challenger_profile = copy.deepcopy(original_profile)
        before_obs_ids = {
            str(o.get("id") or "")
            for o in challenger_profile.get("external_observations") or []
            if isinstance(o, dict) and str(o.get("id") or "")
        }
        attach_company_site_contact_email_observations(challenger_profile)
        attach_zero_network_social_recovery(challenger_profile)

        for obs in challenger_profile.get("external_observations") or []:
            if not isinstance(obs, dict):
                continue
            oid = str(obs.get("id") or "")
            if not oid or oid in before_obs_ids:
                continue
            strategy = str(obs.get("strategy") or "")
            if strategy not in {JSONLD_CONTACT_STRATEGY, SOCIAL_STRATEGY}:
                continue
            errs = validate_observation(obs)
            for error in errs:
                observation_errors.append(
                    {"organisation_number": org, "observation_id": oid, "error": error}
                )
            if strategy == JSONLD_CONTACT_STRATEGY:
                new_contact_observations += 1
            elif strategy == SOCIAL_STRATEGY:
                new_social_observations += 1
                added_social_platforms[str(obs.get("platform") or "unknown")] += 1

        challenger = _project(original_contract, challenger_profile)

        base_non_managed = sorted(
            _claim_sig(c)
            for c in baseline.get("claims") or []
            if isinstance(c, dict) and c.get("field") not in MANAGED_FIELDS
        )
        new_non_managed = sorted(
            _claim_sig(c)
            for c in challenger.get("claims") or []
            if isinstance(c, dict) and c.get("field") not in MANAGED_FIELDS
        )
        if base_non_managed != new_non_managed:
            non_managed_mutations.append(org)

        base_contacts = _available_claims(baseline, "external.contact_email")
        new_contacts = _available_claims(challenger, "external.contact_email")
        base_socials = _available_claims(baseline, "external.profile_handle")
        new_socials = _available_claims(challenger, "external.profile_handle")

        baseline_contact_claims += len(base_contacts)
        challenger_contact_claims += len(new_contacts)
        baseline_social_claims += len(base_socials)
        challenger_social_claims += len(new_socials)

        if base_contacts:
            baseline_contact.add(org)
        if new_contacts:
            challenger_contact.add(org)
        if base_socials:
            baseline_social.add(org)
        if new_socials:
            challenger_social.add(org)
        if base_contacts or base_socials:
            baseline_union.add(org)
        if new_contacts or new_socials:
            challenger_union.add(org)

        base_canonical = project_canonical_profile(baseline)
        new_canonical = project_canonical_profile(challenger)
        base_canonical["synthesis"] = build_company_synthesis(base_canonical)
        new_canonical["synthesis"] = build_company_synthesis(new_canonical)

        for area, value in ((base_canonical.get("canonical_profile") or {}).get("data_areas") or {}).items():
            area_before[area] += int(bool(value))
        for area, value in ((new_canonical.get("canonical_profile") or {}).get("data_areas") or {}).items():
            area_after[area] += int(bool(value))

        for error in validate_contract_object(new_canonical):
            contract_errors.append({"organisation_number": org, "error": error})
        for error in validate_canonical_projection(new_canonical):
            canonical_errors.append({"organisation_number": org, "error": error})
        for error in validate_company_synthesis(new_canonical):
            synthesis_errors.append({"organisation_number": org, "error": error})

    lost_contact = baseline_contact - challenger_contact
    lost_social = baseline_social - challenger_social
    new_contact_coverage = challenger_contact - baseline_contact
    new_social_coverage = challenger_social - baseline_social
    new_union_coverage = challenger_union - baseline_union

    report = {
        "screen_type": "combined_zero_network_exact_site_enrichment_gate_frozen1000",
        "companies": len(contracts),
        "baseline_contact_companies": len(baseline_contact),
        "challenger_contact_companies": len(challenger_contact),
        "newly_covered_contact_companies": len(new_contact_coverage),
        "baseline_contact_claims": baseline_contact_claims,
        "challenger_contact_claims": challenger_contact_claims,
        "contact_claim_delta": challenger_contact_claims - baseline_contact_claims,
        "baseline_social_companies": len(baseline_social),
        "challenger_social_companies": len(challenger_social),
        "newly_covered_social_companies": len(new_social_coverage),
        "baseline_social_claims": baseline_social_claims,
        "challenger_social_claims": challenger_social_claims,
        "social_claim_delta": challenger_social_claims - baseline_social_claims,
        "baseline_contact_or_social_companies": len(baseline_union),
        "challenger_contact_or_social_companies": len(challenger_union),
        "net_new_contact_or_social_companies": len(new_union_coverage),
        "net_new_contact_or_social_reach_pct": round(
            100 * len(new_union_coverage) / len(contracts), 3
        ) if contracts else 0.0,
        "new_jsonld_contact_observations_attached": new_contact_observations,
        "new_social_observations_attached": new_social_observations,
        "added_social_platform_counts": dict(sorted(added_social_platforms.items())),
        "lost_contact_companies": len(lost_contact),
        "lost_social_companies": len(lost_social),
        "non_managed_claim_mutations": len(non_managed_mutations),
        "observation_errors": len(observation_errors),
        "contract_errors": len(contract_errors),
        "canonical_errors": len(canonical_errors),
        "synthesis_errors": len(synthesis_errors),
        "canonical_data_area_before": dict(sorted(area_before.items())),
        "canonical_data_area_after": dict(sorted(area_after.items())),
        "company_website_area_delta": area_after["company_website"] - area_before["company_website"],
        "hiring_public_activity_area_delta": (
            area_after["hiring_and_public_activity"] - area_before["hiring_and_public_activity"]
        ),
        "logical_requests_added": 0,
        "conservative_request_charge_added": 0,
        "third_party_api_cost_usd_added": 0.0,
        "search_api_requests_added": 0,
        "privacy_boundary": {
            "raw_contact_values_in_report": False,
            "raw_social_urls_in_report": False,
            "organisation_lists_in_report": False,
            "aggregate_counts_only": True,
        },
        "publication_boundary": (
            "Already-retained exact verified primary homepage only. Contact recovery requires "
            "an individually identified schema.org Organization node plus same registered-domain "
            "email. Social recovery requires a homepage-declared canonical social URL plus the "
            "existing deterministic handle identity gate. No secondary/social page fetches."
        ),
    }
    report["promotion_gate_passed"] = bool(
        len(new_union_coverage) > 0
        and not lost_contact
        and not lost_social
        and not non_managed_mutations
        and not observation_errors
        and not contract_errors
        and not canonical_errors
        and not synthesis_errors
    )
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    profile_paths = sorted(args.profiles_dir.rglob("profiles.jsonl"))
    profiles: list[dict[str, Any]] = []
    for path in profile_paths:
        profiles.extend(read_jsonl(path))
    contracts = read_jsonl_gz(args.output_contract_gz)
    if len(profiles) != 1000 or len(contracts) != 1000:
        raise SystemExit(f"expected 1000 profiles/contracts, got {len(profiles)}/{len(contracts)}")

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
