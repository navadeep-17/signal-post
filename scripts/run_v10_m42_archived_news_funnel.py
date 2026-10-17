#!/usr/bin/env python3
"""Run M42 over exact earlier M19-A/B/M20-A V8 artifacts, print aggregate only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from run_v10_m40_consumed_family_gap import SOURCES,audit_pinned_archives,_rows
from norway_company_agent.v10_m42_archived_news_funnel import news_root_cause_counts

def audit_m42(files:list[Path])->dict:
    old=audit_pinned_archives(files)
    if old["companies"]!=300 or old["company_counts_by_typed_family"]["first_party_company_update"]!=3:
        raise ValueError("Archived M40 baseline not exact, M42 stopped")
    ps=[]
    cs=[]
    for path in files:
        with ZipFile(path) as z:
            ps.extend(_rows(z.read("baseline-out/work/profiles.jsonl")))
            cs.extend(_rows(z.read("baseline-out/output.jsonl")))
    result=news_root_cause_counts(cs,ps)
    if result["stage_counts"]["total_companies"]!=300:
        raise ValueError("Expected original 300 companies only")
    if result["stage_counts"]["companies_with_published_company_updates"]!=3:
        raise ValueError("Existing exact-page news publication count changed")
    return result

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    for name,*_ in SOURCES:
        parser.add_argument("--"+name.replace("_","-"),required=True,type=Path)
    args=parser.parse_args()
    result=audit_m42([getattr(args,name) for name,*_ in SOURCES])
    print(json.dumps(result,sort_keys=True))
    print("M42 complete: 300 original frozen V8 profiles, zero requests, zero new publication.")

if __name__=="__main__":
    try:
        main()
    except Exception:
        print("M42 archived audit blocked; no company-specific source information is disclosed.")
        raise SystemExit(1)
