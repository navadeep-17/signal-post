#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.external_gap_audit import audit_external_gap_coverage  # noqa: E402


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline Q4-Q6 coverage bottleneck audit over final contracts and retained profiles."
    )
    parser.add_argument("--output-contract", required=True, help="Final OUTPUT_CONTRACT JSONL")
    parser.add_argument("--profiles", required=True, help="Retained enriched profile JSONL")
    parser.add_argument("--run-report", help="Optional final run report JSON for request/source context")
    parser.add_argument("--report", required=True, help="Audit report JSON")
    args = parser.parse_args()

    run_report = None
    if args.run_report:
        run_report = json.loads(Path(args.run_report).read_text(encoding="utf-8"))

    report = audit_external_gap_coverage(
        read_jsonl(Path(args.output_contract)),
        read_jsonl(Path(args.profiles)),
        run_report=run_report,
    )
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
