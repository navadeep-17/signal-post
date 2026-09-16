#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.external_footprint import validate_observation
from norway_company_agent.registry_workforce import registry_workforce_observations
from norway_company_agent.workforce_contract import project_workforce_observations


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate zero-request BRREG registry workforce observations.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--expected-count", type=int, default=300)
    args = parser.parse_args()

    profiles = read_jsonl(Path(args.profiles))
    if len(profiles) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} profiles, got {len(profiles)}")

    audit = []
    validation_errors = []
    candidate_companies = 0
    contract_projection_errors = []
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        observations = registry_workforce_observations(profile)
        if observations:
            candidate_companies += 1
        for observation in observations:
            errors = validate_observation(observation)
            validation_errors.extend(
                {"organisation_number": org, "observation_id": observation.get("id"), "error": error}
                for error in errors
            )
            contract = {
                "organisation_number": org,
                "claims": [],
                "evidence": [],
            }
            projected = project_workforce_observations(contract, {**profile, "external_observations": observations})
            claims = [claim for claim in projected["claims"] if claim.get("field") == "external.workforce_snapshot"]
            if len(claims) != 1 or len(projected["evidence"]) != 1:
                contract_projection_errors.append(
                    {"organisation_number": org, "error": "workforce projection did not yield exactly one claim/evidence pair"}
                )
            audit.append(
                {
                    "organisation_number": org,
                    "name": profile.get("name"),
                    "employees": (observation.get("metrics") or {}).get("employees"),
                    "source_url": observation.get("source_url"),
                    "retrieved_at": observation.get("retrieved_at"),
                    "content_sha256": observation.get("content_sha256"),
                    "observation_id": observation.get("id"),
                }
            )

    report = {
        "experiment": "h2e_registry_workforce_v1",
        "profiles": len(profiles),
        "candidate_companies": candidate_companies,
        "company_coverage": round(candidate_companies / len(profiles), 6) if profiles else 0.0,
        "added_logical_requests": 0,
        "added_conservative_challenge_request_charge": 0,
        "third_party_cost_usd": 0.0,
        "validation_errors": validation_errors,
        "contract_projection_errors": contract_projection_errors,
        "claim_boundary": "Exact BRREG legal-entity employee count already fetched by production; no FTE, group, trend, or inferred workforce claim.",
        "passed": not validation_errors and not contract_projection_errors,
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.audit).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in audit), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
