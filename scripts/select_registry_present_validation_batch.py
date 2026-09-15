#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.sampling import iter_bulk


def _open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else path.open("r", encoding="utf-8")


def _org(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("organisation_number")
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) != 9:
        raise ValueError(f"Invalid Norwegian organisation number: {value!r}")
    return digits


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with _open_text(path) as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"Expected JSON object rows in {path}")
            _org(item)
            rows.append(item)
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select a deterministic validation batch that is disjoint and present in the current BRREG bulk snapshot."
    )
    parser.add_argument("--universe", required=True)
    parser.add_argument("--exclude", required=True)
    parser.add_argument("--registry-bulk", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--count", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20260921)
    parser.add_argument("--evaluation-split", default="registry_present_zero_overlap_validation")
    parser.add_argument("--sample-slice", default="registry_present_external_validation")
    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count must be positive")

    universe_path = Path(args.universe)
    exclude_path = Path(args.exclude)
    registry_path = Path(args.registry_bulk)
    output_path = Path(args.output)
    report_path = Path(args.report)

    universe_rows = _read_jsonl(universe_path)
    exclude_rows = _read_jsonl(exclude_path)
    excluded = {_org(row) for row in exclude_rows}
    if len(excluded) != len(exclude_rows):
        raise ValueError("Exclude manifest contains duplicate organisation numbers")

    registry_orgs: set[str] = set()
    registry_rows = 0
    for row in iter_bulk(registry_path):
        registry_rows += 1
        org = _org(row)
        if org in registry_orgs:
            raise ValueError(f"Current BRREG bulk contains duplicate organisation number: {org}")
        registry_orgs.add(org)

    eligible = [
        row for row in universe_rows
        if _org(row) not in excluded and _org(row) in registry_orgs
    ]
    if args.count > len(eligible):
        raise SystemExit(
            f"Requested {args.count}; only {len(eligible)} disjoint current-registry companies are available"
        )

    chosen = random.Random(args.seed).sample(eligible, args.count)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in chosen:
            item = dict(row)
            item["evaluation_split"] = args.evaluation_split
            item["sample_slice"] = args.sample_slice
            handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")

    selected = [_org(row) for row in chosen]
    overlap = sorted(set(selected) & excluded)
    missing_registry = sorted(set(selected) - registry_orgs)
    if overlap:
        raise RuntimeError(f"Validation sample overlaps excluded manifest: {overlap[:10]}")
    if missing_registry:
        raise RuntimeError(f"Validation sample contains rows absent from current BRREG: {missing_registry[:10]}")
    if len(selected) != len(set(selected)):
        raise RuntimeError("Validation sample contains duplicate organisation numbers")

    universe_orgs = {_org(row) for row in universe_rows}
    report = {
        "seed": args.seed,
        "count": args.count,
        "universe_rows": len(universe_rows),
        "excluded_rows": len(excluded),
        "registry_rows": registry_rows,
        "registry_unique_orgs": len(registry_orgs),
        "universe_rows_present_in_registry": len(universe_orgs & registry_orgs),
        "eligible_rows": len(eligible),
        "overlap_count": len(overlap),
        "missing_registry_count": len(missing_registry),
        "evaluation_split": args.evaluation_split,
        "sample_slice": args.sample_slice,
        "universe_sha256": _sha256(universe_path),
        "exclude_manifest_sha256": _sha256(exclude_path),
        "registry_snapshot_sha256": _sha256(registry_path),
        "output_sha256": _sha256(output_path),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
