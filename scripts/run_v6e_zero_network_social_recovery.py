#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.external_footprint import validate_observation  # noqa: E402
from norway_company_agent.zero_network_social_recovery import (  # noqa: E402
    recover_company_site_social_observations,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="V6e zero-network exact-homepage social recovery experiment")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--observations", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    profiles = read_jsonl(Path(args.profiles))
    recovered: list[dict[str, Any]] = []
    eligible_exact_sites = 0
    exact_sites_with_recovery = 0
    platform_counts: dict[str, int] = {}
    validation_errors: list[dict[str, str]] = []

    for profile in profiles:
        website = ((profile.get("evidence") or {}).get("website") or {})
        identity = ((website.get("value") or {}).get("identity_assessment") or {})
        if website.get("status") == "available" and identity.get("publishable"):
            eligible_exact_sites += 1
        rows = recover_company_site_social_observations(profile)
        if rows:
            exact_sites_with_recovery += 1
        for item in rows:
            for error in validate_observation(item):
                validation_errors.append(
                    {
                        "organisation_number": str(profile.get("organisation_number") or ""),
                        "observation_id": str(item.get("id") or ""),
                        "error": error,
                    }
                )
            recovered.append(item)
            platform = str(item.get("platform") or "unknown")
            platform_counts[platform] = platform_counts.get(platform, 0) + 1

    if validation_errors:
        raise SystemExit("V6e generated invalid observations: " + json.dumps(validation_errors[:10], ensure_ascii=False))

    write_jsonl(Path(args.observations), recovered)
    report = {
        "experiment": "V6e zero-network exact-homepage social recovery",
        "input_profiles": len(profiles),
        "eligible_exact_verified_sites": eligible_exact_sites,
        "exact_sites_with_net_new_socials": exact_sites_with_recovery,
        "net_new_social_observations": len(recovered),
        "net_new_social_companies": len({str(item.get("organisation_number") or "") for item in recovered}),
        "platform_counts": dict(sorted(platform_counts.items())),
        "logical_requests_added": 0,
        "conservative_request_charge_added": 0,
        "third_party_api_cost_usd": 0.0,
        "search_api_requests": 0,
        "validation_errors": validation_errors,
        "website_identity_created": 0,
        "publication_boundary": (
            "Existing exact V5 homepage URL/hash plus deterministic social-handle identity only; "
            "secondary pages and social-platform content cannot create evidence."
        ),
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
