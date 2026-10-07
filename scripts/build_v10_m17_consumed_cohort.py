#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs
from norway_company_agent.h1g_hyphenated_no_recall import hyphenated_no_candidate

M13B_TARGET_MANIFEST_SHA256 = "eddd8ed807f1116a3fd2d780b21796d546717fd3a27ee7983d8a89d14d891cbe"

KNOWN_RESEARCHED_ORGS = {
    "927097532", "979943377", "999096298",
    "828829092", "870418892", "896488562", "898321622",
    "911546221", "914384729", "936455298", "976533194",
    "979436661", "988936987", "992784229", "996405524",
    "811413682", "811730912", "883971752", "923609016",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ).encode("utf-8")


def _read_orgs(path: Path) -> set[str]:
    rows = read_organisation_inputs(path)
    values = {str(row["organisation_number"]) for row in rows}
    if any(len(org) != 9 or not org.isdigit() for org in values):
        raise ValueError(f"{path}: invalid organisation number")
    return values


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_jsonl_bytes(rows))


def _reconstruct_m13b(
    profiles: list[dict[str, Any]],
    *,
    base_excluded: set[str],
) -> tuple[set[str], str]:
    eligible: list[str] = []
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        if org in base_excluded:
            continue
        if str(profile.get("website") or "").strip():
            continue
        if hyphenated_no_candidate(profile) is None:
            continue
        eligible.append(org)
    eligible.sort()
    if len(eligible) < 100:
        raise ValueError(f"cannot reconstruct M13b: only {len(eligible)} eligible")

    selected = eligible[:100]
    manifest = [
        {
            "organisation_number": org,
            "evaluation_split": "v9_m13b_consumed_search_replacement",
            "sample_slice": (
                "m13b_search_holdout" if index < 20 else "m13b_control_unsearched"
            ),
        }
        for index, org in enumerate(selected)
    ]
    digest = hashlib.sha256(_jsonl_bytes(manifest)).hexdigest()
    if digest != M13B_TARGET_MANIFEST_SHA256:
        raise ValueError(
            f"reconstructed M13b SHA mismatch: {digest} != {M13B_TARGET_MANIFEST_SHA256}"
        )
    return set(selected), digest


def _address(profile: dict[str, Any]) -> dict[str, Any]:
    for key in ("business_address", "postal_address"):
        value = profile.get(key)
        if isinstance(value, dict) and value:
            return value
    raw = ((profile.get("evidence") or {}).get("registry") or {}).get("value")
    if isinstance(raw, dict):
        for key in ("forretningsadresse", "postadresse"):
            value = raw.get(key)
            if isinstance(value, dict) and value:
                return value
    return {}


def _address_is_usable(profile: dict[str, Any]) -> bool:
    value = _address(profile)
    street = value.get("adresse")
    municipality = value.get("kommune") or profile.get("municipality")
    postcode = value.get("postnummer")
    return bool(street and (municipality or postcode))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-manifest", type=Path, required=True)
    p.add_argument("--bulk", type=Path, required=True)
    p.add_argument("--m13b-base-exclude", action="append", type=Path, default=[])
    p.add_argument("--extra-exclude", action="append", type=Path, default=[])
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--count", type=int, default=20)
    args = p.parse_args()

    source = read_organisation_inputs(args.source_manifest)
    source_orgs = [str(row["organisation_number"]) for row in source]
    if len(source_orgs) != 1000 or len(set(source_orgs)) != 1000:
        raise ValueError("M17 requires the exact frozen consumed 1000-company source")

    base_excluded = set(KNOWN_RESEARCHED_ORGS)
    exclusion_hashes: list[dict[str, Any]] = []
    for path in args.m13b_base_exclude:
        values = _read_orgs(path)
        base_excluded |= values
        exclusion_hashes.append({
            "role": "m13b_base_exclude",
            "path": path.name,
            "sha256": _sha256(path),
            "companies": len(values),
        })

    profiles, snapshot = profiles_from_bulk(args.bulk, source_orgs)
    reconstructed_m13b, reconstructed_m13b_sha = _reconstruct_m13b(
        profiles,
        base_excluded=base_excluded,
    )

    excluded = set(base_excluded) | reconstructed_m13b
    for path in args.extra_exclude:
        values = _read_orgs(path)
        excluded |= values
        exclusion_hashes.append({
            "role": "extra_exclude",
            "path": path.name,
            "sha256": _sha256(path),
            "companies": len(values),
        })

    candidates: list[dict[str, Any]] = []
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        if org in excluded:
            continue
        if str(profile.get("website") or "").strip():
            continue
        if not _address_is_usable(profile):
            continue
        candidates.append({
            "organisation_number": org,
            "evaluation_split": "v10_m17_consumed_osm_site_screen",
            "sample_slice": "m17_osm_name_location_nomination",
        })

    candidates.sort(key=lambda row: row["organisation_number"])
    if len(candidates) < args.count:
        raise ValueError(f"only {len(candidates)} eligible M17 companies remain")

    selected = candidates[: args.count]
    _write_jsonl(args.output, selected)

    report = {
        "screen_type": "v10_m17_consumed_osm_site_nomination",
        "source_population_companies": len(source_orgs),
        "selected_companies": len(selected),
        "eligible_after_exclusions": len(candidates),
        "fresh_companies_used": 0,
        "known_researched_orgs_excluded": len(KNOWN_RESEARCHED_ORGS),
        "reconstructed_m13b_companies_excluded": len(reconstructed_m13b),
        "reconstructed_m13b_manifest_sha256": reconstructed_m13b_sha,
        "external_exclusion_manifests": exclusion_hashes,
        "source_manifest_sha256": _sha256(args.source_manifest),
        "target_manifest_sha256": _sha256(args.output),
        "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
        "registry_snapshot_missing_count": snapshot.get("missing_count"),
        "selection_rule": [
            "start with exact frozen already-consumed 1000-company population",
            "reconstruct and exclude frozen untouched M13b before selection",
            "exclude supplied prior experiment/search cohorts",
            "exclude known M10/M12 researched cases and Builderr public examples",
            "require no registry website",
            "require a usable public BRREG business/postal address",
            "sort by organisation number and take first requested count",
            "OSM/Nominatim output never influences cohort membership",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "screen_type": report["screen_type"],
        "selected_companies": report["selected_companies"],
        "eligible_after_exclusions": report["eligible_after_exclusions"],
        "fresh_companies_used": 0,
        "reconstructed_m13b_companies_excluded": 100,
        "target_manifest_sha256": report["target_manifest_sha256"],
        "registry_snapshot_sha256": report["registry_snapshot_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
