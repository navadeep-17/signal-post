#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_contract import (  # noqa: E402
    project_canonical_contract,
    validate_canonical_contract,
)
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project an existing Signalpost output JSONL into the V2 canonical schema without network access."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = Path(args.input)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)

    rows = 0
    with source.open("r", encoding="utf-8") as reader, destination.open("w", encoding="utf-8") as writer:
        for line_no, line in enumerate(reader, 1):
            if not line.strip():
                continue
            item = json.loads(line)
            base_errors = validate_contract_object(item)
            if base_errors:
                raise SystemExit(f"input contract invalid at line {line_no}: {base_errors[:5]}")
            projected = project_canonical_contract(item)
            canonical_errors = validate_canonical_contract(projected)
            if canonical_errors:
                raise SystemExit(f"canonical projection invalid at line {line_no}: {canonical_errors[:5]}")
            writer.write(json.dumps(projected, ensure_ascii=False, separators=(",", ":")) + "\n")
            rows += 1

    print(json.dumps({"input": str(source), "output": str(destination), "rows": rows}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
