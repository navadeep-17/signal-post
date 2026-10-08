#!/usr/bin/env python3
"""Read-only aggregate source-reach audit over prior M19/M20 GitHub artifact ZIPs.

No company HTTP traffic; no new sampling, candidate promotion, or model calls.
The three ZIP SHA-256 values and frozen cohort manifests are pinned below.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import zipfile
from pathlib import Path

SOURCES = (
    ("M19 Gate A", "m19_a", 11505218381,
     "45a9fb18b6c8e05e7f7d90106de223fc31cf71e50ba6306d9c72c95118503bc9",
     "frozen/m19-transfer-gate-a-100.jsonl",
     "4a9ff2027bf1c5d17beb48742d717cfab2b143f8ed7abf892dbc3056cea3c7e6"),
    ("M19 Gate B", "m19_b", 11525046472,
     "7439ace3eabb7ad3f951abb91396dac23e26cf04bd1e1d25f12ada625ceb4df6",
     "frozen/m19-transfer-gate-b-100.jsonl",
     "3fc5fdd69ee4c650dc3e6daa32cde3bf5cb14022db9dddb8c2efa5acaae4a82a"),
    ("M20 Gate A", "m20_a", 11525304908,
     "3d00b7fc2399fb7bbe6dd2d438ad689313dccd1850cc429b002d499fcb26e05a",
     "frozen/m20-transfer-gate-a-100.jsonl",
     "8cc4e45c238cc446bf9d88e1f5268c33c9779a4b2a57bd60552c156fa4a9d6d2"),
)
FIELDS = (
    "official_website", "external.profile_handle", "external.contact_email",
    "external.careers_page", "external.job_posting", "external.company_update",
    "external.workforce_snapshot", "official.support_award",
)

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def json_lines(data: bytes) -> list[dict]:
    return [json.loads(line) for line in data.splitlines() if line.strip()]

def audit_zip(path: Path, spec: tuple) -> tuple[dict, set[str]]:
    label, _, artifact_id, artifact_digest, manifest_path, manifest_digest = spec
    assert sha256(path.read_bytes()) == artifact_digest, f"wrong artifact ZIP: {label}"
    with zipfile.ZipFile(path) as z:
        assert sha256(z.read(manifest_path)) == manifest_digest, label
        manifest = json_lines(z.read(manifest_path))
        report = json.loads(z.read("baseline-out/report.json"))
        outputs = json_lines(z.read("baseline-out/output.jsonl"))
        profiles = json_lines(z.read("baseline-out/work/profiles.jsonl"))
    ids = {str(p["organisation_number"]) for p in profiles}
    assert len(manifest) == len(profiles) == len(outputs) == len(ids) == 100, label
    assert ids == {str(x["organisation_number"]) for x in manifest}, label
    assert ids == {str(x["organisation_number"]) for x in outputs}, label
    by_field = {k: set() for k in FIELDS}
    for obj in outputs:
        for c in obj.get("claims", []):
            if c.get("availability") == "available" and c.get("field") in by_field:
                by_field[c["field"]].add(str(obj["organisation_number"]))
    sd, es, budget = report["site_discovery"], report["external_signals"], report["request_budget"]
    assert report["passed"] is True, label
    assert len(by_field["official_website"]) == sd["profiles_with_verified_site"], label
    assert len(by_field["external.profile_handle"]) == es["companies_with_profile_handles"], label
    assert len(by_field["external.contact_email"]) == es["companies_with_contact_emails"], label
    assert len(by_field["external.workforce_snapshot"]) == es["companies_with_workforce"], label
    assert sum(sd["selected_sources"].values()) == 100, label
    assert budget["observed_conservative_challenge_request_charge"] <= 2000, label
    assert budget["theoretical_challenge_request_charge_ceiling"] == 2000, label
    assert report["runtime"]["wall_runtime_seconds"] <= 2400, label
    assert report["source_policy"]["third_party_cost_usd"] == 0.0, label
    assert report["source_policy"]["search_api_requests"] == 0, label
    status = collections.Counter(
        ((p.get("evidence") or {}).get("website") or {}).get("status", "none")
        for p in profiles
    )
    return ({
        "cohort": label, "companies": 100, "artifact_id": artifact_id,
        "artifact_zip_sha256": artifact_digest, "frozen_manifest_sha256": manifest_digest,
        "verified_website_companies": sd["profiles_with_verified_site"],
        "published_company_counts": {k: len(v) for k, v in by_field.items()},
        "website_source_selection": sd["selected_sources"],
        "website_evidence_status_counts": dict(status),
        "accessible_candidates_not_published": status["available"] - len(by_field["official_website"]),
        "wikidata_candidates": sd["wikidata"]["candidate_count"],
        "h1g_attempts": sd["h1g"]["attempted"],
        "h1g_verified": sd["h1g"]["verified"],
        "observed_conservative_request_charge": budget["observed_conservative_challenge_request_charge"],
        "theoretical_conservative_request_ceiling": budget["theoretical_challenge_request_charge_ceiling"],
        "wall_runtime_seconds": report["runtime"]["wall_runtime_seconds"],
        "search_api_requests": report["source_policy"]["search_api_requests"],
        "third_party_cost_usd": report["source_policy"]["third_party_cost_usd"],
    }, ids)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for _, dest, *_ in SOURCES:
        parser.add_argument("--" + dest.replace("_", "-"), required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    a = parser.parse_args()
    result = {"screen": "M21_read_only_300_company_source_reach_diagnostic", "cohorts": []}
    all_ids: set[str] = set()
    for spec in SOURCES:
        record, ids = audit_zip(getattr(a, spec[1]), spec)
        assert not (ids & all_ids), f"cohorts overlap: {spec[0]}"
        all_ids.update(ids)
        result["cohorts"].append(record)
    assert len(all_ids) == 300
    keys = ("companies", "verified_website_companies", "accessible_candidates_not_published",
            "wikidata_candidates", "h1g_attempts", "h1g_verified", "observed_conservative_request_charge",
            "theoretical_conservative_request_ceiling", "wall_runtime_seconds", "search_api_requests",
            "third_party_cost_usd")
    result["totals"] = {k: sum(c[k] for c in result["cohorts"]) for k in keys}
    result["totals"]["published_company_counts"] = {
        k: sum(c["published_company_counts"][k] for c in result["cohorts"]) for k in FIELDS
    }
    for key in ("website_source_selection", "website_evidence_status_counts"):
        result["totals"][key] = dict(sum((collections.Counter(c[key]) for c in result["cohorts"]), collections.Counter()))
    result["cohort_disjoint"] = True
    result["fresh_companies_used"] = 0
    result["qualified_website_share_of_300"] = round(result["totals"]["verified_website_companies"] / 300, 4)
    result["social_share_given_qualified_site"] = round(
        result["totals"]["published_company_counts"]["external.profile_handle"] /
        result["totals"]["verified_website_companies"], 4)
    result["email_share_given_qualified_site"] = round(
        result["totals"]["published_company_counts"]["external.contact_email"] /
        result["totals"]["verified_website_companies"], 4)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("AUDIT PASS: 300 disjoint previously consumed companies, 0 fresh and 0 network calls")
    print(json.dumps(result["totals"], indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
