#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Signalpost V2: run the qualified collector, emit canonical facts, and build the data-linked product surface.",
        add_help=False,
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--product-output")
    known, remaining = parser.parse_known_args()

    output = Path(known.output)
    product_output = Path(known.product_output) if known.product_output else output.with_suffix(".html")

    runner = ROOT / "scripts" / "run_signalpost_final.py"
    builder = ROOT / "scripts" / "build_submission_prototype.py"
    runner_args = [sys.executable, str(runner), "--output", str(output), *remaining]
    completed = subprocess.run(runner_args, cwd=ROOT, check=False)
    if completed.returncode != 0:
        return completed.returncode

    rows = _read_jsonl(output)
    missing = [row.get("organisation_number") for row in rows if not isinstance(row.get("canonical"), dict)]
    if missing:
        raise SystemExit(f"V2 canonical projection missing for {len(missing)} output rows; first={missing[0]}")

    product_output.parent.mkdir(parents=True, exist_ok=True)
    built = subprocess.run(
        [
            sys.executable,
            str(builder),
            "--input",
            str(output),
            "--output",
            str(product_output),
            "--title",
            "Signalpost canonical company intelligence",
        ],
        cwd=ROOT,
        check=False,
    )
    if built.returncode != 0:
        return built.returncode

    print(json.dumps({
        "output": str(output),
        "product_output": str(product_output),
        "canonical_rows": len(rows),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
