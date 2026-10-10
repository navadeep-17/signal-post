#!/usr/bin/env python3
"""M39 NO-NETWORK SHA-pinned historical source-field inventory.

Read only three *already consumed* M19 A/B + M20 A ZIP artifacts provided by
the GitHub Actions runner. Reuses M24's archive content digests and original
20-company selection. Reports ONLY 20 + 300 aggregate integer counters,
NO company names, org IDs, emails, URLs or source text.

No provider requests, no website probes, no production integration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]

from freeze_v10_m24_consumed_dev import SOURCES,freeze,parse_jsonl
from run_v10_m26_consumed_pilot import EXPECTED_SHA,load_consumed_cohort
from norway_company_agent.v10_m39_offline_existing_evidence_inventory import aggregate_existing_signals


def run_inventory(archive_paths:list[Path],manifest_path:Path)->dict:
    if len(archive_paths)!=3:
        raise ValueError("Exactly three SHA-pinned consumed archives required")
    source=freeze(archive_paths)  # verifies all prior content, SHA, 300 unique
    if source["selected_list_sha256"]!=EXPECTED_SHA:
        raise ValueError("M39 prior-used development subset changed")
    frozen20=load_consumed_cohort(archive_paths,manifest_path)
    rows300=[]
    previous_site_claims=0
    for spec,path in zip(SOURCES,archive_paths):
        with ZipFile(path) as z:
            profiles=parse_jsonl(z.read("baseline-out/work/profiles.jsonl"))
            outputs=parse_jsonl(z.read("baseline-out/output.jsonl"))
        assert len(profiles)==len(outputs)==100
        rows300.extend(profiles)
        previous_site_claims+=sum(
            any(
                claim.get("field")=="official_website"
                and claim.get("availability")=="available"
                for claim in out.get("claims",[])
            )
            for out in outputs
        )
    assert len(rows300)==300
    assert len({str(p["organisation_number"]) for p in rows300})==300
    summary20=aggregate_existing_signals(frozen20)
    summary300=aggregate_existing_signals(rows300,allow_missing_identity_fields=True)
    assert summary20["profiles_inspected"]==20
    assert summary300["profiles_inspected"]==300
    assert 0<=previous_site_claims<=300
    assert summary20["verified_new_websites"]==summary300["verified_new_websites"]==0
    assert summary20["additional_external_http_requests"]==0
    return {
        "schema":"m39_archive_existing_evidence_aggregate_v1",
        "source":"THREE_ALREADY_CONSUMED_AND_SHA_PINNED_M19_M20_COHORTS",
        "original_sample_company_count":300,
        "original_output_sites_verified_before_this_audit":previous_site_claims,
        "frozen_missing_site_dev_20":summary20,
        "original_consumed_all_300":summary300,
        "website_ownership_newly_verified":0,
        "new_company_http_requests":0,
        "new_provider_http_requests":0,
        "production_modified":False,
    }


def main()->None:
    arg=argparse.ArgumentParser()
    arg.add_argument("--m19-a",type=Path,required=True)
    arg.add_argument("--m19-b",type=Path,required=True)
    arg.add_argument("--m20-a",type=Path,required=True)
    a=arg.parse_args()
    report=run_inventory(
        [a.m19_a,a.m19_b,a.m20_a],
        ROOT/"evaluation/v10_m24_consumed_dev_20.json",
    )
    # Safe by schema: only fixed counters, booleans, category labels.
    print(json.dumps(report,sort_keys=True))
    print("M39 PASS: prior-consumed source-field inventory only, no site or provider requests.")


if __name__=="__main__":
    try:
        main()
    except Exception:
        print("M39 historical source inventory failed its offline safety/integrity validation")
        raise SystemExit(1)
