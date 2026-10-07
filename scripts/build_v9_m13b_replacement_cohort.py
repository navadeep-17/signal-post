#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

BUILDERR_PUBLIC_PRACTICE_ORGS = {
    "811413682",  # ELOPAK ASA
    "811730912",  # MTM SKOGSERVICE AS
    "883971752",  # SUNNAAS SYKEHUS HF
    "923609016",  # EQUINOR ASA
}


def _load_m13_builder():
    path = ROOT / "scripts" / "build_v9_m13_consumed_search_cohort.py"
    spec = importlib.util.spec_from_file_location("m13_builder", path)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load frozen M13 cohort builder")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M13 = _load_m13_builder()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{path}: JSON object rows required")
    return rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def orgs(path: Path, *, expected_count: int) -> set[str]:
    rows = read_jsonl(path)
    values = {str(row.get("organisation_number") or "") for row in rows}
    if len(rows) != expected_count or len(values) != expected_count:
        raise ValueError(f"{path}: expected {expected_count} unique organisations")
    if any(len(org) != 9 or not org.isdigit() for org in values):
        raise ValueError(f"{path}: invalid organisation number")
    return values


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-manifest", type=Path, required=True)
    p.add_argument("--bulk", type=Path, required=True)
    p.add_argument("--prior-search-manifest", type=Path, required=True)
    p.add_argument("--prior-m13-manifest", type=Path, required=True)
    p.add_argument("--prior-m14-manifest", type=Path, required=True)
    p.add_argument("--prior-m14b-manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--target-count", type=int, default=100)
    p.add_argument("--search-count", type=int, default=20)
    args = p.parse_args()

    if sha256(args.prior_search_manifest) != M13.PR137_GATE_A_SHA256:
        raise ValueError("PR #137 prior-search Gate-A manifest SHA-256 mismatch")

    source = M13.read_organisation_inputs(args.source_manifest)
    source_orgs = [row["organisation_number"] for row in source]
    if len(source_orgs) != 1000 or len(set(source_orgs)) != 1000:
        raise ValueError("expected exact frozen consumed 1000")

    prior_search = orgs(args.prior_search_manifest, expected_count=20)
    prior_m13 = orgs(args.prior_m13_manifest, expected_count=100)
    prior_m14 = orgs(args.prior_m14_manifest, expected_count=100)
    prior_m14b = orgs(args.prior_m14b_manifest, expected_count=100)

    all_excluded = (
        prior_m13
        | prior_m14
        | prior_m14b
        | BUILDERR_PUBLIC_PRACTICE_ORGS
    )

    profiles, snapshot = M13.profiles_from_bulk(args.bulk, source_orgs)
    remaining = [
        profile
        for profile in profiles
        if str(profile.get("organisation_number") or "") not in all_excluded
    ]

    manifest, audit, report = M13.build(
        remaining,
        prior_search_orgs=prior_search,
        target_count=args.target_count,
        search_count=args.search_count,
    )

    selected = {str(row["organisation_number"]) for row in manifest}
    overlap = selected & all_excluded
    if overlap:
        raise AssertionError(f"replacement cohort overlaps researched/practice sets: {sorted(overlap)}")

    for row in manifest:
        row["evaluation_split"] = "v9_m13b_consumed_search_replacement"
        row["sample_slice"] = (
            "m13b_search_holdout"
            if row["sample_slice"] == "m13_search_holdout"
            else "m13b_control_unsearched"
        )
    for row in audit:
        row["bucket"] = (
            "m13b_search_holdout"
            if row["bucket"] == "m13_search_holdout"
            else "m13b_control_unsearched"
        )
        row["prior_m13_cohort"] = row["organisation_number"] in prior_m13
        row["prior_m14_cohort"] = row["organisation_number"] in prior_m14
        row["prior_m14b_cohort"] = row["organisation_number"] in prior_m14b
        row["builderr_public_practice"] = row["organisation_number"] in BUILDERR_PUBLIC_PRACTICE_ORGS

    M13.write_jsonl(args.output, manifest)
    M13.write_jsonl(args.audit, audit)

    report.update(
        {
            "screen_type": "v9_m13b_consumed_search_replacement_holdout",
            "source_population_companies": 1000,
            "prior_m13_companies_excluded": 100,
            "prior_m14_companies_excluded": 100,
            "prior_m14b_companies_excluded": 100,
            "builderr_public_practice_orgs_excluded": sorted(BUILDERR_PUBLIC_PRACTICE_ORGS),
            "prior_m13_manifest_sha256": sha256(args.prior_m13_manifest),
            "prior_m14_manifest_sha256": sha256(args.prior_m14_manifest),
            "prior_m14b_manifest_sha256": sha256(args.prior_m14b_manifest),
            "replacement_disjoint_from_all_prior_experiment_cohorts": True,
            "target_manifest_sha256": sha256(args.output),
            "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
            "registry_snapshot_missing_count": snapshot.get("missing_count"),
        }
    )
    report["target_organisation_numbers"] = [
        str(row["organisation_number"])
        for row in manifest[: args.search_count]
    ]
    report["selection_rule"] = [
        "start with frozen already-consumed 1000-company population",
        "exclude PR #137 search-development 20 via frozen M13 builder",
        "exclude M10 positive canaries and M12 researched organisations via frozen M13 builder",
        "exclude entire original M13 100-company cohort after manual web research contaminated its holdout",
        "exclude entire M14 and M14b 100-company cohorts",
        "exclude Builderr public practice examples",
        "require no BRREG website in frozen shared registry snapshot",
        "require deterministic baseline H1g slot candidate before treatment",
        "sort remaining organisations by organisation number",
        f"first {args.search_count} become untouched M13b provider-search holdout",
        f"next {args.target_count - args.search_count} become untreated controls",
        "provider/search output never influences cohort membership",
    ]

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
