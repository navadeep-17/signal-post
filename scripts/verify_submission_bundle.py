#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "submission" / "manifest.json"
MANIFEST_SHA_PATH = ROOT / "submission" / "manifest.sha256"
SUMMARY_PATH = ROOT / "submission" / "final-release-1000-summary.json"

REQUIRED_REPOSITORY_FILES = (
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
    "submission/EMAIL_TEMPLATE.md",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_head() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip()
    return value if len(value) == 40 else None


def read_submission_manifest() -> dict[str, Any]:
    body = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise ValueError("submission/manifest.json must contain a JSON object")
    return body


def validate_repository_bundle(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_REPOSITORY_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required repository file: {relative}")

    if manifest.get("schema_version") != 1:
        errors.append("submission manifest schema_version must be 1")
    if manifest.get("project") != "Signalpost":
        errors.append("submission manifest project must be Signalpost")

    identity = manifest.get("submission_identity") or {}
    if identity.get("production_application_behavior_sha") != "b14ef3c277d8f1512064f865d4028e23dcd8bacf":
        errors.append("unexpected production application behavior SHA")

    release = manifest.get("certified_release") or {}
    if release.get("release_companies") != 1000:
        errors.append("certified release must contain 1000 companies")
    if release.get("overlap_count") != 0:
        errors.append("certified release overlap_count must be zero")
    if release.get("release_manifest_sha256") != "80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26":
        errors.append("unexpected frozen release manifest SHA-256")
    if release.get("aggregate_output_sha256") != "00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2":
        errors.append("unexpected certified aggregate output SHA-256")

    aggregate = release.get("aggregate_artifact") or {}
    if aggregate.get("artifact_digest_sha256") != "8cdaad00c48f1d0af811fb947c97f258fdeb26d8336767f8c8e2db7d7f15e37e":
        errors.append("unexpected certified aggregate artifact digest")

    models = manifest.get("models_and_paid_apis") or {}
    if models.get("llm_models_invoked_by_production_runner") != []:
        errors.append("production runner must declare no LLM models")
    if models.get("paid_apis_invoked_by_production_runner") != []:
        errors.append("production runner must declare no paid APIs")
    if models.get("third_party_api_cost_usd_per_100_policy") != 0.0:
        errors.append("third-party API cost policy must remain $0 per 100")

    if MANIFEST_SHA_PATH.is_file():
        expected = MANIFEST_SHA_PATH.read_text(encoding="utf-8").strip().split()[0]
        actual = sha256_file(MANIFEST_PATH)
        if expected != actual:
            errors.append(f"submission manifest sidecar mismatch: expected {expected}, got {actual}")

    if SUMMARY_PATH.is_file():
        summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        metrics = release.get("metrics") or {}
        expected_pairs = {
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
        for key, expected in expected_pairs.items():
            if summary.get(key) != expected:
                errors.append(f"certified summary mismatch for {key}: expected {expected!r}, got {summary.get(key)!r}")
    return errors


def verify_release_manifest(path: Path, expected_sha: str) -> dict[str, Any]:
    digest = sha256_file(path)
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    orgs: list[str] = []
    parse_errors: list[str] = []
    for line_no, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
            org = str(row.get("organisation_number") or "")
            if len(org) != 9 or not org.isdigit():
                parse_errors.append(f"line {line_no}: invalid organisation_number")
            orgs.append(org)
        except Exception as exc:  # pragma: no cover - diagnostic path
            parse_errors.append(f"line {line_no}: {type(exc).__name__}: {exc}")
    return {
        "path": str(path),
        "sha256": digest,
        "expected_sha256": expected_sha,
        "sha256_matches": digest == expected_sha,
        "rows": len(lines),
        "unique_organisation_numbers": len(set(orgs)),
        "parse_errors": parse_errors,
        "passed": digest == expected_sha and len(lines) == 1000 and len(set(orgs)) == 1000 and not parse_errors,
    }


def verify_aggregate_output(path: Path, expected_sha: str) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "src"))
    from norway_company_agent.output_contract import validate_contract_object

    digest = sha256_file(path)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    orgs = [str(row.get("organisation_number") or "") for row in rows]
    contract_failures = [
        {"organisation_number": row.get("organisation_number"), "errors": errors}
        for row in rows
        if (errors := validate_contract_object(row))
    ]
    completed = sum(1 for row in rows if (row.get("run") or {}).get("terminal_status") == "completed")
    return {
        "path": str(path),
        "sha256": digest,
        "expected_sha256": expected_sha,
        "sha256_matches": digest == expected_sha,
        "rows": len(rows),
        "unique_organisation_numbers": len(set(orgs)),
        "terminal_completed": completed,
        "contract_failures": contract_failures,
        "passed": digest == expected_sha and len(rows) == 1000 and len(set(orgs)) == 1000 and completed == 1000 and not contract_failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the final Signalpost submission bundle and optional certified artifacts.")
    parser.add_argument("--release-manifest", type=Path)
    parser.add_argument("--aggregate-output", type=Path)
    parser.add_argument("--aggregate-zip", type=Path)
    args = parser.parse_args()

    manifest = read_submission_manifest()
    release = manifest["certified_release"]
    errors = validate_repository_bundle(manifest)
    report: dict[str, Any] = {
        "repository_head": repository_head(),
        "production_application_behavior_sha": manifest["submission_identity"]["production_application_behavior_sha"],
        "release_manifest_sha256": release["release_manifest_sha256"],
        "aggregate_output_sha256": release["aggregate_output_sha256"],
        "aggregate_artifact_digest_sha256": release["aggregate_artifact"]["artifact_digest_sha256"],
        "repository_bundle_errors": errors,
    }

    artifact_failures = False
    if args.release_manifest:
        result = verify_release_manifest(args.release_manifest, release["release_manifest_sha256"])
        report["release_manifest_verification"] = result
        artifact_failures = artifact_failures or not result["passed"]
    if args.aggregate_output:
        result = verify_aggregate_output(args.aggregate_output, release["aggregate_output_sha256"])
        report["aggregate_output_verification"] = result
        artifact_failures = artifact_failures or not result["passed"]
    if args.aggregate_zip:
        digest = sha256_file(args.aggregate_zip)
        expected = release["aggregate_artifact"]["artifact_digest_sha256"]
        result = {
            "path": str(args.aggregate_zip),
            "sha256": digest,
            "expected_sha256": expected,
            "passed": digest == expected,
        }
        report["aggregate_zip_verification"] = result
        artifact_failures = artifact_failures or not result["passed"]

    report["passed"] = not errors and not artifact_failures
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
