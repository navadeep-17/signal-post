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
SMOKE_REPORT = SUBMISSION / "v5-smoke-100-run-report.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_submission_manifest_and_repository_artifacts_are_frozen() -> None:
    body = json.loads(MANIFEST.read_text(encoding="utf-8"))
    release = body["certified_release"]
    metrics = release["metrics"]
    artifacts = release["repository_artifacts"]
    revision_v2 = body["revision_v2"]
    current = body["current_revision"]

    assert body["schema_version"] == 3
    assert body["submission_identity"]["revision"] == "v5"
    assert body["submission_identity"]["v1_pinned_submission_sha"] == "60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa"
    assert body["submission_identity"]["base_collector_behavior_sha"] == "b14ef3c277d8f1512064f865d4028e23dcd8bacf"
    assert body["submission_identity"]["v5_merged_production_sha"] == "a0ca7bb1ab19de5c7c96b2e5e862763c27f8e34b"
    assert body["submission_identity"]["v5_production_wrapper_git_blob"] == "07cdd0f5f1edb6c425ac8b8c9ae90e6357c87643"
    assert body["submission_identity"]["v5_brreg_change_connector_git_blob"] == "9d22bcaf494a356a47985fc731cef6c2e0ecd493"

    assert body["entrypoints"]["evaluator_runner"] == "scripts/run_signalpost_v2.py"
    assert body["entrypoints"]["base_collector"] == "scripts/run_signalpost_final.py"
    assert body["entrypoints"]["canonical_projection"] == "src/norway_company_agent/canonical_projection.py"
    assert body["entrypoints"]["brreg_change_connector"] == "src/norway_company_agent/brreg_changes.py"
    assert body["entrypoints"]["smoke_test_report"] == "submission/v5-smoke-100-run-report.json"

    policy = current["qualification_policy"]
    assert current["canonical_schema_version"] == "signalpost-canonical-v2"
    assert current["synthesis_schema_version"] == "signalpost-synthesis-v1"
    assert policy["official_score_threshold"] == 65
    assert policy["separate_dimension_thresholds"] is False
    assert policy["weights"] == {
        "recall_and_coverage": 50,
        "precision_and_evidence": 30,
        "synthesis": 12,
        "ux": 8,
    }
    assert policy["official_score_claimed"] is False

    smoke = current["fresh_smoke_test"]
    assert smoke["workflow_run_id"] == 36892430561
    assert smoke["companies"] == 100
    assert smoke["overlap"] == 0
    assert smoke["final_objects"] == 100
    assert smoke["observed_conservative_request_charge"] == 1382
    assert smoke["theoretical_conservative_request_ceiling"] == 2000
    assert smoke["third_party_api_cost_usd"] == 0.0
    assert smoke["search_api_requests"] == 0
    assert smoke["passed"] is True

    assert revision_v2["canonical_schema_version"] == "signalpost-canonical-v2"
    assert revision_v2["zero_network_projection"] is True
    assert revision_v2["v2_registry_projection_zero_network"] is True
    assert revision_v2["strict_first_party_activity_projection_zero_network"] is True
    assert revision_v2["changes_identity_thresholds"] is False
    assert revision_v2["changes_v1_certified_corpus"] is False
    assert revision_v2["changes_v1_base_runner_or_output_adapter"] is False
    assert revision_v2["product_surface_generated_from_final_output"] is True
    assert revision_v2["generic_careers_page_counts_as_hiring"] is False
    assert revision_v2["generic_news_index_counts_as_activity"] is False
    assert revision_v2["cross_domain_activity_pages_allowed"] is False
    assert revision_v2["canonical_audit"]["canonical_facts"] == 19951
    assert revision_v2["canonical_audit"]["selected_fact_counts"]["person_role"] == 3932
    assert revision_v2["canonical_audit"]["validation_errors"] == 0
    assert revision_v2["canonical_audit"]["official_score_claimed"] is False

    assert body["runtime"]["server_side_secrets_required"] == []
    assert body["models_and_paid_apis"]["llm_models_invoked_by_production_runner"] == []
    assert body["models_and_paid_apis"]["paid_apis_invoked_by_production_runner"] == []
    assert body["models_and_paid_apis"]["third_party_api_cost_usd_per_100_policy"] == 0.0

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


def test_current_smoke_report_is_submission_ready() -> None:
    body = json.loads(SMOKE_REPORT.read_text(encoding="utf-8"))
    result = body["result"]
    operations = body["operations"]

    assert body["workflow_run_id"] == 36892430561
    assert body["input"]["companies"] == 100
    assert body["input"]["overlap"] == 0
    assert result["expected_count"] == 100
    assert result["final_objects"] == 100
    assert result["unique_organisation_numbers"] is True
    assert result["all_entity_states_terminal"] is True
    assert result["zero_silent_drops"] is True
    assert result["contract_validation_errors"] == 0
    assert result["canonical_validation_errors"] == 0
    assert result["synthesis_validation_errors"] == 0
    assert result["registry_change_integrity_errors"] == 0
    assert result["passed"] is True
    assert operations["observed_conservative_request_charge"] <= 2000
    assert operations["theoretical_conservative_request_ceiling"] <= 2000
    assert operations["wall_runtime_seconds"] <= operations["max_wall_runtime_seconds"]
    assert operations["third_party_api_cost_usd"] == 0.0
    assert operations["search_api_requests"] == 0


def test_v2_compatibility_components_are_present() -> None:
    required = (
        "scripts/run_signalpost_v2.py",
        "scripts/build_v2_product.py",
        "scripts/build_certified_v2_product.py",
        "src/norway_company_agent/canonical_projection.py",
        "src/norway_company_agent/v2_registry_projection.py",
        "src/norway_company_agent/first_party_activity.py",
        "submission/signalpost-v2.html",
        "tests/test_canonical_projection.py",
        "tests/test_v2_registry_mapping.py",
        "tests/test_first_party_activity.py",
        "tests/test_v2_product_artifact.py",
    )
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert missing == []


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


def test_submission_docs_preserve_current_and_compatibility_boundaries() -> None:
    submission = (ROOT / "SUBMISSION.md").read_text(encoding="utf-8")
    email = (SUBMISSION / "EMAIL_TEMPLATE.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    contract = (ROOT / "OUTPUT_CONTRACT.md").read_text(encoding="utf-8")
    requirements = (ROOT / "docs" / "REQUIREMENTS_MATRIX.md").read_text(encoding="utf-8")
    submission_folded = submission.casefold()
    requirements_folded = requirements.casefold()

    assert "scripts/run_signalpost_v2.py" in submission
    assert "--product-output" in submission
    assert "scripts/run_signalpost_v2.py" in readme
    assert "canonical_facts" in contract
    assert "19,951" in submission
    assert "3,932" in submission
    assert "detail url" in submission_folded
    assert "explicit apply/application action" in submission_folded
    assert "explicit publication date" in submission_folded
    assert "strict job-posting facts | **0**" in submission_folded
    assert "strict dated company-update facts | **0**" in submission_folded
    assert "server-side secrets required: **none**" in submission_folded
    assert "contact name: `<contact_name>`" in email.casefold()
    assert "contact email: `<contact_email>`" in email.casefold()
    assert "mailbox deliverability" in submission_folded
    assert "follower" in submission_folded
    assert "generic careers" in submission_folded
    assert "65/100" in submission
    assert "not separate qualification thresholds" in submission_folded
    assert "separate qualification thresholds" in requirements_folded
    assert "21/35" not in submission
    assert "60% weighted external" not in submission
    assert "95% external" not in submission


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
    assert report["revision"] == "v5"
    assert report["repository_bundle_errors"] == []
    assert report["v1_base_blobs"]["scripts/run_signalpost_final.py"] == "9be89b9827135b1ed703318e1d189d5d3b8ca604"
    assert report["v1_base_blobs"]["src/norway_company_agent/output_contract.py"] == "c163f493017e39252ef200e68d53bcebc12930b4"
    assert report["v5_production_blobs"]["scripts/run_signalpost_v2.py"] == "07cdd0f5f1edb6c425ac8b8c9ae90e6357c87643"
    assert report["v5_production_blobs"]["src/norway_company_agent/brreg_changes.py"] == "9d22bcaf494a356a47985fc731cef6c2e0ecd493"
    assert report["repository_artifacts"]["manifest_rows"] == 1000
    assert report["repository_artifacts"]["aggregate_output_rows"] == 1000
    assert report["repository_artifacts"]["terminal_completed"] == 1000
    assert report["repository_artifacts"]["contract_failures"] == []
    assert report["repository_artifacts"]["manifest_output_order_match"] is True
    assert report["repository_artifacts"]["v2_canonical_facts"] == 19951
    assert report["repository_artifacts"]["v2_canonical_failures"] == []
    assert report["repository_artifacts"]["v2_product"]["canonical_area_labels_present"] is True
    assert report["repository_artifacts"]["v5_smoke_report"]["result"]["passed"] is True
