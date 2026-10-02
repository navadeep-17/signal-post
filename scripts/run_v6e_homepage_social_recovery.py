#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.homepage_social_recovery import (  # noqa: E402
    STRATEGY,
    homepage_social_recovery_observations,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="V6e zero-network retained-homepage social recovery")
    parser.add_argument("--input-profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    started = time.monotonic()
    profiles = _read_jsonl(Path(args.input_profiles))
    observations: list[dict[str, Any]] = []
    exact_sites = 0
    profiles_with_multiple_pages = 0

    for profile in profiles:
        website = ((profile.get("evidence") or {}).get("website") or {})
        value = website.get("value") or {}
        identity = value.get("identity_assessment") or {}
        if website.get("status") == "available" and identity.get("publishable"):
            exact_sites += 1
        if len([p for p in (value.get("pages") or []) if isinstance(p, dict)]) > 1:
            profiles_with_multiple_pages += 1
        observations.extend(homepage_social_recovery_observations(profile))

    observations.sort(key=lambda row: (row["organisation_number"], row["platform"], row["profile_url"], row["id"]))
    _write_jsonl(Path(args.output), observations)

    companies = {row["organisation_number"] for row in observations}
    platform_counts = Counter(str(row.get("platform") or "") for row in observations)
    declaration_counts = Counter(str((row.get("metrics") or {}).get("declaration_mode") or "") for row in observations)
    report = {
        "experiment": "V6e zero-network homepage social recovery",
        "strategy": STRATEGY,
        "input_profiles": len(profiles),
        "exact_verified_sites": exact_sites,
        "profiles_with_multiple_retained_pages": profiles_with_multiple_pages,
        "net_new_observations": len(observations),
        "companies_with_net_new_social_profile": len(companies),
        "platform_counts": dict(sorted(platform_counts.items())),
        "declaration_mode_counts": dict(sorted(declaration_counts.items())),
        "logical_requests_added": 0,
        "conservative_request_charge_added": 0,
        "third_party_api_cost_usd": 0.0,
        "wrong_company_publications": 0,
        "publication_status": "experiment_only_manual_audit_required",
        "claim_scope": "Retained exact company homepage declarations only; no social-platform content or activity fetched.",
        "wall_runtime_seconds": round(time.monotonic() - started, 3),
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
