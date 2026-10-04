#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection  # noqa: E402
from norway_company_agent.synthesis import validate_company_synthesis  # noqa: E402

C12_OFFICIAL_SIGNAL_TYPES = {
    "official_registry_live_projection",
    "official_registry_narrative_projection",
}
MATERIAL_EXTERNAL_FIELDS = {
    "external.profile_handle",
    "external.company_update",
    "external.job_posting",
    "external.careers_page",
}
EXPECTED_LIVE_PATHS = {
    "industry": "/naeringskode1",
    "municipality_number": "/forretningsadresse/kommunenummer",
    "bankrupt": "/konkurs",
    "liquidating": "/underAvvikling",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_mapping_errors(row: dict[str, Any], claim: dict[str, Any]) -> list[str]:
    org = str(row.get("organisation_number") or "")
    evidence_by_id = {str(item.get("id")): item for item in (row.get("evidence") or []) if item.get("id")}
    errors: list[str] = []
    ids = [str(value) for value in (claim.get("evidence_ids") or []) if value]
    if not ids:
        return [f"{org}:{claim.get('field')}:missing_evidence_id"]
    for evidence_id in ids:
        item = evidence_by_id.get(evidence_id)
        if not item:
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:missing_evidence")
            continue
        if item.get("source_class") != "official":
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:not_official")
        if str(item.get("source_row_key") or "") != org:
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:wrong_source_row_key")
        if len(str(item.get("content_sha256") or "")) != 64:
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:missing_exact_hash")
        if not item.get("retrieved_at"):
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:missing_retrieved_at")
        if not str(item.get("source_url") or "").startswith(("http://", "https://")):
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:missing_source_url")
        source_field = str(item.get("source_field") or "")
        if not source_field.startswith("/"):
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:missing_source_field")
        expected = EXPECTED_LIVE_PATHS.get(str(claim.get("field") or ""))
        if expected and source_field != expected:
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:wrong_source_field={source_field}")
    return errors


def external_evidence_errors(row: dict[str, Any], claim: dict[str, Any]) -> list[str]:
    org = str(row.get("organisation_number") or "")
    evidence_by_id = {str(item.get("id")): item for item in (row.get("evidence") or []) if item.get("id")}
    errors: list[str] = []
    for evidence_id in claim.get("evidence_ids") or []:
        item = evidence_by_id.get(str(evidence_id))
        if not item:
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:missing_evidence")
            continue
        if item.get("source_class") != "company_owned":
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:not_company_owned")
        if len(str(item.get("content_sha256") or "")) != 64:
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:missing_hash")
        if not item.get("retrieved_at"):
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:missing_retrieved_at")
        if not str(item.get("source_url") or "").startswith(("http://", "https://")):
            errors.append(f"{org}:{claim.get('field')}:{evidence_id}:missing_source_url")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize C12 M1-M4 transfer on a qualification cohort.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--selection-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-report", required=True)
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--product", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--repository-sha", required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    selection_path = Path(args.selection_report)
    output_path = Path(args.output)
    run_report_path = Path(args.run_report)
    profiles_path = Path(args.profiles)
    product_path = Path(args.product)

    inputs = read_jsonl(input_path)
    rows = read_jsonl(output_path)
    profiles = read_jsonl(profiles_path)
    report = read_json(run_report_path)
    selection = read_json(selection_path)
    profile_by_org = {str(row.get("organisation_number") or ""): row for row in profiles}

    if len(inputs) != 100 or len(rows) != 100:
        raise AssertionError((len(inputs), len(rows)))
    if len({str(row.get("organisation_number") or "") for row in rows}) != 100:
        raise AssertionError("duplicate organisation numbers")
    if selection.get("overlap_count") != 0:
        raise AssertionError(selection)
    if report.get("passed") is not True:
        raise AssertionError(report)
    if report.get("contract_errors"):
        raise AssertionError(report["contract_errors"][:5])
    if report.get("change_errors"):
        raise AssertionError(report["change_errors"][:5])
    if report.get("budget_errors"):
        raise AssertionError(report["budget_errors"][:5])
    if float((report.get("source_policy") or {}).get("third_party_cost_usd") or 0) != 0.0:
        raise AssertionError("third-party API cost must remain zero")
    if int((report.get("source_policy") or {}).get("search_api_requests") or 0) != 0:
        raise AssertionError("search API requests must remain zero")

    canonical_errors: list[str] = []
    synthesis_errors: list[str] = []
    decision_briefs = 0
    verified_websites = 0
    official_state = defaultdict(Counter)
    official_mapping_errors: list[str] = []
    external_mapping_errors: list[str] = []
    external_claims = Counter()
    external_companies: dict[str, set[str]] = defaultdict(set)
    audit_rows: list[dict[str, Any]] = []
    live_registry_available = 0

    for row in rows:
        org = str(row.get("organisation_number") or "")
        canonical = project_canonical_profile(row)
        canonical_errors.extend(f"{org}:{error}" for error in validate_canonical_projection(canonical))
        synthesis_errors.extend(f"{org}:{error}" for error in validate_company_synthesis(row))
        decision_briefs += int(bool(((row.get("synthesis") or {}).get("decision_brief") or {})))

        profile = profile_by_org.get(org) or {}
        profile_evidence = profile.get("evidence") or {}
        registry_live = profile_evidence.get("registry_live") or {}
        live_registry_available += int(registry_live.get("status") == "available")
        website = profile_evidence.get("website") or {}
        website_value = website.get("value") or {}
        website_identity = website_value.get("identity_assessment") or {}
        if website.get("status") == "available" and website_identity.get("publishable"):
            verified_websites += 1

        row_material: list[dict[str, Any]] = []
        for claim in row.get("claims") or []:
            field = str(claim.get("field") or "")
            availability = str(claim.get("availability") or "")
            signal_type = str(claim.get("signal_type") or "")
            if signal_type in C12_OFFICIAL_SIGNAL_TYPES:
                official_state[field][availability] += 1
                official_mapping_errors.extend(evidence_mapping_errors(row, claim))
            if field in MATERIAL_EXTERNAL_FIELDS and availability == "available":
                external_claims[field] += 1
                external_companies[field].add(org)
                external_mapping_errors.extend(external_evidence_errors(row, claim))
                row_material.append(
                    {
                        "field": field,
                        "value": claim.get("value"),
                        "confidence": claim.get("confidence"),
                        "evidence_ids": claim.get("evidence_ids"),
                    }
                )

        if row_material:
            audit_rows.append(
                {
                    "organisation_number": org,
                    "name": profile.get("name"),
                    "municipality": profile.get("municipality"),
                    "verified_website": website_value.get("final_url") or website.get("source_url"),
                    "website_identity": website_identity,
                    "material_external_claims": row_material,
                }
            )

    if canonical_errors:
        raise AssertionError(canonical_errors[:5])
    if synthesis_errors:
        raise AssertionError(synthesis_errors[:5])
    if official_mapping_errors:
        raise AssertionError(official_mapping_errors[:10])
    if external_mapping_errors:
        raise AssertionError(external_mapping_errors[:10])

    summary = {
        "schema_version": "signalpost-c12-m5-combined-measurement-v1",
        "repository_sha": args.repository_sha,
        "cohort": {
            "companies": len(rows),
            "unique_organisation_numbers": len({str(row.get("organisation_number") or "") for row in rows}),
            "terminal_completed": sum((row.get("run") or {}).get("terminal_status") == "completed" for row in rows),
            "selection_overlap_count": selection.get("overlap_count"),
            "selection_seed": selection.get("seed"),
            "excluded_rows": selection.get("excluded_rows"),
            "input_sha256": sha256(input_path),
        },
        "c12_m1_official_evidence": {
            "registry_live_available_companies": live_registry_available,
            "claim_states_by_field": {field: dict(counter) for field, counter in sorted(official_state.items())},
            "exact_evidence_mapping_errors": len(official_mapping_errors),
        },
        "c12_m2_m3_m4_external_recall": {
            "verified_website_companies": verified_websites,
            "claim_counts": dict(sorted(external_claims.items())),
            "company_counts": {field: len(orgs) for field, orgs in sorted(external_companies.items())},
            "companies_with_any_material_external_claim": len({org for orgs in external_companies.values() for org in orgs}),
            "company_owned_evidence_mapping_errors": len(external_mapping_errors),
        },
        "quality": {
            "canonical_validation_errors": len(canonical_errors),
            "synthesis_validation_errors": len(synthesis_errors),
            "decision_brief_companies": decision_briefs,
            "contract_errors": len(report.get("contract_errors") or []),
            "change_errors": len(report.get("change_errors") or []),
            "budget_errors": len(report.get("budget_errors") or []),
        },
        "operations": {
            "observed_logical_requests": (report.get("request_budget") or {}).get("observed_logical_requests"),
            "observed_conservative_request_charge": (report.get("request_budget") or {}).get("observed_conservative_challenge_request_charge"),
            "theoretical_conservative_request_ceiling": (report.get("request_budget") or {}).get("theoretical_challenge_request_charge_ceiling"),
            "wall_runtime_seconds": (report.get("runtime") or {}).get("wall_runtime_seconds"),
            "third_party_api_cost_usd": (report.get("source_policy") or {}).get("third_party_cost_usd"),
            "search_api_requests": (report.get("source_policy") or {}).get("search_api_requests"),
        },
        "artifacts": {
            "output_sha256": sha256(output_path),
            "run_report_sha256": sha256(run_report_path),
            "profiles_sha256": sha256(profiles_path),
            "product_sha256": sha256(product_path),
            "product_bytes": product_path.stat().st_size,
        },
        "passed": True,
    }

    audit_path = Path(args.audit)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in audit_rows),
        encoding="utf-8",
    )
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
