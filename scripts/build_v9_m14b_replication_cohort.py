#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load_m14_builder():
    path = ROOT / "scripts" / "build_v9_m14_consumed_cohort.py"
    spec = importlib.util.spec_from_file_location("m14_builder", path)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load M14 builder")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M14 = _load_m14_builder()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows=[json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{path}: all rows must be objects")
    return rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--source-manifest",type=Path,required=True)
    p.add_argument("--bulk",type=Path,required=True)
    p.add_argument("--prior-search-manifest",type=Path,required=True)
    p.add_argument("--prior-m14-manifest",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--audit",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--treated-count",type=int,default=20)
    p.add_argument("--control-count",type=int,default=80)
    args=p.parse_args()

    if sha256(args.prior_search_manifest) != M14.PR137_GATE_A_SHA256:
        raise ValueError("PR #137 prior-search manifest SHA mismatch")

    source=M14.read_organisation_inputs(args.source_manifest)
    source_orgs=[row["organisation_number"] for row in source]
    if len(source_orgs)!=1000 or len(set(source_orgs))!=1000:
        raise ValueError("expected exact frozen consumed 1000")

    prior_search=M14.read_organisation_inputs(args.prior_search_manifest)
    prior_search_orgs={row["organisation_number"] for row in prior_search}
    if len(prior_search_orgs)!=20:
        raise ValueError("expected exact PR #137 20-company development set")

    prior_m14=read_jsonl(args.prior_m14_manifest)
    prior_m14_orgs={str(row.get("organisation_number") or "") for row in prior_m14}
    if len(prior_m14_orgs)!=100:
        raise ValueError("expected exact prior M14 100-company cohort")

    profiles,snapshot=M14.profiles_from_bulk(args.bulk,source_orgs)
    remaining=[
        profile for profile in profiles
        if str(profile.get("organisation_number") or "") not in prior_m14_orgs
    ]

    manifest,audit,report=M14.build(
        remaining,
        prior_search_orgs=prior_search_orgs,
        treated_count=args.treated_count,
        control_count=args.control_count,
    )

    selected={row["organisation_number"] for row in manifest}
    if selected & prior_m14_orgs:
        raise AssertionError("M14b cohort overlaps prior M14 cohort")

    for row in manifest:
        row["evaluation_split"]="v9_m14b_consumed_compact_com_replication"
    for row in audit:
        row["replication_prior_m14_excluded"]=True

    M14.write_jsonl(args.output,manifest)
    M14.write_jsonl(args.audit,audit)
    report.update({
        "screen_type":"v9_m14b_consumed_single_token_compact_com_replication",
        "source_population_companies":1000,
        "prior_m14_companies_excluded":100,
        "prior_m14_manifest_sha256":sha256(args.prior_m14_manifest),
        "replication_disjoint_from_prior_m14":True,
        "target_manifest_sha256":sha256(args.output),
        "registry_snapshot_sha256":snapshot.get("registry_snapshot_sha256"),
        "registry_snapshot_missing_count":snapshot.get("missing_count"),
    })
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
