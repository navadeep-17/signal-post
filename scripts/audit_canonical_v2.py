#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import (  # noqa: E402
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402


def read_gzip_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"Expected object at {path}:{line_no}")
            rows.append(row)
    return rows


def _role_row_counts(row: dict[str, Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for claim in row.get("claims") or []:
        if not isinstance(claim, dict) or claim.get("field") != "roles" or claim.get("availability") != "available":
            continue
        value = claim.get("value") or {}
        roles = value.get("roles") if isinstance(value, dict) else None
        if not isinstance(roles, list):
            continue
        for role in roles:
            if not isinstance(role, dict):
                continue
            counts["inactive" if role.get("inactive") is True else "active"] += 1
    return counts


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    projected = [project_canonical_profile(row) for row in rows]
    validation_errors: list[dict[str, str]] = []
    fact_counts: Counter[str] = Counter()
    area_counts: Counter[str] = Counter()
    source_role_counts: Counter[str] = Counter()

    for source, row in zip(rows, projected, strict=True):
        source_role_counts.update(_role_row_counts(source))
        org = str(row.get("organisation_number") or "")
        for error in validate_contract_object(row):
            validation_errors.append({"organisation_number": org, "layer": "output_contract", "error": error})
        for error in validate_canonical_projection(row):
            validation_errors.append({"organisation_number": org, "layer": "canonical_projection", "error": error})
        for fact in row.get("canonical_facts") or []:
            fact_counts[str(fact.get("type") or "unknown")] += 1
        for key, value in ((row.get("canonical_profile") or {}).get("data_areas") or {}).items():
            if value:
                area_counts[str(key)] += 1

    return {
        "companies": len(projected),
        "unique_organisation_numbers": len({str(row.get("organisation_number") or "") for row in projected}),
        "canonical_facts": sum(fact_counts.values()),
        "fact_type_counts": dict(sorted(fact_counts.items())),
        "companies_by_data_area": dict(sorted(area_counts.items())),
        "source_role_rows": {
            "active": source_role_counts["active"],
            "inactive": source_role_counts["inactive"],
            "total": source_role_counts["active"] + source_role_counts["inactive"],
        },
        "validation_errors": validation_errors,
        "passed": len(projected) == len({str(row.get("organisation_number") or "") for row in projected}) and not validation_errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit V2 canonical mapping over a frozen output corpus.")
    parser.add_argument(
        "--input",
        default="submission/final-release-1000-output.jsonl.gz",
        help="gzip JSONL output corpus",
    )
    parser.add_argument("--expect-count", type=int, default=1000)
    args = parser.parse_args()

    report = audit(read_gzip_jsonl(Path(args.input)))
    if report["companies"] != args.expect_count:
        report["validation_errors"].append(
            {
                "organisation_number": "",
                "layer": "audit",
                "error": f"expected {args.expect_count} companies, got {report['companies']}",
            }
        )
        report["passed"] = False
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
