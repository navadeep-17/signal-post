#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalise_org(value: Any) -> str:
    org = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(org) != 9:
        raise ValueError(f"invalid organisation number: {value!r}")
    return org


def read_unique_jsonl(path: Path) -> tuple[list[dict[str, Any]], set[str]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected object")
        org = normalise_org(value.get("organisation_number"))
        if org in seen:
            raise ValueError(f"{path}:{line_number}: duplicate organisation number {org}")
        seen.add(org)
        rows.append(value)
    return rows, seen


def build_exclusion(
    prior_path: Path,
    failed_fresh_path: Path,
    output_path: Path,
    report_path: Path,
    *,
    expected_prior: int = 8423,
    expected_failed: int = 100,
    expected_union: int = 8523,
) -> dict[str, Any]:
    prior_rows, prior_orgs = read_unique_jsonl(prior_path)
    failed_rows, failed_orgs = read_unique_jsonl(failed_fresh_path)

    if len(prior_orgs) != expected_prior:
        raise ValueError(f"prior exclusion count {len(prior_orgs)} != {expected_prior}")
    if len(failed_orgs) != expected_failed:
        raise ValueError(f"failed fresh count {len(failed_orgs)} != {expected_failed}")

    overlap = sorted(prior_orgs & failed_orgs)
    if overlap:
        raise ValueError(f"failed fresh cohort overlaps prior exclusion: {overlap[:10]}")

    combined = [*prior_rows, *failed_rows]
    combined_orgs = prior_orgs | failed_orgs
    if len(combined_orgs) != expected_union:
        raise ValueError(f"union count {len(combined_orgs)} != {expected_union}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in combined),
        encoding="utf-8",
    )

    report = {
        "schema_version": "signalpost-q8-exclusion-v1",
        "prior_exclusion_rows": len(prior_orgs),
        "failed_fresh_rows": len(failed_orgs),
        "source_overlap_count": len(overlap),
        "union_unique_companies": len(combined_orgs),
        "prior_exclusion_sha256": sha256(prior_path),
        "failed_fresh_sha256": sha256(failed_fresh_path),
        "exclude_sha256": sha256(output_path),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Q8 all-touched exclusion from prior exclusion + failed fresh cohort.")
    parser.add_argument("--prior", required=True)
    parser.add_argument("--failed-fresh", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--expected-prior", type=int, default=8423)
    parser.add_argument("--expected-failed", type=int, default=100)
    parser.add_argument("--expected-union", type=int, default=8523)
    args = parser.parse_args()

    report = build_exclusion(
        Path(args.prior),
        Path(args.failed_fresh),
        Path(args.output),
        Path(args.report),
        expected_prior=args.expected_prior,
        expected_failed=args.expected_failed,
        expected_union=args.expected_union,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
