#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_v2_product import build_v2_html  # noqa: E402
from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection  # noqa: E402
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the V2 data-linked product from an immutable output corpus.")
    parser.add_argument("--input", default="submission/final-release-1000-output.jsonl.gz")
    parser.add_argument("--output", default="submission/signalpost-v2.html")
    parser.add_argument("--expect-count", type=int, default=1000)
    args = parser.parse_args()

    rows = read_gzip_jsonl(Path(args.input))
    if len(rows) != args.expect_count:
        raise SystemExit(f"expected {args.expect_count} rows, got {len(rows)}")

    projected: list[dict[str, Any]] = []
    failures: list[str] = []
    for row in rows:
        org = str(row.get("organisation_number") or "")
        source_errors = validate_contract_object(row)
        item = project_canonical_profile(row)
        canonical_errors = validate_canonical_projection(item)
        if source_errors or canonical_errors:
            failures.append(f"{org}: source={source_errors}; canonical={canonical_errors}")
        projected.append(item)
    if failures:
        raise SystemExit("\n".join(failures[:20]))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        build_v2_html(projected, title="Signalpost V2 — evidence-backed company intelligence"),
        encoding="utf-8",
    )
    print(json.dumps({
        "input": str(args.input),
        "output": str(output),
        "companies": len(projected),
        "canonical_facts": sum(len(row.get("canonical_facts") or []) for row in projected),
        "bytes": output.stat().st_size,
        "data_linked": True,
        "canonical_areas": [
            "company_record",
            "financials",
            "people_and_locations",
            "company_website",
            "hiring_and_public_activity",
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
