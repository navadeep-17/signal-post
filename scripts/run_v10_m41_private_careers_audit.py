#!/usr/bin/env python3
"""M41 private, read-only provenance/contract audit of ONE M40 careers candidate.

All source records stay inside this runner's memory. No name, website, orgnr,
hash, claim spans, or company row is printed, uploaded, or returned in output.
No provider/company requests. Frozen V8/M40 parents are never modified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]

from run_v10_m40_consumed_family_gap import SOURCES,_sha,_rows,audit_pinned_archives
from norway_company_agent.careers_contract import project_careers_page_claims
from norway_company_agent.v10_m41_private_careers_audit import (
    audit_one_archived_careers_candidate,
)

def _careers_present(row:dict)->bool:
    return any(isinstance(x,dict) and x.get("field")=="external.careers_page"
               and x.get("availability")=="available"
               for x in (row.get("claims") or []))

def audit_frozen_m41_archives(paths:list[Path])->dict:
    original=audit_pinned_archives(paths)  # SHA-pins every historical source
    assert original["companies"]==300
    original_family_count=original["company_counts_by_typed_family"]["company_careers_link"]
    assert original_family_count==5, "Unexpected archived careers source baseline"

    audited=[]
    seen=set()
    baseline_contracts=0
    extra_existing_careers_urls=0
    for path,(group,digest,manifest,man_sha) in zip(paths,SOURCES):
        with ZipFile(path) as z:
            profiles=_rows(z.read("baseline-out/work/profiles.jsonl"))
            contracts=_rows(z.read("baseline-out/output.jsonl"))
        by_profile={p["organisation_number"]:p for p in profiles}
        assert len(by_profile)==100
        for row in contracts:
            org=row["organisation_number"]
            if org in seen or org not in by_profile:
                raise ValueError("Unmatched or duplicate frozen source record")
            seen.add(org)
            p=by_profile[org]
            is_old=_careers_present(row)
            baseline_contracts+=int(is_old)
            proposed=project_careers_page_claims(row,p)
            is_new=_careers_present(proposed)
            if not is_old and is_new:
                audited.append(audit_one_archived_careers_candidate(row,p))
            if is_old and is_new:
                old_urls={str(x.get("value",{}).get("url") or "") for x in row["claims"]
                          if isinstance(x,dict) and x.get("field")=="external.careers_page"}
                new_urls={str(x.get("value",{}).get("url") or "") for x in proposed["claims"]
                          if isinstance(x,dict) and x.get("field")=="external.careers_page"}
                extra_existing_careers_urls+=int(bool(new_urls-old_urls))
    assert len(seen)==300 and baseline_contracts==5
    assert len(audited)==1, "Source cohort differs from fixed M40 one-company result"
    flags=audited[0]["flags"]
    return {
        "schema":"m41_private_one_careers_archived_evidence_v1",
        "source":"ORIGINAL_SHA_PINNED_M19_A_M19_B_M20_A_V8_ONLY",
        "consumed_companies":300,
        "historical_existing_careers_company_claims":baseline_contracts,
        "reprojection_net_new_company_candidates":len(audited),
        "existing_careers_companies_with_extra_urls_replay_only":extra_existing_careers_urls,
        "one_candidate_archived_gate":flags,
        "candidate_recommended_for_future_human_source_review":sum(
            int(x["eligible_for_separate_manual_source_review"]) for x in audited
        ),
        "approved_for_automatic_publication":0,
        "human_review_completed":0,
        "official_recall_score_delta":None,
        "added_provider_search_requests":0,
        "added_company_website_requests":0,
        "baseline_or_qualified_v8_modified":False,
    }

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    for name,*_ in SOURCES:
        parser.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    args=parser.parse_args()
    files=[getattr(args,name) for name,*_ in SOURCES]
    report=audit_frozen_m41_archives(files)
    print(json.dumps(report,sort_keys=True))
    print("M41 private original-archive audit complete: zero new HTTP or publication.")

if __name__=="__main__":
    try:
        main()
    except Exception:
        # Do not leak source URLs/company identities/evidence in stack traces.
        print("M41 archived source gate blocked; no company-specific details disclosed.")
        raise SystemExit(1)
