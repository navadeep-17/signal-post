#!/usr/bin/env python3
"""No-network M44 exact-candidate source gate on original prior-consumed 300 profiles."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from run_v10_m40_consumed_family_gap import SOURCES,audit_pinned_archives,_rows
from norway_company_agent.v10_m44_homepage_news_proof_gate import archived_nomination_gate

def evaluate(files:list[Path])->dict:
    origin=audit_pinned_archives(files)
    if origin["companies"]!=300:
        raise ValueError("Exact old V8 300 required")
    contracts=[]
    profiles=[]
    for file in files:
        with ZipFile(file) as archive:
            contracts+=_rows(archive.read("baseline-out/output.jsonl"))
            profiles+=_rows(archive.read("baseline-out/work/profiles.jsonl"))
    result=archived_nomination_gate(contracts,profiles)
    if (result["archived_original_companies"]!=300
        or result["exact_verified_websites"]!=41
        or result["news_nominating_websites"]!=2
        or result["nominated_urls"]!=3):
        raise ValueError("Original pinned source evidence unexpectedly changed")
    return result

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    for name,*_ in SOURCES:
        p.add_argument("--"+name.replace("_","-"),required=True,type=Path)
    args=p.parse_args()
    result=evaluate([getattr(args,name) for name,*_ in SOURCES])
    print(json.dumps(result,sort_keys=True))
    print("M44 archive-only source gate: no live requests, no official score claim")

if __name__=="__main__":
    try:
        main()
    except Exception:
        print("M44 pinned private source gate rejected input or failed; private details withheld.")
        raise SystemExit(1)
