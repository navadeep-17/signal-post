#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs  # noqa: E402
from norway_company_agent.h1g_hyphenated_no_recall import hyphenated_no_candidate  # noqa: E402

PR137_GATE_A_SHA256 = "f2177abd0bd0d6202f9fe47fd00b8def06b21c01fdf4c864c1f3b68f80b160d5"

M10_POSITIVE_CANARIES = {"927097532", "979943377", "999096298"}
M12_RESEARCHED_ORGS = {
    "828829092", "870418892", "896488562", "898321622",
    "911546221", "914384729", "936455298", "976533194",
    "979436661", "988936987", "992784229", "996405524",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _orgs(rows: list[dict[str, Any]]) -> set[str]:
    result = {str(row.get("organisation_number") or "") for row in rows}
    if any(len(org) != 9 or not org.isdigit() for org in result):
        raise ValueError("all exclusion/selection organisation numbers must be 9 digits")
    return result


def build(
    profiles: list[dict[str, Any]],
    *,
    prior_search_orgs: set[str],
    target_count: int = 100,
    search_count: int = 20,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if target_count < 1 or search_count < 1 or search_count > target_count:
        raise ValueError("require 1 <= search_count <= target_count")

    excluded = set(prior_search_orgs) | M10_POSITIVE_CANARIES | M12_RESEARCHED_ORGS
    candidates: list[dict[str, Any]] = []
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        if len(org) != 9 or not org.isdigit() or org in excluded:
            continue
        if str(profile.get("website") or "").strip():
            continue
        if hyphenated_no_candidate(profile) is None:
            continue
        candidates.append(
            {
                "organisation_number": org,
                "name": str(profile.get("name") or ""),
                "municipality": str(profile.get("municipality") or ""),
                "registry_website_present": False,
                "baseline_h1g_candidate_available": True,
            }
        )

    candidates.sort(key=lambda row: row["organisation_number"])
    if len(candidates) < target_count:
        raise ValueError(
            f"only {len(candidates)} clean consumed H1g-eligible companies remain; "
            f"need {target_count}"
        )

    targets = candidates[:search_count]
    controls = candidates[search_count:target_count]
    selected = [*targets, *controls]

    manifest = [
        {
            "organisation_number": row["organisation_number"],
            "evaluation_split": "v9_m13_consumed_search_breadth",
            "sample_slice": (
                "m13_search_holdout"
                if index < search_count
                else "m13_control_unsearched"
            ),
        }
        for index, row in enumerate(selected)
    ]
    audit = [
        {
            **row,
            "bucket": (
                "m13_search_holdout"
                if index < search_count
                else "m13_control_unsearched"
            ),
            "previous_search_development": row["organisation_number"] in prior_search_orgs,
            "m10_positive_canary": row["organisation_number"] in M10_POSITIVE_CANARIES,
            "m12_researched": row["organisation_number"] in M12_RESEARCHED_ORGS,
        }
        for index, row in enumerate(selected)
    ]

    report = {
        "screen_type": "v9_m13_consumed_search_holdout_selection",
        "source_population_companies": len(profiles),
        "selected_companies": len(selected),
        "search_holdout_companies": len(targets),
        "control_companies": len(controls),
        "eligible_unresearched_population": len(candidates),
        "fresh_companies_used": 0,
        "prior_search_development_excluded": len(prior_search_orgs),
        "m10_positive_canaries_excluded": sorted(M10_POSITIVE_CANARIES),
        "m12_researched_orgs_excluded": sorted(M12_RESEARCHED_ORGS),
        "target_organisation_numbers": [row["organisation_number"] for row in targets],
        "selection_rule": [
            "start with the frozen already-consumed 1000-company population",
            "exclude all 20 PR #137 search Gate-A companies",
            "exclude all three M10 positive canaries",
            "exclude all twelve M12 externally researched development companies",
            "require no BRREG website in the frozen shared registry snapshot",
            "require a deterministic baseline H1g slot candidate before treatment",
            "sort remaining organisations by organisation number",
            f"first {search_count} become unresearched M13 search holdout targets",
            f"next {target_count - search_count} become untreated controls",
            "provider output never influences cohort membership",
        ],
    }
    if any(row["previous_search_development"] or row["m10_positive_canary"] or row["m12_researched"] for row in audit):
        raise AssertionError("researched organisation leaked into M13 holdout/control")
    return manifest, audit, report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-manifest", type=Path, required=True)
    p.add_argument("--bulk", type=Path, required=True)
    p.add_argument("--prior-search-manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--target-count", type=int, default=100)
    p.add_argument("--search-count", type=int, default=20)
    args = p.parse_args()

    if sha256(args.prior_search_manifest) != PR137_GATE_A_SHA256:
        raise ValueError("PR #137 prior-search Gate-A manifest SHA-256 mismatch")

    source = read_organisation_inputs(args.source_manifest)
    source_orgs = [row["organisation_number"] for row in source]
    if len(source_orgs) != 1000 or len(set(source_orgs)) != 1000:
        raise ValueError(f"expected frozen consumed 1000, got {len(source_orgs)}")

    prior_search = read_organisation_inputs(args.prior_search_manifest)
    if len(prior_search) != 20 or len(_orgs(prior_search)) != 20:
        raise ValueError("expected exact prior PR #137 Gate-A 20-company manifest")

    profiles, snapshot = profiles_from_bulk(args.bulk, source_orgs)
    manifest, audit, report = build(
        profiles,
        prior_search_orgs=_orgs(prior_search),
        target_count=args.target_count,
        search_count=args.search_count,
    )
    write_jsonl(args.output, manifest)
    write_jsonl(args.audit, audit)
    report.update(
        {
            "source_manifest_sha256": sha256(args.source_manifest),
            "prior_search_manifest_sha256": sha256(args.prior_search_manifest),
            "target_manifest_sha256": sha256(args.output),
            "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
            "registry_snapshot_missing_count": snapshot.get("missing_count"),
        }
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
