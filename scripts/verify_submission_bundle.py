#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"
MANIFEST_PATH = SUBMISSION / "manifest.json"
MANIFEST_SHA_PATH = SUBMISSION / "manifest.sha256"
RELEASE_MANIFEST_PATH = SUBMISSION / "final-release-1000.jsonl"
RELEASE_MANIFEST_SHA_PATH = SUBMISSION / "final-release-1000.sha256"
OUTPUT_GZ_PATH = SUBMISSION / "final-release-1000-output.jsonl.gz"
OUTPUT_SHA_PATH = SUBMISSION / "final-release-1000-output.sha256"
OUTPUT_GZ_SHA_PATH = SUBMISSION / "final-release-1000-output.jsonl.gz.sha256"
SUMMARY_PATH = SUBMISSION / "final-release-1000-summary.json"

REQUIRED_FILES = (
    ".gitignore",
    "README.md",
    "SUBMISSION.md",
    "OUTPUT_CONTRACT.md",
    "uv.lock",
    "scripts/run_signalpost_final.py",
    "scripts/run_refresh_replay.py",
    "scripts/build_submission_prototype.py",
    "scripts/verify_submission_bundle.py",
    "docs/SUBMISSION_SOURCE_RIGHTS.md",
    "docs/FINAL_RELEASE_1000_AUDIT.md",
    "docs/REQUIREMENTS_MATRIX.md",
    "submission/manifest.json",
    "submission/manifest.sha256",
    "submission/final-release-1000-summary.json",
    "submission/final-release-1000.jsonl",
    "submission/final-release-1000.sha256",
    "submission/final-release-1000-output.jsonl.gz",
    "submission/final-release-1000-output.sha256",
    "submission/final-release-1000-output.jsonl.gz.sha256",
    "submission/EMAIL_TEMPLATE.md",
)


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sidecar_sha(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip().split()[0]


def repository_head() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip()
    return value if len(value) == 40 else None


def read_manifest() -> dict[str, Any]:
    body = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise ValueError("submission/manifest.json must contain an object")
    return body


def read_jsonl_bytes(body: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(body.decode("utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        row = json.loads(raw)
        if not isinstance(row, dict):
            raise ValueError(f"line {line_no} is not an object")
        rows.append(row)
    return rows


def repository_artifact_report(manifest: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    release = manifest.get("certified_release") or {}

    manifest_bytes = RELEASE_MANIFEST_PATH.read_bytes()
    manifest_digest = sha256_bytes(manifest_bytes)
    expected_manifest = str(release.get("release_manifest_sha256") or "")
    if manifest_digest != expected_manifest:
        errors.append(f"release manifest SHA mismatch: {manifest_digest}")
    if sidecar_sha(RELEASE_MANIFEST_SHA_PATH) != expected_manifest:
        errors.append("release manifest sidecar mismatch")
    manifest_rows = read_jsonl_bytes(manifest_bytes)
    manifest_orgs = [str(row.get("organisation_number") or "") for row in manifest_rows]
    if len(manifest_rows) != 1000 or len(set(manifest_orgs)) != 1000:
        errors.append("release manifest must contain 1000 unique organisation numbers")

    gzip_digest = sha256_file(OUTPUT_GZ_PATH)
    repo_artifacts = release.get("repository_artifacts") or {}
    expected_gzip = str(repo_artifacts.get("aggregate_output_gzip_sha256") or "")
    if gzip_digest != expected_gzip:
        errors.append(f"compressed output SHA mismatch: {gzip_digest}")
    if sidecar_sha(OUTPUT_GZ_SHA_PATH) != expected_gzip:
        errors.append("compressed output sidecar mismatch")

    output_bytes = gzip.decompress(OUTPUT_GZ_PATH.read_bytes())
    output_digest = sha256_bytes(output_bytes)
    expected_output = str(release.get("aggregate_output_sha256") or "")
    if output_digest != expected_output:
        errors.append(f"aggregate output SHA mismatch: {output_digest}")
    if sidecar_sha(OUTPUT_SHA_PATH) != expected_output:
        errors.append("aggregate output sidecar mismatch")

    sys.path.insert(0, str(ROOT / "src"))
    from norway_company_agent.output_contract import validate_contract_object

    output_rows = read_jsonl_bytes(output_bytes)
    output_orgs = [str(row.get("organisation_number") or "") for row in output_rows]
    completed = sum(1 for row in output_rows if (row.get("run") or {}).get("terminal_status") == "completed")
    contract_failures = [
        {"organisation_number": row.get("organisation_number"), "errors": row_errors}
        for row in output_rows
        if (row_errors := validate_contract_object(row))
    ]
    if len(output_rows) != 1000 or len(set(output_orgs)) != 1000:
        errors.append("aggregate output must contain 1000 unique organisation numbers")
    if completed != 1000:
        errors.append(f"aggregate output terminal completed count is {completed}, expected 1000")
    if output_orgs != manifest_orgs:
        errors.append("aggregate output organisation-number order does not match frozen manifest")
    if contract_failures:
        errors.append(f"aggregate output has {len(contract_failures)} contract-invalid rows")

    return {
        "manifest_sha256": manifest_digest,
        "manifest_rows": len(manifest_rows),
        "aggregate_output_gzip_sha256": gzip_digest,
        "aggregate_output_sha256": output_digest,
        "aggregate_output_rows": len(output_rows),
        "unique_organisation_numbers": len(set(output_orgs)),
        "terminal_completed": completed,
        "contract_failures": contract_failures,
        "manifest_output_order_match": output_orgs == manifest_orgs,
    }, errors


def validate_repository_bundle(manifest: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    errors = [f"missing required repository file: {path}" for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    if errors:
        return errors, {}

    if manifest.get("schema_version") != 2:
        errors.append("submission manifest schema_version must be 2")
    if manifest.get("project") != "Signalpost":
        errors.append("submission manifest project must be Signalpost")

    identity = manifest.get("submission_identity") or {}
    if identity.get("production_application_behavior_sha") != "b14ef3c277d8f1512064f865d4028e23dcd8bacf":
        errors.append("unexpected production application behavior SHA")

    runtime = manifest.get("runtime") or {}
    if runtime.get("server_side_secrets_required") != []:
        errors.append("production submission must explicitly declare no required server-side secrets")

    models = manifest.get("models_and_paid_apis") or {}
    if models.get("llm_models_invoked_by_production_runner") != []:
        errors.append("production runner must declare no LLM models")
    if models.get("paid_apis_invoked_by_production_runner") != []:
        errors.append("production runner must declare no paid APIs")
    if models.get("third_party_api_cost_usd_per_100_policy") != 0.0:
        errors.append("third-party API cost policy must remain $0 per 100")

    release = manifest.get("certified_release") or {}
    if release.get("release_companies") != 1000 or release.get("overlap_count") != 0:
        errors.append("certified release identity is inconsistent")
    if release.get("release_manifest_sha256") != "80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26":
        errors.append("unexpected release manifest SHA-256")
    if release.get("aggregate_output_sha256") != "00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2":
        errors.append("unexpected aggregate output SHA-256")
    aggregate = release.get("aggregate_artifact") or {}
    if aggregate.get("artifact_digest_sha256") != "8cdaad00c48f1d0af811fb947c97f258fdeb26d8336767f8c8e2db7d7f15e37e":
        errors.append("unexpected Actions aggregate artifact digest")

    if sidecar_sha(MANIFEST_SHA_PATH) != sha256_file(MANIFEST_PATH):
        errors.append("submission manifest sidecar mismatch")

    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    metrics = release.get("metrics") or {}
    expected = {
        "companies": 1000,
        "unique_organisations": 1000,
        "terminal_completed": 1000,
        "claims": metrics.get("claims"),
        "evidence": metrics.get("deduplicated_evidence_records"),
        "contract_validation_errors": 0,
        "third_party_cost_usd": 0.0,
        "search_api_requests": 0,
        "all_chunks_passed": True,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            errors.append(f"certified summary mismatch for {key}: {summary.get(key)!r} != {value!r}")

    artifact_report, artifact_errors = repository_artifact_report(manifest)
    errors.extend(artifact_errors)
    return errors, artifact_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the final Signalpost submission bundle.")
    parser.add_argument("--aggregate-zip", type=Path, help="Optional downloaded Actions aggregate ZIP to verify")
    args = parser.parse_args()

    manifest = read_manifest()
    errors, artifacts = validate_repository_bundle(manifest)
    report: dict[str, Any] = {
        "repository_head": repository_head(),
        "production_application_behavior_sha": manifest["submission_identity"]["production_application_behavior_sha"],
        "repository_artifacts": artifacts,
        "repository_bundle_errors": errors,
    }

    if args.aggregate_zip:
        expected = manifest["certified_release"]["aggregate_artifact"]["artifact_digest_sha256"]
        actual = sha256_file(args.aggregate_zip)
        report["actions_aggregate_zip"] = {"sha256": actual, "expected_sha256": expected, "passed": actual == expected}
        if actual != expected:
            errors.append("Actions aggregate ZIP digest mismatch")

    report["passed"] = not errors
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
