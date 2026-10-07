#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

KNOWN_RESEARCHED_ORGS = {
    "927097532", "979943377", "999096298",
    "828829092", "870418892", "896488562", "898321622",
    "911546221", "914384729", "936455298", "976533194",
    "979436661", "988936987", "992784229", "996405524",
    "811413682", "811730912", "883971752", "923609016",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value=json.loads(line)
            if not isinstance(value,dict):
                raise ValueError(f"{path}: JSON objects required")
            rows.append(value)
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(
        "".join(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n" for row in rows),
        encoding="utf-8",
    )


def _available_claim(row: dict[str, Any], field: str) -> dict[str, Any] | None:
    for claim in row.get("claims") or []:
        if (
            isinstance(claim,dict)
            and claim.get("field")==field
            and claim.get("availability")=="available"
            and claim.get("value") not in (None,"")
        ):
            return claim
    return None


def _website_is_company_owned(row: dict[str, Any], claim: dict[str, Any]) -> bool:
    evidence_by_id={
        str(item.get("id")):item
        for item in (row.get("evidence") or [])
        if isinstance(item,dict) and item.get("id")
    }
    ids=[str(x) for x in (claim.get("evidence_ids") or []) if str(x)]
    if not ids:
        return False
    evidence_rows=[evidence_by_id.get(eid) for eid in ids]
    return bool(
        all(
            isinstance(item,dict)
            and item.get("source_class")=="company_owned"
            for item in evidence_rows
        )
    )


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--legacy-output",type=Path,required=True)
    p.add_argument("--m10-exclude",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--count",type=int,default=20)
    args=p.parse_args()

    legacy=_read_jsonl(args.legacy_output)
    if len(legacy)!=1000:
        raise ValueError(f"expected exact 1000-company legacy aggregate, got {len(legacy)}")

    m10_rows=_read_jsonl(args.m10_exclude)
    m10_orgs={str(row.get("organisation_number") or "") for row in m10_rows}
    if len(m10_rows)!=100 or len(m10_orgs)!=100:
        raise ValueError("expected exact M10 Gate-B 100-company exclusion manifest")

    excluded=set(KNOWN_RESEARCHED_ORGS)|m10_orgs
    eligible: list[dict[str, Any]]=[]
    for row in legacy:
        org=str(row.get("organisation_number") or "")
        if len(org)!=9 or not org.isdigit() or org in excluded:
            continue
        claim=_available_claim(row,"official_website")
        if claim is None or not _website_is_company_owned(row,claim):
            continue
        eligible.append({
            "organisation_number":org,
            "evaluation_split":"v10_m18_consumed_current_downstream_audit",
            "sample_slice":"legacy_company_owned_verified_site",
        })

    eligible.sort(key=lambda row:row["organisation_number"])
    if len(eligible)<args.count:
        raise ValueError(f"only {len(eligible)} eligible companies remain")
    selected=eligible[:args.count]
    _write_jsonl(args.output,selected)

    report={
        "audit":"v10_m18_current_downstream_coverage",
        "legacy_population_companies":1000,
        "legacy_company_owned_site_eligible_after_exclusions":len(eligible),
        "selected_companies":len(selected),
        "fresh_companies_used":0,
        "m10_gate_b_companies_excluded":len(m10_orgs),
        "known_researched_public_orgs_excluded":len(KNOWN_RESEARCHED_ORGS),
        "legacy_output_sha256":_sha256(args.legacy_output),
        "m10_exclude_sha256":_sha256(args.m10_exclude),
        "target_manifest_sha256":_sha256(args.output),
        "selection_rule":[
            "start with immutable already-consumed 1000-company final-release aggregate",
            "require a legacy available official_website claim",
            "require every website evidence row to have source_class=company_owned",
            "exclude the entire M10 Gate-B 100-company cohort",
            "exclude known M10/M12 research cases and Builderr public examples",
            "sort by organisation number and take first requested count",
            "no current website/careers/news outcome influences selection",
        ],
    }
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(
        json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )
    print(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
