#!/usr/bin/env python3
"""M24 deterministic consumed-development cohort freeze; NO network operations.

Replays already-consumed M19 A/B and M20 A baseline artifacts. Excludes
registry-seeded and previously verified website cases, then selects 7/7/6
using SHA256 of a fixed label and public Norwegian organisation number.
This is an intentionally targeted *development* sample, never a holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

SALT = "signalpost-v10-m24-consumed-development-v1"
SOURCES = (
    ("m19_a", 7, 11505218381,
     "45a9fb18b6c8e05e7f7d90106de223fc31cf71e50ba6306d9c72c95118503bc9",
     "frozen/m19-transfer-gate-a-100.jsonl",
     "4a9ff2027bf1c5d17beb48742d717cfab2b143f8ed7abf892dbc3056cea3c7e6"),
    ("m19_b", 7, 11525046472,
     "7439ace3eabb7ad3f951abb91396dac23e26cf04bd1e1d25f12ada625ceb4df6",
     "frozen/m19-transfer-gate-b-100.jsonl",
     "3fc5fdd69ee4c650dc3e6daa32cde3bf5cb14022db9dddb8c2efa5acaae4a82a"),
    ("m20_a", 6, 11525304908,
     "3d00b7fc2399fb7bbe6dd2d438ad689313dccd1850cc429b002d499fcb26e05a",
     "frozen/m20-transfer-gate-a-100.jsonl",
     "8cc4e45c238cc446bf9d88e1f5268c33c9779a4b2a57bd60552c156fa4a9d6d2"),
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_jsonl(data: bytes) -> list[dict]:
    return [json.loads(line) for line in data.splitlines() if line.strip()]


def read_archive(path: Path, spec: tuple) -> tuple[list[str], dict, set[str]]:
    cohort, count, artifact_id, zip_sha, frozen_path, frozen_sha = spec
    assert digest(path.read_bytes()) == zip_sha, f"Wrong or altered ZIP: {cohort}"
    with zipfile.ZipFile(path) as archive:
        assert digest(archive.read(frozen_path)) == frozen_sha, cohort
        frozen = parse_jsonl(archive.read(frozen_path))
        profiles = parse_jsonl(archive.read("baseline-out/work/profiles.jsonl"))
        outputs = parse_jsonl(archive.read("baseline-out/output.jsonl"))
        report = json.loads(archive.read("baseline-out/report.json"))
    assert report["passed"] is True
    assert report["source_policy"]["search_api_requests"] == 0
    assert report["source_policy"]["third_party_cost_usd"] == 0
    assert report["request_budget"]["theoretical_challenge_request_charge_ceiling"] == 2000
    assert len(frozen) == len(profiles) == len(outputs) == 100
    ids = {str(row["organisation_number"]) for row in frozen}
    by_profile = {str(row["organisation_number"]): row for row in profiles}
    by_output = {str(row["organisation_number"]): row for row in outputs}
    assert len(ids) == len(by_profile) == len(by_output) == 100
    assert ids == set(by_profile) == set(by_output)
    has_verified = set()
    for org, row in by_output.items():
        if any(c.get("field") == "official_website" and
               c.get("availability") == "available" for c in row.get("claims", [])):
            has_verified.add(org)
    assert len(has_verified) == report["site_discovery"]["profiles_with_verified_site"]
    eligible = []
    for org, profile in by_profile.items():
        if org in has_verified or str(profile.get("website") or "").strip():
            continue
        if not str(profile.get("name") or "").strip() or not str(profile.get("municipality") or "").strip():
            continue
        eligible.append(org)
    eligible.sort(key=lambda org: (digest(f"{SALT}|{org}".encode()), org))
    assert len(eligible) >= count
    return eligible[:count], {
        "cohort": cohort, "artifact_id": artifact_id, "eligible_before_selection": len(eligible),
        "selected_count": count, "zip_sha256": zip_sha, "manifest_sha256": frozen_sha,
        "prior_verified_site_count": len(has_verified)
    }, ids


def freeze(paths: list[Path]) -> dict:
    assert len(paths) == len(SOURCES)
    results = []
    infos = []
    seen: set[str] = set()
    for spec, path in zip(SOURCES, paths):
        selected, info, original_ids = read_archive(path, spec)
        assert not seen.intersection(original_ids), "M21 archives are not disjoint"
        seen.update(original_ids)
        results.append((spec[0], selected))
        infos.append(info)
    assert len(seen) == 300
    selected_flat = [org for _, orgs in results for org in orgs]
    assert len(selected_flat) == len(set(selected_flat)) == 20
    return {
        "schema": "v10_m24_consumed_dev_20_v1",
        "qualified_v8_sha": "200f056a5a60cad23610a3958b6bec62dfb624a5",
        "type": "PRIOR_CONSUMED_ONLY_NOT_TRANSFER",
        "salt": SALT,
        "eligibility": "legal name and municipality present; no BRREG website seed; no available official_website claim",
        "selected_per_cohort": {cohort: orgs for cohort, orgs in results},
        "selected_list_sha256": digest("\n".join(selected_flat).encode()),
        "origin_artifacts": infos,
        "count": 20,
        "new_external_requests": 0,
        "fresh_companies_used": 0,
        "live_provider_authorized": False,
        "production_promotion_authorized": False
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for spec in SOURCES:
        parser.add_argument("--" + spec[0].replace("_", "-"), type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = freeze([getattr(args, spec[0]) for spec in SOURCES])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("M24 deterministic, no-network, already-consumed 20-company freeze: PASS")
    print(result["selected_list_sha256"])
    print([(x["cohort"], x["eligible_before_selection"], x["selected_count"])
           for x in result["origin_artifacts"]])


if __name__ == "__main__":
    main()
