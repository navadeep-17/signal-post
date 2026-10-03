from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v7_evaluator_addendum_remains_as_previous_qualified_path() -> None:
    body = (ROOT / "submission" / "V7_EVALUATOR_PATH.md").read_text(encoding="utf-8")

    assert "scripts/run_signalpost_v7.py" in body
    assert "scripts/run_signalpost_v2.py" in body
    assert "scripts/build_v6_ui.py" in body
    assert "same `--product-output` path" in body
    assert "adds no network requests or third-party API cost" in body
    assert "does not claim an official score" in body


def test_v8_evaluator_addendum_is_batch_size_adaptive() -> None:
    body = (ROOT / "submission" / "V8_EVALUATOR_PATH.md").read_text(encoding="utf-8")

    assert "scripts/run_signalpost_v8.py" in body
    assert "scripts/run_signalpost_v7.py" in body
    assert "derive the exact company count" in body
    assert "Do not hard-code `--expected-count`" in body
    assert "max(2000, 20 × company_count)" in body
    assert "Builderr's evaluator/harness remains authoritative" in body
    assert "No new source, network connector, model, claim type, identity heuristic or publication rule" in body


def test_submission_email_recommends_v8_without_relabelling_certified_lineage() -> None:
    body = (ROOT / "submission" / "EMAIL_TEMPLATE.md").read_text(encoding="utf-8")

    assert "Signalpost V8 evaluator compatibility revision" in body
    assert "uv run python scripts/run_signalpost_v8.py" in body
    assert "hard-coded 100-company assumption" in body
    assert "already-qualified V7 evaluator/product path" in body
    assert "a verified company-owned careers page is a `hiring.careers_page` signal only" in body
    assert "does not establish an active vacancy" in body
    assert "no new official score is claimed" in body


def test_machine_readable_manifest_remains_certified_v5_lineage() -> None:
    manifest = json.loads((ROOT / "submission" / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["submission_identity"]["revision"] == "v5"
    assert manifest["entrypoints"]["evaluator_runner"] == "scripts/run_signalpost_v2.py"
    assert manifest["current_revision"]["qualification_policy"]["official_score_claimed"] is False
