#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs
from norway_company_agent.h1g_hyphenated_no_recall import hyphenated_no_candidate

PR137_GATE_A_SHA256 = "f2177abd0bd0d6202f9fe47fd00b8def06b21c01fdf4c864c1f3b68f80b160d5"
EXPECTED_M13B_TARGET_SHA256 = "eddd8ed807f1116a3fd2d780b21796d546717fd3a27ee7983d8a89d14d891cbe"

M10_POSITIVE_CANARIES = {"927097532", "979943377", "999096298"}
M12_RESEARCHED_ORGS = {
    "828829092", "870418892", "896488562", "898321622",
    "911546221", "914384729", "936455298", "976533194",
    "979436661", "988936987", "992784229", "996405524",
}
BUILDERR_PUBLIC_PRACTICE_ORGS = {
    "811413682", "811730912", "883971752", "923609016",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def orgs(path: Path, *, expected: int) -> set[str]:
    rows = read_organisation_inputs(path)
    values = {str(row.get("organisation_number") or "") for row in rows}
    if len(rows) != expected or len(values) != expected:
        raise ValueError(f"{path}: expected {expected} unique organisations")
    if any(len(org) != 9 or not org.isdigit() for org in values):
        raise ValueError(f"{path}: invalid organisation number")
    return values


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-manifest", type=Path, required=True)
    p.add_argument("--bulk", type=Path, required=True)
    p.add_argument("--prior-search-manifest", type=Path, required=True)
    p.add_argument("--prior-m13-manifest", type=Path, required=True)
    p.add_argument("--prior-m14-manifest", type=Path, required=True)
    p.add_argument("--prior-m14b-manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()

    if sha256(args.prior_search_manifest) != PR137_GATE_A_SHA256:
        raise ValueError("PR #137 prior-search manifest hash mismatch")

    source = read_organisation_inputs(args.source_manifest)
    source_orgs = [str(row["organisation_number"]) for row in source]
    if len(source_orgs) != 1000 or len(set(source_orgs)) != 1000:
        raise ValueError("expected exact frozen consumed 1000")

    prior_search = orgs(args.prior_search_manifest, expected=20)
    prior_m13 = orgs(args.prior_m13_manifest, expected=100)
    prior_m14 = orgs(args.prior_m14_manifest, expected=100)
    prior_m14b = orgs(args.prior_m14b_manifest, expected=100)

    outer_excluded = (
        prior_m13
        | prior_m14
        | prior_m14b
        | BUILDERR_PUBLIC_PRACTICE_ORGS
    )
    inner_excluded = prior_search | M10_POSITIVE_CANARIES | M12_RESEARCHED_ORGS

    profiles, _snapshot = profiles_from_bulk(args.bulk, source_orgs)
    candidates: list[dict[str, Any]] = []
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        if org in outer_excluded or org in inner_excluded:
            continue
        if len(org) != 9 or not org.isdigit():
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
            }
        )

    candidates.sort(key=lambda row: row["organisation_number"])
    if len(candidates) < 100:
        raise ValueError(f"only {len(candidates)} M13b-eligible candidates remain")

    selected = candidates[:100]
    manifest = [
        {
            "organisation_number": row["organisation_number"],
            "evaluation_split": "v9_m13b_consumed_search_replacement",
            "sample_slice": (
                "m13b_search_holdout" if index < 20 else "m13b_control_unsearched"
            ),
        }
        for index, row in enumerate(selected)
    ]
    write_jsonl(args.output, manifest)

    digest = sha256(args.output)
    if digest != EXPECTED_M13B_TARGET_SHA256:
        raise ValueError(
            f"M13b reconstruction hash mismatch: {digest} != {EXPECTED_M13B_TARGET_SHA256}"
        )
    print(json.dumps({
        "reconstructed_companies": len(manifest),
        "target_manifest_sha256": digest,
        "matches_frozen_m13b": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
