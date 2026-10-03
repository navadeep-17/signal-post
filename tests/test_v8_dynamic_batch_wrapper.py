from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_signalpost_v8 as wrapper  # noqa: E402


def write_batch(path: Path, count: int) -> None:
    rows = [
        {"organisation_number": str(900_000_000 + index)}
        for index in range(count)
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def arg_value(args: list[str], flag: str) -> str | None:
    prefix = flag + "="
    for index, arg in enumerate(args):
        if arg.startswith(prefix):
            return arg[len(prefix) :]
        if arg == flag and index + 1 < len(args):
            return args[index + 1]
    return None


def test_100_company_smoke_settings_remain_unchanged(tmp_path: Path) -> None:
    batch = tmp_path / "batch.jsonl"
    write_batch(batch, 100)

    prepared, settings = wrapper.prepare_evaluator_args([
        "--organisations",
        str(batch),
        "--output",
        "out/final.jsonl",
        "--product-output",
        "out/product.html",
    ])

    assert settings == {
        "expected_count": 100,
        "max_challenge_requests": 2000,
        "max_wall_runtime_seconds": 2400,
    }
    assert arg_value(prepared, "--expected-count") == "100"
    assert arg_value(prepared, "--max-challenge-requests") == "2000"
    assert arg_value(prepared, "--max-wall-runtime-seconds") == "2400"


def test_1200_company_batch_scales_without_hard_coded_100(tmp_path: Path) -> None:
    batch = tmp_path / "batch.jsonl"
    write_batch(batch, 1200)

    prepared, settings = wrapper.prepare_evaluator_args([
        "--organisations=" + str(batch),
        "--output",
        "out/final.jsonl",
        "--product-output",
        "out/product.html",
    ])

    assert settings == {
        "expected_count": 1200,
        "max_challenge_requests": 24000,
        "max_wall_runtime_seconds": 3600,
    }
    assert arg_value(prepared, "--expected-count") == "1200"
    assert arg_value(prepared, "--max-challenge-requests") == "24000"
    assert arg_value(prepared, "--max-wall-runtime-seconds") == "3600"


def test_arbitrary_batch_sizes_are_derived_from_supplied_file(tmp_path: Path) -> None:
    for count in (1, 17, 250, 1000, 1350):
        batch = tmp_path / f"batch-{count}.jsonl"
        write_batch(batch, count)
        prepared, settings = wrapper.prepare_evaluator_args([
            "--organisations",
            str(batch),
        ])
        assert settings["expected_count"] == count
        assert arg_value(prepared, "--expected-count") == str(count)
        assert settings["max_challenge_requests"] == max(2000, count * 20)
        assert settings["max_wall_runtime_seconds"] == max(2400, count * 3)


def test_explicit_expected_count_must_match_input(tmp_path: Path) -> None:
    batch = tmp_path / "batch.jsonl"
    write_batch(batch, 1200)

    try:
        wrapper.prepare_evaluator_args([
            "--organisations",
            str(batch),
            "--expected-count",
            "100",
        ])
    except ValueError as exc:
        assert "does not match the supplied evaluator batch (1200)" in str(exc)
    else:
        raise AssertionError("expected mismatched evaluator count to be rejected")


def test_explicit_resource_limits_are_preserved(tmp_path: Path) -> None:
    batch = tmp_path / "batch.jsonl"
    write_batch(batch, 250)

    prepared, settings = wrapper.prepare_evaluator_args([
        "--organisations",
        str(batch),
        "--max-challenge-requests=7777",
        "--max-wall-runtime-seconds",
        "5555",
    ])

    assert settings["max_challenge_requests"] == 7777
    assert settings["max_wall_runtime_seconds"] == 5555
    assert arg_value(prepared, "--max-challenge-requests") == "7777"
    assert arg_value(prepared, "--max-wall-runtime-seconds") == "5555"


def test_main_delegates_once_to_v7_with_derived_settings(tmp_path: Path, monkeypatch) -> None:
    batch = tmp_path / "batch.jsonl"
    write_batch(batch, 1200)
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)
    rc = wrapper.main([
        "--organisations",
        str(batch),
        "--output",
        "out/final.jsonl",
        "--product-output",
        "out/product.html",
    ])

    assert rc == 0
    assert len(calls) == 1
    assert calls[0][0] == sys.executable
    assert calls[0][1] == str(wrapper.V7_RUNNER)
    forwarded = calls[0][2:]
    assert arg_value(forwarded, "--expected-count") == "1200"
    assert arg_value(forwarded, "--max-challenge-requests") == "24000"
    assert arg_value(forwarded, "--max-wall-runtime-seconds") == "3600"
