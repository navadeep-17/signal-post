#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_profiles(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("profiles.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"{path}: expected JSON object")
                rows.append(value)
    return rows


def exact_verified(profile: dict[str, Any]) -> bool:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") if isinstance(website.get("value"), dict) else {}
    assessment = value.get("identity_assessment") if isinstance(value.get("identity_assessment"), dict) else {}
    return bool(
        website.get("status") == "available"
        and assessment.get("publishable")
        and str(value.get("final_url") or website.get("source_url") or "").startswith(("http://", "https://"))
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a consumed-only M6 target from companies with archived exact verified sites."
    )
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--target-count", type=int, default=100)
    args = parser.parse_args()

    profiles = read_profiles(args.profiles_dir)
    if len(profiles) != 1000:
        raise ValueError(f"expected frozen consumed 1000 profiles, got {len(profiles)}")
    if len({str(row.get("organisation_number") or "") for row in profiles}) != len(profiles):
        raise ValueError("archived profiles contain duplicate organisation numbers")

    eligible = sorted(
        (
            str(row.get("organisation_number") or "")
            for row in profiles
            if exact_verified(row)
        )
    )
    if len(eligible) < args.target_count:
        raise ValueError(
            f"only {len(eligible)} exact-verified consumed companies; need {args.target_count}"
        )
    selected = eligible[: args.target_count]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps({"organisation_number": org}) + "\n" for org in selected),
        encoding="utf-8",
    )
    report = {
        "screen_type": "v9_m6_consumed_exact_site_target",
        "source_profiles": len(profiles),
        "eligible_exact_verified_site_companies": len(eligible),
        "selected_companies": len(selected),
        "selection": "lexicographically first organisation numbers from frozen consumed exact-site population",
        "fresh_companies_used": 0,
        "organisation_numbers_retained_in_report": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
