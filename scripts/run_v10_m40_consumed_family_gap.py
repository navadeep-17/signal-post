#!/usr/bin/env python3
"""M40 source-family gap replay of 300 previous V8 company outcomes, no network.

Accept EXACT original M19-A/M19-B/M20-A artifacts, verify original archived
ZIP SHA-256 and frozen per-group cohort SHA-256, baseline contract statuses,
company set/count and report success. Print only aggregate family counts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from norway_company_agent.v10_m40_offline_family_reach import score_evidence_family_reach

SOURCES=(
    ("m19_a","45a9fb18b6c8e05e7f7d90106de223fc31cf71e50ba6306d9c72c95118503bc9",
     "frozen/m19-transfer-gate-a-100.jsonl","4a9ff2027bf1c5d17beb48742d717cfab2b143f8ed7abf892dbc3056cea3c7e6"),
    ("m19_b","7439ace3eabb7ad3f951abb91396dac23e26cf04bd1e1d25f12ada625ceb4df6",
     "frozen/m19-transfer-gate-b-100.jsonl","3fc5fdd69ee4c650dc3e6daa32cde3bf5cb14022db9dddb8c2efa5acaae4a82a"),
    ("m20_a","3d00b7fc2399fb7bbe6dd2d438ad689313dccd1850cc429b002d499fcb26e05a",
     "frozen/m20-transfer-gate-a-100.jsonl","8cc4e45c238cc446bf9d88e1f5268c33c9779a4b2a57bd60552c156fa4a9d6d2"),
)

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _rows(data:bytes)->list[dict]:
    return [json.loads(line) for line in data.splitlines() if line.strip()]

def audit_pinned_archives(files:list[Path])->dict:
    if len(files)!=len(SOURCES):
        raise ValueError("Only exact original three already-consumed archives are allowed")
    all_contracts=[]
    all_profiles=[]
    observed_request_charge=0
    for file, spec in zip(files,SOURCES):
        name,zip_sha,frozen_name,frozen_sha=spec
        if _sha(file.read_bytes())!=zip_sha:
            raise ValueError("Archived historical ZIP checksum mismatch")
        with ZipFile(file) as z:
            if _sha(z.read(frozen_name))!=frozen_sha:
                raise ValueError("Frozen validation manifest checksum mismatch")
            frozen=_rows(z.read(frozen_name))
            profiles=_rows(z.read("baseline-out/work/profiles.jsonl"))
            output=_rows(z.read("baseline-out/output.jsonl"))
            report=json.loads(z.read("baseline-out/report.json"))
        if len(frozen)!=len(profiles)!=len(output):
            raise ValueError("Archives have incorrect company counts")
        if len(frozen)!=100 or len(profiles)!=100 or len(output)!=100:
            raise ValueError("Expected exactly 100 historical results per source")
        if report.get("passed") is not True:
            raise ValueError("Archived V8 baseline report not qualified")
        if report.get("source_policy",{}).get("search_api_requests")!=0:
            raise ValueError("Unexpected search source in archived V8")
        if report.get("source_policy",{}).get("third_party_cost_usd")!=0:
            raise ValueError("Historical source was not zero spend")
        if report.get("request_budget",{}).get("theoretical_challenge_request_charge_ceiling")!=2000:
            raise ValueError("Unexpected historical 100-company request theorem")
        ids=[str(p.get("organisation_number") or "") for p in profiles]
        if len(set(ids))!=100:
            raise ValueError("Duplicate companies within prior cohort")
        output_ids=[str(o.get("organisation_number") or "") for o in output]
        frozen_ids=[str(o.get("organisation_number") or "") for o in frozen]
        if set(ids)!=set(output_ids) or set(ids)!=set(frozen_ids):
            raise ValueError("Historical output cohort does not match frozen evidence")
        all_profiles.extend(profiles)
        all_contracts.extend(output)
    if len({str(x["organisation_number"]) for x in all_profiles})!=300:
        raise ValueError("Historical 300 cohort overlap")
    result=score_evidence_family_reach(all_contracts,all_profiles)
    assert result["companies"]==300 and result["new_verified_coverage"]==0
    return result

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    for name,*_ in SOURCES:
        p.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    args=p.parse_args()
    paths=[getattr(args,name) for name,*_ in SOURCES]
    result=audit_pinned_archives(paths)
    print(json.dumps(result,sort_keys=True))
    print("M40 archived family gap audit PASS: 300 exact companies, zero new external requests.")

if __name__=="__main__":
    try:
        main()
    except Exception:
        # Don't inadvertently print source records, company IDs or external URLs.
        print("M40 pinned archived evidence gate failed closed; no source details disclosed")
        raise SystemExit(1)
