from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "submission" / "manifest.json"


def test_submission_manifest_is_frozen_and_self_consistent() -> None:
    body = json.loads(MANIFEST.read_text(encoding="utf-8"))
    release = body["certified_release"]
    metrics = release["metrics"]

    assert body["submission_identity"]["production_application_behavior_sha"] == "b14ef3c277d8f1512064f865d4028e23dcd8bacf"
    assert release["release_companies"] == 1000
    assert release["overlap_count"] == 0
    assert release["release_manifest_sha256"] == "80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26"
    assert release["aggregate_output_sha256"] == "00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2"
    assert release["aggregate_artifact"]["artifact_digest_sha256"] == "8cdaad00c48f1d0af811fb947c97f258fdeb26d8336767f8c8e2db7d7f15e37e"
    assert metrics["terminal_completed"] == 1000
    assert metrics["contract_validation_errors"] == 0
    assert metrics["runner_contract_errors"] == 0
    assert metrics["change_errors"] == 0
    assert metrics["structural_request_ceiling_per_100"] == 2000
    assert metrics["third_party_api_cost_usd"] == 0.0
    assert body["models_and_paid_apis"]["llm_models_invoked_by_production_runner"] == []
    assert body["models_and_paid_apis"]["paid_apis_invoked_by_production_runner"] == []


def test_submission_manifest_sidecar_matches_bytes() -> None:
    digest = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    expected = (ROOT / "submission" / "manifest.sha256").read_text(encoding="utf-8").split()[0]
    assert digest == expected


def test_submission_docs_preserve_claim_boundaries() -> None:
    submission = (ROOT / "SUBMISSION.md").read_text(encoding="utf-8")
    rights = (ROOT / "docs" / "SUBMISSION_SOURCE_RIGHTS.md").read_text(encoding="utf-8")
    combined = submission + "\n" + rights

    assert "does **not** claim that Builderr's hidden weighted external recall" in submission
    assert "production runner invokes **no LLM and no sentiment model**" in rights
    assert "zero requests to social platforms" in rights
    assert "mailbox deliverability" in combined
    assert "follower" in combined
    assert "No blanket content-reuse licence is assumed" in rights


def test_repository_only_submission_verifier_passes() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/verify_submission_bundle.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(completed.stdout)
    assert report["passed"] is True
    assert report["repository_bundle_errors"] == []
