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
PRODUCT_PATH = SUBMISSION / "signalpost-v2.html"

# These are Git blob identities from the immutable V1 submitted commit. V2 is allowed to
# wrap/project their outputs, but these shared base files must not silently drift.
V1_BASE_BLOBS = {
    "scripts/run_signalpost_final.py": "9be89b9827135b1ed703318e1d189d5d3b8ca604",
    "src/norway_company_agent/output_contract.py": "c163f493017e39252ef200e68d53bcebc12930b4",
}

REQUIRED_FILES = (
    ".gitignore",
    "README.md",
    "SUBMISSION.md",
    "OUTPUT_CONTRACT.md",
    "uv.lock",
    "scripts/run_signalpost_final.py",
    "scripts/run_signalpost_v2.py",
    "scripts/audit_canonical_v2.py",
    "scripts/run_refresh_replay.py",
    "scripts/build_v2_product.py",
    "scripts/build_certified_v2_product.py",
    "scripts/verify_submission_bundle.py",
    "src/norway_company_agent/canonical_projection.py",
    "src/norway_company_agent/v2_registry_projection.py",
    "src/norway_company_agent/first_party_activity.py",
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
    "submission/signalpost-v2.html",
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


def git_blob_sha(path: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "hash-object", path], cwd=ROOT, check=True,
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


def product_report() -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    body = PRODUCT_PATH.read_text(encoding="utf-8")
    required_labels = (
        "Company record",
        "Financials",
        "People & locations",
        "Company website",
        "Hiring & public activity",
    )
    missing_labels = [label for label in required_labels if label not in body]
    if missing_labels:
        errors.append(f"V2 product missing canonical areas: {missing_labels}")
    if len(body.encode("utf-8")) < 1_000_000:
        errors.append("V2 product artifact is unexpectedly small")
    if "Evidence" not in body or "evidence" not in body.casefold():
        errors.append("V2 product does not expose evidence/provenance")
    return {
        "path": str(PRODUCT_PATH.relative_to(ROOT)),
        "bytes": len(body.encode("utf-8")),
        "sha256": sha256_bytes(body.encode("utf-8")),
        "canonical_area_labels_present": not missing_labels,
    }, errors


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
    from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection

    output_rows = read_jsonl_bytes(output_bytes)
    output_orgs = [str(row.get("organisation_number") or "") for row in output_rows]
    completed = sum(1 for row in output_rows if (row.get("run") or {}).get("terminal_status") == "completed")
    contract_failures = [
        {"organisation_number": row.get("organisation_number"), "errors": row_errors}
        for row in output_rows
        if (row_errors := validate_contract_object(row))
    ]
    canonical_failures = []
    canonical_fact_count = 0
    for row in output_rows:
        projected = project_canonical_profile(row)
        canonical_fact_count += len(projected.get("canonical_facts") or [])
        row_errors = validate_canonical_projection(projected)
        if row_errors:
            canonical_failures.append({"organisation_number": row.get("organisation_number"), "errors": row_errors})

    if len(output_rows) != 1000 or len(set(output_orgs)) != 1000:
        errors.append("aggregate output must contain 1000 unique organisation numbers")
    if completed != 1000:
        errors.append(f"aggregate output terminal completed count is {completed}, expected 1000")
    if output_orgs != manifest_orgs:
        errors.append("aggregate output organisation-number order does not match frozen manifest")
    if contract_failures:
        errors.append(f"aggregate output has {len(contract_failures)} contract-invalid rows")
    if canonical_failures:
        errors.append(f"V2 canonical projection has {len(canonical_failures)} invalid rows")

    product, product_errors = product_report()
    errors.extend(product_errors)
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
        "v2_canonical_facts": canonical_fact_count,
        "v2_canonical_failures": canonical_failures,
        "v2_product": product,
    }, errors


def validate_repository_bundle(manifest: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    errors = [f"missing required repository file: {path}" for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    if errors:
        return errors, {}

    if manifest.get("schema_version") != 3:
        errors.append("submission manifest schema_version must be 3 for V2")
    if manifest.get("project") != "Signalpost":
        errors.append("submission manifest project must be Signalpost")

    identity = manifest.get("submission_identity") or {}
    if identity.get("revision") != "v2":
        errors.append("submission identity must declare revision v2")
    if identity.get("v1_pinned_submission_sha") != "60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa":
        errors.append("unexpected immutable V1 submission SHA")
    if identity.get("base_collector_behavior_sha") != "b14ef3c277d8f1512064f865d4028e23dcd8bacf":
        errors.append("unexpected V1 base collector behavior SHA")

    for path, expected_blob in V1_BASE_BLOBS.items():
        actual_blob = git_blob_sha(path)
        if actual_blob != expected_blob:
            errors.append(f"V1 base file drifted: {path} blob {actual_blob!r} != {expected_blob}")

    entrypoints = manifest.get("entrypoints") or {}
    expected_entrypoints = {
        "evaluator_runner": "scripts/run_signalpost_v2.py",
        "base_collector": "scripts/run_signalpost_final.py",
        "canonical_projection": "src/norway_company_agent/canonical_projection.py",
        "canonical_audit": "scripts/audit_canonical_v2.py",
    }
    for key, value in expected_entrypoints.items():
        if entrypoints.get(key) != value:
            errors.append(f"unexpected V2 entrypoint for {key}")

    revision = manifest.get("revision_v2") or {}
    if revision.get("canonical_schema_version") != "signalpost-canonical-v2":
        errors.append("unexpected V2 canonical schema version")
    if revision.get("zero_network_projection") is not True:
        errors.append("V2 canonical projection must be declared zero-network")
    if revision.get("changes_identity_thresholds") is not False:
        errors.append("V2 must not weaken identity thresholds")
    if revision.get("changes_v1_certified_corpus") is not False:
        errors.append("V2 must not change the certified V1 corpus")
    if revision.get("product_surface_generated_from_final_output") is not True:
        errors.append("V2 must declare a data-linked product surface")
    if revision.get("generic_careers_page_counts_as_hiring") is not False:
        errors.append("generic careers pages must not count as hiring")
    audit = revision.get("canonical_audit") or {}
    if audit.get("companies") != 1000 or audit.get("unique_organisation_numbers") != 1000:
        errors.append("V2 canonical audit must cover the immutable certified 1000")
    declared_facts = audit.get("canonical_facts")
    if not isinstance(declared_facts, int) or declared_facts <= 0 or audit.get("validation_errors") != 0:
        errors.append("V2 canonical audit metrics are invalid")
    if audit.get("official_score_claimed") is not False:
        errors.append("V2 manifest must not claim an official Builderr score")

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
        errors.append("certified V1 release identity is inconsistent")
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
    if artifact_report.get("v2_canonical_facts") != declared_facts:
        errors.append("repository-derived V2 canonical fact count does not match manifest declaration")
    return errors, artifact_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the Signalpost V2 submission bundle and immutable V1 evidence baseline.")
    parser.add_argument("--aggregate-zip", type=Path, help="Optional downloaded V1 Actions aggregate ZIP to verify")
    args = parser.parse_args()

    manifest = read_manifest()
    errors, artifacts = validate_repository_bundle(manifest)
    report: dict[str, Any] = {
        "repository_head": repository_head(),
        "revision": manifest["submission_identity"]["revision"],
        "v1_pinned_submission_sha": manifest["submission_identity"]["v1_pinned_submission_sha"],
        "base_collector_behavior_sha": manifest["submission_identity"]["base_collector_behavior_sha"],
        "v1_base_blobs": {path: git_blob_sha(path) for path in V1_BASE_BLOBS},
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
