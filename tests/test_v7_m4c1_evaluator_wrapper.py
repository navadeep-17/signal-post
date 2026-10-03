from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_signalpost_v7 as wrapper  # noqa: E402


def test_build_commands_preserves_v5_runner_args_and_promotes_product_output() -> None:
    args = [
        "--organisations",
        "evaluator-100.jsonl",
        "--bulk=brreg-enheter.csv",
        "--output",
        "out/final-output.jsonl",
        "--report",
        "out/final-report.json",
        "--product-output=out/signalpost.html",
        "--expected-count",
        "100",
        "--workers",
        "8",
    ]

    legacy, workspace = wrapper.build_commands(args)

    assert legacy[0] == sys.executable
    assert legacy[1] == str(wrapper.LEGACY_RUNNER)
    assert legacy[2:] == args
    assert workspace == [
        sys.executable,
        str(wrapper.V6_BUILDER),
        "--input",
        "out/final-output.jsonl",
        "--output",
        "out/signalpost.html",
        "--expect-count",
        "100",
    ]


def test_wrapper_requires_final_and_product_paths() -> None:
    for args, message in [
        (["--product-output", "out/product.html"], "requires --output"),
        (["--output", "out/final.jsonl"], "requires --product-output"),
    ]:
        try:
            wrapper.build_commands(args)
        except ValueError as exc:
            assert message in str(exc)
        else:
            raise AssertionError("expected wrapper validation error")


def test_wrapper_builds_v6_only_after_legacy_runner_succeeds(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)
    rc = wrapper.main(
        [
            "--output",
            "out/final-output.jsonl",
            "--product-output",
            "out/signalpost.html",
            "--expected-count",
            "100",
        ]
    )

    assert rc == 0
    assert len(calls) == 2
    assert calls[0][1] == str(wrapper.LEGACY_RUNNER)
    assert calls[1][1] == str(wrapper.V6_BUILDER)
    assert calls[1][-2:] == ["--expect-count", "100"]


def test_wrapper_does_not_build_v6_after_legacy_failure(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)
    rc = wrapper.main(["--output", "out/final.jsonl", "--product-output", "out/product.html"])

    assert rc == 7
    assert len(calls) == 1
    assert calls[0][1] == str(wrapper.LEGACY_RUNNER)
