#!/usr/bin/env python3
"""M43 read-only diagnostics for M42's already-consumed 300 V8 companies."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from run_v10_m40_consumed_family_gap import SOURCES,audit_pinned_archives,_rows
from norway_company_agent.v10_m43_archived_news_source_failures import source_failure_categories

def run_m43(files:list[Path])->dict:
    proof=audit_pinned_archives(files)
    assert proof["companies"]==300
    c=[]
    p=[]
    for filename in files:
        with ZipFile(filename) as archive:
            p.extend(_rows(archive.read("baseline-out/work/profiles.jsonl")))
            c.extend(_rows(archive.read("baseline-out/output.jsonl")))
    result=source_failure_categories(c,p)
    assert result["exact_verified_sites"]==41
    assert result["news_nomination_intersections"]["news_nominated_sites"]==2
    return result

def main()->None:
    parser=argparse.ArgumentParser()
    for name,*_ in SOURCES:
        parser.add_argument("--"+name.replace("_","-"),required=True,type=Path)
    args=parser.parse_args()
    report=run_m43([getattr(args,name) for name,*_ in SOURCES])
    print(json.dumps(report,sort_keys=True))
    print("M43 archival source-veto review complete: 0 provider/site requests, 0 new facts.")

if __name__=="__main__":
    try:
        main()
    except Exception:
        print("M43 archival source review failed closed, without source detail exposure.")
        raise SystemExit(1)
