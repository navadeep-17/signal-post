#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.evidence_visibility import audit_contract_rows  # noqa: E402


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            rows.append(value)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit evaluator-visible claim/evidence completeness without network access."
    )
    parser.add_argument("--input", required=True, help="V7/V8 final JSONL output")
    parser.add_argument("--output", help="Optional JSON report path")
    parser.add_argument(
        "--fail-on-core-gaps",
        action="store_true",
        help="Return non-zero when an available claim lacks URL/time/span/hash/reopenable URL.",
    )
    args = parser.parse_args(argv)

    try:
        rows = _read_jsonl(Path(args.input))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    report = audit_contract_rows(rows)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)

    if args.fail_on_core_gaps and any(
        "source_url" in issue["missing"]
        or "retrieved_at" in issue["missing"]
        or "claim_span" in issue["missing"]
        or "content_sha256" in issue["missing"]
        or "reopenable_source_url" in issue["missing"]
        or "referenced_evidence" in issue["missing"]
        for issue in report["issues"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
