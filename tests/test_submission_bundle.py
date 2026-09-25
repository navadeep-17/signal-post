from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"
MANIFEST = SUBMISSION / "manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_submission_manifest_and_repository_artifacts_are_frozen() -> None:
    body = json.loads(MANIFEST.read_text(encoding="utf-8"))
    release = body["certified_release"]
    metrics = release["metrics"]
    artifacts = release["repository_artifacts"]
    revision = body["revision_v2"]

    assert body["schema_version"] == 3
    assert body["submission_identity"]["revision"] == "v2"
    assert body["submission_identity"]["v1_pinned_submission_sha"] == "60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa"
    assert body["submission_identity"]["base_collector_behavior_sha"] == "b14ef3c277d8f1512064f865d4028e23dcd8bacf"
    assert body["entrypoints"]["evaluator_runner"] == "scripts/run_signalpost_v2.py"
    assert body["entrypoints"]["base_collector"] == "scripts/run_signalpost_final.py"
    assert body["runtime"]["server_side_secrets_required"] == []
    assert revision["canonical_schema_version"] == "signalpost-canonical-v2"
    assert revision["zero_network_projection"] is True
    assert revision["changes_identity_thresholds"] is False
    assert revision["changes_v1_certified_corpus"] is False
    assert revision["product_surface_generated_from_final_output"] is True
    assert revision["generic_careers_page_counts_as_hiring"] is False
    assert revision["canonical_audit"]["canonical_facts"] == 19951
    assert revision["canonical_audit"]["selected_fact_counts"]["person_role"] == 3932
    assert revision["canonical_audit"]["validation_errors"] == 0
    assert revision["canonical_audit"]["official_score_claimed"] is False

    assert release["release_companies"] == 1000
    assert release["overlap_count"] == 0
    assert release["release_manifest_sha256"] == "80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26"
    assert release["aggregate_output_sha256"] == "00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2"
    assert release["aggregate_artifact"]["artifact_digest_sha256"] == "8cdaad00c48f1d0af811fb947c97f258fdeb26d8336767f8c8e2db7d7f15e37e"
    assert artifacts["aggregate_output_gzip_sha256"] == "7c9e7e822d2ad0fa5a2809ae5a092c9072eb0eed03899b190f62320a5f0c2bc1"
    assert metrics["terminal_completed"] == 1000
    assert metrics["contract_validation_errors"] == 0
    assert metrics["structural_request_ceiling_per_100"] == 2000
    assert metrics["third_party_api_cost_usd"] == 0.0


def test_submission_manifest_sidecar_matches_bytes() -> None:
    expected = (SUBMISSION / "manifest.sha256").read_text(encoding="utf-8").split()[0]
    assert _sha256(MANIFEST) == expected


def test_committed_certified_manifest_and_output_hashes_match() -> None:
    body = json.loads(MANIFEST.read_text(encoding="utf-8"))
    release = body["certified_release"]
    release_manifest = SUBMISSION / "final-release-1000.jsonl"
    output_gz = SUBMISSION / "final-release-1000-output.jsonl.gz"

    assert _sha256(release_manifest) == release["release_manifest_sha256"]
    assert _sha256(output_gz) == release["repository_artifacts"]["aggregate_output_gzip_sha256"]
    assert hashlib.sha256(gzip.decompress(output_gz.read_bytes())).hexdigest() == release["aggregate_output_sha256"]


def test_submission_docs_preserve_v2_and_claim_boundaries() -> None:
    submission = (ROOT / "SUBMISSION.md").read_text(encoding="utf-8")
    email = (SUBMISSION / "EMAIL_TEMPLATE.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    contract = (ROOT / "OUTPUT_CONTRACT.md").read_text(encoding="utf-8")
    submission_folded = submission.casefold()

    assert "scripts/run_signalpost_v2.py" in submission
    assert "--product-output" in submission
    assert "scripts/run_signalpost_v2.py" in readme
    assert "canonical_facts" in contract
    assert "server-side secrets required: **none**" in submission_folded
    assert "contact name: `<contact_name>`" in email.casefold()
    assert "contact email: `<contact_email>`" in email.casefold()
    assert "mailbox deliverability" in submission_folded
    assert "follower" in submission_folded
    assert "generic careers page" in submission_folded


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
    assert report["revision"] == "v2"
    assert report["repository_bundle_errors"] == []
    assert report["repository_artifacts"]["manifest_rows"] == 1000
    assert report["repository_artifacts"]["aggregate_output_rows"] == 1000
    assert report["repository_artifacts"]["terminal_completed"] == 1000
    assert report["repository_artifacts"]["contract_failures"] == []
    assert report["repository_artifacts"]["manifest_output_order_match"] is True
    assert report["repository_artifacts"]["v2_canonical_facts"] == 19951
    assert report["repository_artifacts"]["v2_canonical_failures"] == []
