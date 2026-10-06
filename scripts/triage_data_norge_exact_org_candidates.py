#!/usr/bin/env python3
"""Offline triage of frozen Data.norge exact-org catalogue candidates.

No network access. The input is the frozen broad-catalogue candidates.jsonl.
The aim is to identify potentially broad/current source families before any
dataset download or API probe.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

BROAD_HINTS = (
    "register",
    "virksom",
    "bedrift",
    "foretak",
    "leverand",
    "tillat",
    "godkjent",
    "løyve",
    "loyve",
    "autorisasjon",
    "sertif",
    "arbeidsgiver",
)
NICHE_HINTS = (
    "jordbruk",
    "landbruk",
    "fisk",
    "akvakultur",
    "petroleum",
    "olje",
    "miljøtilskudd",
    "miljotilskudd",
    "produksjonstilskudd",
    "slakteri",
)
STALE_YEAR_RE = re.compile(r"\b(20(?:0\d|1\d|2[0-3]))\b")


def read_rows(path: Path) -> list[dict[str, Any]]:
    rows=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row=json.loads(line)
            if isinstance(row,dict):
                rows.append(row)
    return rows


def score(row: dict[str, Any]) -> tuple[int,list[str]]:
    title=str(row.get("title") or "")
    org=str(row.get("organization") or "")
    cats=[str(x) for x in row.get("semantic_categories") or []]
    modified=str(row.get("modified") or "")
    text=" ".join([title,org,*cats]).casefold()
    points=0
    reasons=[]

    if any(h in text for h in BROAD_HINTS):
        points+=5; reasons.append("broad-title-hint")
    if "website" in cats:
        points+=6; reasons.append("website-value")
    if "contact" in cats:
        points+=4; reasons.append("contact-value")
    if "activity" in cats:
        points+=3; reasons.append("activity-value")
    if "procurement" in cats:
        points+=4; reasons.append("procurement-value")
    if any(h in text for h in NICHE_HINTS):
        points-=6; reasons.append("sector-niche")
    if modified.startswith("2026"):
        points+=5; reasons.append("modified-2026")
    elif modified.startswith("2025"):
        points+=3; reasons.append("modified-2025")
    elif modified.startswith("2024"):
        points+=1; reasons.append("modified-2024")

    years=[int(x) for x in STALE_YEAR_RE.findall(title)]
    if years and max(years)<=2023:
        points-=4; reasons.append("title-old-year")

    return points,reasons


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidates",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    args=ap.parse_args()

    rows=read_rows(args.candidates)
    ranked=[]
    for row in rows:
        points,reasons=score(row)
        ranked.append({
            "dataset":row.get("dataset"),
            "title":row.get("title"),
            "organization":row.get("organization"),
            "modified":row.get("modified"),
            "formats":row.get("formats"),
            "semantic_categories":row.get("semantic_categories"),
            "prior_selection_score":row.get("selection_score"),
            "triage_score":points,
            "triage_reasons":reasons,
        })
    ranked.sort(key=lambda r:(-r["triage_score"],str(r.get("title") or "")))
    report={
        "screen_type":"offline_data_norge_exact_org_candidate_triage",
        "network_requests":0,
        "candidate_count":len(ranked),
        "top_candidates":ranked[:85],
    }
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
