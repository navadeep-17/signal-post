from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v7_evaluator_addendum_points_to_one_command_wrapper() -> None:
    body = (ROOT / "submission" / "V7_EVALUATOR_PATH.md").read_text(encoding="utf-8")

    assert "scripts/run_signalpost_v7.py" in body
    assert "scripts/run_signalpost_v2.py" in body
    assert "scripts/build_v6_ui.py" in body
    assert "same `--product-output` path" in body
    assert "adds no network requests or third-party API cost" in body
    assert "does not claim an official score" in body


def test_submission_email_recommends_v7_without_relabelling_certified_lineage() -> None:
    body = (ROOT / "submission" / "EMAIL_TEMPLATE.md").read_text(encoding="utf-8")

    assert "Signalpost V7 evaluator/product revision" in body
    assert "uv run python scripts/run_signalpost_v7.py" in body
    assert "preserves the certified V5 evaluator/data runner" in body
    assert "a verified company-owned careers page is a `hiring.careers_page` signal only" in body
    assert "does not establish an active vacancy" in body
    assert "no official score is claimed" in body


def test_machine_readable_manifest_remains_certified_v5_lineage() -> None:
    manifest = json.loads((ROOT / "submission" / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["submission_identity"]["revision"] == "v5"
    assert manifest["entrypoints"]["evaluator_runner"] == "scripts/run_signalpost_v2.py"
    assert manifest["current_revision"]["qualification_policy"]["official_score_claimed"] is False
