#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Any, TextIO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_measurement import (  # noqa: E402
    compare_company_family_coverage,
    publication_diff,
)


def _open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with _open_text(path) as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare V9 score-family company coverage on identical baseline/challenger cohorts."
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--challenger", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--new-publications", type=Path)
    parser.add_argument("--lost-publications", type=Path)
    args = parser.parse_args()

    baseline_rows = read_jsonl(args.baseline)
    challenger_rows = read_jsonl(args.challenger)
    report = compare_company_family_coverage(baseline_rows, challenger_rows)
    audit = publication_diff(baseline_rows, challenger_rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    for path, rows in (
        (args.new_publications, audit["added"]),
        (args.lost_publications, audit["lost"]),
    ):
        if path is None:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
    report["new_publications"] = len(audit["added"])
    report["lost_publications"] = len(audit["lost"])
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
