from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_signalpost_v7 as wrapper  # noqa: E402


def arg_value(args: list[str], flag: str) -> str | None:
    prefix = flag + "="
    for index, arg in enumerate(args):
        if arg.startswith(prefix):
            return arg[len(prefix) :]
        if arg == flag and index + 1 < len(args):
            return args[index + 1]
    return None


def test_build_commands_reserves_support_budget_and_promotes_product_output() -> None:
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
        "--max-challenge-requests",
        "2000",
    ]

    legacy, workspace = wrapper.build_commands(args)

    assert legacy[0] == sys.executable
    assert legacy[1] == str(wrapper.LEGACY_RUNNER)
    forwarded = legacy[2:]
    assert arg_value(forwarded, "--max-challenge-requests") == "1998"
    assert arg_value(forwarded, "--organisations") == "evaluator-100.jsonl"
    assert arg_value(forwarded, "--report") == "out/final-report.json"
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


def test_wrapper_requires_final_report_and_product_paths() -> None:
    cases = [
        (["--report", "out/report.json", "--product-output", "out/product.html"], "requires --output"),
        (["--output", "out/final.jsonl", "--product-output", "out/product.html"], "requires --report"),
        (["--output", "out/final.jsonl", "--report", "out/report.json"], "requires --product-output"),
    ]
    for args, message in cases:
        try:
            wrapper.build_commands(args)
        except ValueError as exc:
            assert message in str(exc)
        else:
            raise AssertionError("expected wrapper validation error")


def test_wrapper_projects_support_before_building_v6(monkeypatch) -> None:
    calls: list[list[str]] = []
    support_calls: list[dict[str, object]] = []
    finalize_calls: list[int] = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        return SimpleNamespace(returncode=0)

    def fake_support(settings, wall_start):
        support_calls.append(dict(settings))
        return True

    def fake_finalize(settings, wall_start, workspace_returncode):
        finalize_calls.append(workspace_returncode)
        return True

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)
    monkeypatch.setattr(wrapper, "_apply_support_awards", fake_support)
    monkeypatch.setattr(wrapper, "_finalize_report", fake_finalize)
    rc = wrapper.main(
        [
            "--output",
            "out/final-output.jsonl",
            "--report",
            "out/final-report.json",
            "--product-output",
            "out/signalpost.html",
            "--expected-count",
            "100",
            "--max-challenge-requests",
            "2000",
        ]
    )

    assert rc == 0
    assert len(calls) == 2
    assert calls[0][1] == str(wrapper.LEGACY_RUNNER)
    assert calls[1][1] == str(wrapper.V6_BUILDER)
    assert arg_value(calls[0][2:], "--max-challenge-requests") == "1998"
    assert calls[1][-2:] == ["--expect-count", "100"]
    assert len(support_calls) == 1
    assert support_calls[0]["legacy_max_challenge_requests"] == 1998
    assert finalize_calls == [0]


def test_wrapper_stops_before_support_and_v6_after_legacy_failure(monkeypatch) -> None:
    calls: list[list[str]] = []
    support_called = False

    def fake_run(command, **kwargs):
        calls.append(list(command))
        return SimpleNamespace(returncode=7)

    def fake_support(settings, wall_start):
        nonlocal support_called
        support_called = True
        return True

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)
    monkeypatch.setattr(wrapper, "_apply_support_awards", fake_support)
    rc = wrapper.main(
        [
            "--output",
            "out/final.jsonl",
            "--report",
            "out/report.json",
            "--product-output",
            "out/product.html",
        ]
    )

    assert rc == 7
    assert len(calls) == 1
    assert calls[0][1] == str(wrapper.LEGACY_RUNNER)
    assert support_called is False


def test_support_specific_flags_never_leak_to_pinned_v2() -> None:
    prepared, settings = wrapper.prepare_legacy_args(
        [
            "--output",
            "out/final.jsonl",
            "--report",
            "out/report.json",
            "--product-output",
            "out/product.html",
            "--support-registry-timeout=99",
            "--support-lookback-days",
            "180",
            "--support-events-per-company=3",
        ]
    )

    assert settings["support_registry_timeout"] == 99.0
    assert settings["support_lookback_days"] == 180
    assert settings["support_events_per_company"] == 3
    assert not any(arg.startswith("--support-") for arg in prepared)
