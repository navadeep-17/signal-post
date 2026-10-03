#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_RUNNER = ROOT / "scripts" / "run_signalpost_v2.py"
V6_BUILDER = ROOT / "scripts" / "build_v6_ui.py"


def _arg_value(argv: list[str], flag: str) -> str | None:
    prefix = flag + "="
    for index, arg in enumerate(argv):
        if arg.startswith(prefix):
            return arg[len(prefix) :]
        if arg == flag and index + 1 < len(argv):
            return argv[index + 1]
    return None


def build_commands(argv: list[str]) -> tuple[list[str], list[str]]:
    output = _arg_value(argv, "--output")
    product_output = _arg_value(argv, "--product-output")
    expected_count = _arg_value(argv, "--expected-count")
    if not output:
        raise ValueError("V7 wrapper requires --output so the V6 workspace can be built from the final JSONL.")
    if not product_output:
        raise ValueError("V7 wrapper requires --product-output for the evaluator-facing V6 workspace.")

    legacy = [sys.executable, str(LEGACY_RUNNER), *argv]
    workspace = [
        sys.executable,
        str(V6_BUILDER),
        "--input",
        output,
        "--output",
        product_output,
    ]
    if expected_count:
        workspace.extend(["--expect-count", expected_count])
    return legacy, workspace


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        legacy, workspace = build_commands(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    first = subprocess.run(legacy, cwd=ROOT, check=False)
    if first.returncode != 0:
        return int(first.returncode)

    second = subprocess.run(workspace, cwd=ROOT, check=False)
    return int(second.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
