#!/usr/bin/env python3
"""Compare rights-clean official activity sources on a frozen consumed cohort.

Research-only. This script performs no network access and never publishes
production claims. It measures exact-org company coverage and, where a source
has a defensible recency signal, recent-activity coverage. Current production
Støtteregisteret coverage is treated as the baseline for net-new calculations.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ORG_RE = re.compile(r"^\d{9}$")


def norm_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if ORG_RE.fullmatch(digits) else None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}: JSONL row is not an object")
        rows.append(row)
    return rows


def load_cohort(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in read_jsonl(path):
        org = norm_org(
            row.get("organisation_number")
            or row.get("organization_number")
            or row.get("orgnr")
        )
        if not org:
            raise ValueError(f"invalid cohort organisation number: {row!r}")
        if org in out:
            raise ValueError(f"duplicate cohort organisation number: {org}")
        out[org] = str(row.get("name") or "")
    if not out:
        raise ValueError("empty cohort")
    return out


def org_from_row(row: dict[str, Any]) -> str | None:
    for key in (
        "organisation_number",
        "organization_number",
        "orgnr",
        "winner_org",
        "recipient_org",
    ):
        org = norm_org(row.get(key))
        if org:
            return org
    return None


def load_source(path: Path, targets: set[str], kind: str) -> tuple[set[str], set[str]]:
    all_hits: set[str] = set()
    recent_hits: set[str] = set()

    for row in read_jsonl(path):
        org = org_from_row(row)
        if not org or org not in targets:
            continue

        if kind == "landbruk":
            if int(row.get("positive_support_cells") or 0) <= 0:
                continue
            all_hits.add(org)
            # The 2025 file is useful exact activity evidence, but this frozen
            # artifact does not carry a precise event date; do not call it <=365d.
        elif kind == "arbeidstilsynet":
            all_hits.add(org)
            # Registry membership/current approval is a current official fact,
            # not a dated company activity event. Keep it out of recent activity.
        elif kind == "forskningsradet":
            if int(row.get("funded_project_rows") or 0) <= 0:
                continue
            all_hits.add(org)
            if (
                int(row.get("current_year_nonterminal_funded_project_rows") or 0) > 0
                or int(row.get("recent_start_funded_project_rows") or 0) > 0
            ):
                recent_hits.add(org)
        elif kind == "doffin":
            all_hits.add(org)
            if bool(row.get("recent365")):
                recent_hits.add(org)
        elif kind == "support":
            all_hits.add(org)
            recent_hits.add(org)
        else:
            raise ValueError(f"unknown source kind: {kind}")

    return all_hits, recent_hits


def parse_source(value: str) -> tuple[str, str, Path]:
    # NAME:KIND=PATH
    if "=" not in value or ":" not in value.split("=", 1)[0]:
        raise ValueError("--source must be NAME:KIND=PATH")
    lhs, rhs = value.split("=", 1)
    name, kind = lhs.split(":", 1)
    if not name or not kind or not rhs:
        raise ValueError("--source must be NAME:KIND=PATH")
    return name, kind, Path(rhs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", required=True, type=Path)
    ap.add_argument("--source", action="append", default=[], help="NAME:KIND=PATH")
    ap.add_argument("--baseline-source", required=True)
    ap.add_argument("--output-dir", required=True, type=Path)
    args = ap.parse_args()

    cohort = load_cohort(args.cohort)
    targets = set(cohort)
    if len(targets) != 1000:
        raise SystemExit(f"expected frozen consumed 1000, got {len(targets)}")

    parsed = [parse_source(v) for v in args.source]
    if not parsed:
        raise SystemExit("at least one --source is required")
    names = [x[0] for x in parsed]
    if len(names) != len(set(names)):
        raise SystemExit("duplicate source name")
    if args.baseline_source not in names:
        raise SystemExit("baseline source missing from --source")

    source_sets: dict[str, dict[str, set[str]]] = {}
    kinds: dict[str, str] = {}
    for name, kind, path in parsed:
        all_hits, recent_hits = load_source(path, targets, kind)
        source_sets[name] = {"all": all_hits, "recent": recent_hits}
        kinds[name] = kind

    baseline_all = source_sets[args.baseline_source]["all"]
    baseline_recent = source_sets[args.baseline_source]["recent"]

    candidate_names = [n for n in names if n != args.baseline_source]
    union_all: set[str] = set()
    union_recent: set[str] = set()
    for n in candidate_names:
        union_all |= source_sets[n]["all"]
        union_recent |= source_sets[n]["recent"]

    net_new_all = union_all - baseline_all
    net_new_recent = union_recent - baseline_recent

    per_source: dict[str, Any] = {}
    for name in names:
        a = source_sets[name]["all"]
        r = source_sets[name]["recent"]
        per_source[name] = {
            "kind": kinds[name],
            "all_exact_companies": len(a),
            "recent_activity_companies": len(r),
            "all_reach_pct": round(100 * len(a) / len(targets), 3),
            "recent_reach_pct": round(100 * len(r) / len(targets), 3),
            "all_overlap_baseline": len(a & baseline_all),
            "recent_overlap_baseline": len(r & baseline_recent),
            "all_net_new_vs_baseline": 0 if name == args.baseline_source else len(a - baseline_all),
            "recent_net_new_vs_baseline": 0 if name == args.baseline_source else len(r - baseline_recent),
        }

    pairwise: list[dict[str, Any]] = []
    for i, left in enumerate(candidate_names):
        for right in candidate_names[i + 1 :]:
            pairwise.append(
                {
                    "left": left,
                    "right": right,
                    "all_overlap": len(source_sets[left]["all"] & source_sets[right]["all"]),
                    "recent_overlap": len(
                        source_sets[left]["recent"] & source_sets[right]["recent"]
                    ),
                }
            )

    report = {
        "screen_type": "rights_clean_official_activity_union_vs_current_support",
        "cohort_companies": len(targets),
        "baseline_source": args.baseline_source,
        "per_source": per_source,
        "candidate_source_count": len(candidate_names),
        "candidate_union_all_companies": len(union_all),
        "candidate_union_recent_companies": len(union_recent),
        "candidate_union_all_reach_pct": round(100 * len(union_all) / len(targets), 3),
        "candidate_union_recent_reach_pct": round(100 * len(union_recent) / len(targets), 3),
        "union_all_overlap_current_support": len(union_all & baseline_all),
        "union_recent_overlap_current_support": len(union_recent & baseline_recent),
        "union_all_net_new_vs_current_support": len(net_new_all),
        "union_recent_net_new_vs_current_support": len(net_new_recent),
        "union_all_net_new_rate_pct": round(100 * len(net_new_all) / len(targets), 3),
        "union_recent_net_new_rate_pct": round(100 * len(net_new_recent) / len(targets), 3),
        "post_union_official_activity_companies": len(baseline_all | union_all),
        "post_union_recent_official_activity_companies": len(baseline_recent | union_recent),
        "pairwise_candidate_overlaps": pairwise,
        "net_new_all_companies": [
            {"organisation_number": org, "name": cohort.get(org, "")}
            for org in sorted(net_new_all)
        ],
        "net_new_recent_companies": [
            {"organisation_number": org, "name": cohort.get(org, "")}
            for org in sorted(net_new_recent)
        ],
        "notes": [
            "Exact nine-digit organisation number is the only company join.",
            "The comparator is network-free; source workflows own source-specific identity and rights checks.",
            "Current Støtteregisteret is the production baseline.",
            "Arbeidstilsynet current-registry facts are not mislabelled as <=365-day activity.",
            "Landbruk 2025 rows are not mislabelled as <=365-day without an exact event date.",
        ],
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "net-new-all.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in report["net_new_all_companies"]),
        encoding="utf-8",
    )
    (args.output_dir / "net-new-recent.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in report["net_new_recent_companies"]),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
