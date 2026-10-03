#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import read_organisation_inputs  # noqa: E402

V7_RUNNER = ROOT / "scripts" / "run_signalpost_v7.py"
SMOKE_TEST_MIN_REQUEST_BUDGET = 2000
REQUEST_BUDGET_PER_COMPANY = 20
SMOKE_TEST_MIN_WALL_RUNTIME_SECONDS = 2400
WALL_RUNTIME_SECONDS_PER_COMPANY = 3


def _arg_value(argv: list[str], flag: str) -> str | None:
    prefix = flag + "="
    for index, arg in enumerate(argv):
        if arg.startswith(prefix):
            return arg[len(prefix) :]
        if arg == flag:
            if index + 1 >= len(argv):
                raise ValueError(f"V8 wrapper requires a value after {flag}")
            return argv[index + 1]
    return None


def _set_arg(argv: list[str], flag: str, value: str) -> list[str]:
    args = list(argv)
    prefix = flag + "="
    for index, arg in enumerate(args):
        if arg.startswith(prefix):
            args[index] = prefix + value
            return args
        if arg == flag:
            if index + 1 >= len(args):
                raise ValueError(f"V8 wrapper requires a value after {flag}")
            args[index + 1] = value
            return args
    return [*args, flag, value]


def default_request_budget(expected_count: int) -> int:
    if expected_count < 1:
        raise ValueError("expected_count must be positive")
    return max(SMOKE_TEST_MIN_REQUEST_BUDGET, REQUEST_BUDGET_PER_COMPANY * expected_count)


def default_wall_runtime_seconds(expected_count: int) -> int:
    if expected_count < 1:
        raise ValueError("expected_count must be positive")
    return max(
        SMOKE_TEST_MIN_WALL_RUNTIME_SECONDS,
        WALL_RUNTIME_SECONDS_PER_COMPANY * expected_count,
    )


def prepare_evaluator_args(argv: list[str]) -> tuple[list[str], dict[str, int]]:
    organisations = _arg_value(argv, "--organisations")
    if not organisations:
        raise ValueError("V8 wrapper requires --organisations so the evaluator batch size can be derived.")

    inputs = read_organisation_inputs(organisations)
    expected_count = len(inputs)
    if expected_count < 1:
        raise ValueError("V8 wrapper requires at least one organisation input.")

    explicit_expected = _arg_value(argv, "--expected-count")
    if explicit_expected is not None:
        try:
            configured_expected = int(explicit_expected)
        except ValueError as exc:
            raise ValueError("--expected-count must be an integer") from exc
        if configured_expected != expected_count:
            raise ValueError(
                f"--expected-count={configured_expected} does not match the supplied evaluator batch ({expected_count})."
            )

    prepared = _set_arg(argv, "--expected-count", str(expected_count))

    explicit_request_budget = _arg_value(prepared, "--max-challenge-requests")
    if explicit_request_budget is None:
        request_budget = default_request_budget(expected_count)
        prepared = _set_arg(prepared, "--max-challenge-requests", str(request_budget))
    else:
        try:
            request_budget = int(explicit_request_budget)
        except ValueError as exc:
            raise ValueError("--max-challenge-requests must be an integer") from exc
        if request_budget < 1:
            raise ValueError("--max-challenge-requests must be positive")

    explicit_wall_runtime = _arg_value(prepared, "--max-wall-runtime-seconds")
    if explicit_wall_runtime is None:
        wall_runtime = default_wall_runtime_seconds(expected_count)
        prepared = _set_arg(prepared, "--max-wall-runtime-seconds", str(wall_runtime))
    else:
        try:
            wall_runtime = int(explicit_wall_runtime)
        except ValueError as exc:
            raise ValueError("--max-wall-runtime-seconds must be an integer") from exc
        if wall_runtime < 1:
            raise ValueError("--max-wall-runtime-seconds must be positive")

    return prepared, {
        "expected_count": expected_count,
        "max_challenge_requests": request_budget,
        "max_wall_runtime_seconds": wall_runtime,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        prepared, settings = prepare_evaluator_args(args)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        "Signalpost V8 evaluator batch: "
        f"{settings['expected_count']} companies; "
        f"internal conservative request ceiling={settings['max_challenge_requests']}; "
        f"internal wall-runtime validation ceiling={settings['max_wall_runtime_seconds']}s.",
        file=sys.stderr,
    )
    completed = subprocess.run(
        [sys.executable, str(V7_RUNNER), *prepared],
        cwd=ROOT,
        check=False,
    )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
