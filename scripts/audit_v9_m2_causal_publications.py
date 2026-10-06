#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        rows.append(value)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Annotate M2 publication deltas with causal-exposure cohort buckets."
    )
    parser.add_argument("--cohort-audit", type=Path, required=True)
    parser.add_argument("--new-publications", type=Path, required=True)
    parser.add_argument("--lost-publications", type=Path, required=True)
    parser.add_argument("--annotated-new", type=Path, required=True)
    parser.add_argument("--annotated-lost", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    cohort_rows = read_jsonl(args.cohort_audit)
    by_org = {
        str(row.get("organisation_number") or ""): row
        for row in cohort_rows
    }
    if len(by_org) != len(cohort_rows):
        raise ValueError("cohort audit contains duplicate organisation numbers")

    def annotate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for row in rows:
            org = str(row.get("organisation_number") or "")
            cohort = by_org.get(org)
            if cohort is None:
                raise ValueError(f"publication delta outside targeted cohort: {org}")
            out.append(
                {
                    **row,
                    "m2_bucket": cohort.get("bucket"),
                    "baseline_candidate_domain": cohort.get("baseline_candidate_domain"),
                    "baseline_candidate_strength": cohort.get("baseline_candidate_strength"),
                    "challenger_candidate_domain": cohort.get("challenger_candidate_domain"),
                    "challenger_candidate_strength": cohort.get("challenger_candidate_strength"),
                }
            )
        return out

    new_rows = annotate(read_jsonl(args.new_publications))
    lost_rows = annotate(read_jsonl(args.lost_publications))

    def bucket_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
        return dict(sorted(Counter(str(row.get("m2_bucket") or "unknown") for row in rows).items()))

    control_buckets = {"strong_email_control", "no_email_control"}
    control_new = [row for row in new_rows if row.get("m2_bucket") in control_buckets]
    control_lost = [row for row in lost_rows if row.get("m2_bucket") in control_buckets]

    args.annotated_new.parent.mkdir(parents=True, exist_ok=True)
    args.annotated_new.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in new_rows),
        encoding="utf-8",
    )
    args.annotated_lost.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in lost_rows),
        encoding="utf-8",
    )

    report = {
        "new_publications": len(new_rows),
        "lost_publications": len(lost_rows),
        "new_by_bucket": bucket_counts(new_rows),
        "lost_by_bucket": bucket_counts(lost_rows),
        "control_new_publications": len(control_new),
        "control_lost_publications": len(control_lost),
        "control_variance_detected": bool(control_new or control_lost),
        "manual_audit_required_for_every_new_publication": True,
        "notes": [
            "Publication movement in control buckets is external-run variance, not evidence of M2 causality.",
            "Only the m2_delta bucket changes email-domain candidate allocation between V8 and V9.",
        ],
    }
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
