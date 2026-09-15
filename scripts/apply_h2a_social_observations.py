#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_social import attach_company_site_social_observations  # noqa: E402
from norway_company_agent.external_contract import project_profile_handle_observations  # noqa: E402
from norway_company_agent.external_footprint import validate_observation  # noqa: E402
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply zero-network H2a company-page social observations to a completed Signalpost run.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--contracts", required=True)
    parser.add_argument("--base-report", required=True)
    parser.add_argument("--profiles-output", required=True)
    parser.add_argument("--contracts-output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    profiles = read_jsonl(args.profiles)
    contracts = read_jsonl(args.contracts)
    base_report = json.loads(Path(args.base_report).read_text(encoding="utf-8"))

    contract_by_org = {str(item.get("organisation_number")): item for item in contracts}
    if len(contract_by_org) != len(contracts):
        raise SystemExit("Base contracts contain duplicate organisation numbers")

    output_profiles: list[dict[str, Any]] = []
    output_contracts: list[dict[str, Any]] = []
    observation_errors: list[dict[str, Any]] = []
    contract_errors: list[dict[str, Any]] = []
    platforms: Counter[str] = Counter()
    companies_with_handles = 0
    observation_count = 0

    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        base_contract = contract_by_org.get(org)
        if not base_contract:
            raise SystemExit(f"No base contract for {org}")

        attach_company_site_social_observations(profile)
        h2a_observations = [
            item
            for item in (profile.get("external_observations") or [])
            if isinstance(item, dict) and item.get("signal_type") == "profile_handle"
        ]
        for item in h2a_observations:
            reasons = validate_observation(item)
            if reasons:
                observation_errors.append({"organisation_number": org, "observation_id": item.get("id"), "errors": reasons})
            platforms[str(item.get("platform") or "unknown")] += 1
        if h2a_observations:
            companies_with_handles += 1
            observation_count += len(h2a_observations)

        projected = project_profile_handle_observations(base_contract, profile)
        for error in validate_contract_object(projected):
            contract_errors.append({"organisation_number": org, "error": error})
        output_profiles.append(profile)
        output_contracts.append(projected)

    if len(output_profiles) != len(profiles) or len(output_contracts) != len(contracts):
        raise SystemExit("H2a changed terminal object cardinality")

    base_budget = base_report.get("request_budget") or {}
    report = {
        "input_profiles": len(profiles),
        "input_contracts": len(contracts),
        "output_profiles": len(output_profiles),
        "output_contracts": len(output_contracts),
        "companies_with_profile_handles": companies_with_handles,
        "profile_handle_observations": observation_count,
        "platform_counts": dict(sorted(platforms.items())),
        "observation_errors": observation_errors,
        "contract_errors": contract_errors,
        "network_requests_added": 0,
        "third_party_cost_usd_added": 0.0,
        "base_observed_logical_requests": int(base_budget.get("observed_logical_requests") or 0),
        "base_observed_conservative_requests": int(base_budget.get("observed_conservative_challenge_request_charge") or 0),
        "post_h2a_observed_logical_requests": int(base_budget.get("observed_logical_requests") or 0),
        "post_h2a_observed_conservative_requests": int(base_budget.get("observed_conservative_challenge_request_charge") or 0),
    }
    report["passed"] = (
        not observation_errors
        and not contract_errors
        and len(output_profiles) == len(profiles)
        and len(output_contracts) == len(contracts)
    )

    write_jsonl(args.profiles_output, output_profiles)
    write_jsonl(args.contracts_output, output_contracts)
    target = Path(args.report)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
