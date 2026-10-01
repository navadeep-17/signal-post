#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(value)
    return rows


def annual_description_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    org = str(profile.get("organisation_number") or "")
    return [
        row
        for row in (profile.get("external_observations") or [])
        if isinstance(row, dict)
        and row.get("signal_type") == "company_profile"
        and row.get("platform") == "brreg"
        and row.get("source_class") == "official_annual_account_copy"
        and str(row.get("organisation_number") or "") == org
        and str(row.get("company_description") or "").strip()
    ]


def annual_workforce_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    org = str(profile.get("organisation_number") or "")
    return [
        row
        for row in (profile.get("external_observations") or [])
        if isinstance(row, dict)
        and row.get("signal_type") == "workforce_snapshot"
        and row.get("source_class") == "official_annual_account_copy"
        and str(row.get("organisation_number") or "") == org
    ]


def audit(profiles: list[dict[str, Any]], outputs: list[dict[str, Any]]) -> dict[str, Any]:
    profiles_by_org = {str(row.get("organisation_number") or ""): row for row in profiles}
    outputs_by_org = {str(row.get("organisation_number") or ""): row for row in outputs}

    description_rows: list[tuple[str, dict[str, Any]]] = []
    shared_report_orgs: set[str] = set()
    for org, profile in profiles_by_org.items():
        descriptions = annual_description_observations(profile)
        workforce = annual_workforce_observations(profile)
        description_rows.extend((org, row) for row in descriptions)
        workforce_keys = {
            (str(row.get("source_url") or ""), str(row.get("content_sha256") or ""))
            for row in workforce
        }
        if any(
            (str(row.get("source_url") or ""), str(row.get("content_sha256") or "")) in workforce_keys
            for row in descriptions
        ):
            shared_report_orgs.add(org)

    description_counts = Counter(org for org, _row in description_rows)
    duplicate_observation_orgs = sorted(org for org, count in description_counts.items() if count > 1)
    observation_orgs = set(description_counts)

    published_orgs: set[str] = set()
    evidence_errors: list[dict[str, str]] = []
    for org, output in outputs_by_org.items():
        evidence_by_id = {
            str(row.get("id") or ""): row
            for row in (output.get("evidence") or [])
            if isinstance(row, dict) and row.get("id")
        }
        for claim in output.get("claims") or []:
            if not isinstance(claim, dict):
                continue
            if claim.get("field") != "company_description":
                continue
            if claim.get("availability") != "available":
                continue
            if claim.get("platform") != "brreg" or claim.get("signal_type") != "company_profile":
                continue
            published_orgs.add(org)
            evidence_ids = [str(value) for value in (claim.get("evidence_ids") or []) if value]
            if not evidence_ids:
                evidence_errors.append({"organisation_number": org, "error": "published annual description has no evidence id"})
                continue
            for evidence_id in evidence_ids:
                item = evidence_by_id.get(evidence_id)
                if not item:
                    evidence_errors.append({"organisation_number": org, "error": f"missing evidence {evidence_id}"})
                    continue
                for field in ("source_url", "retrieved_at", "content_sha256", "claim_span"):
                    if not item.get(field):
                        evidence_errors.append(
                            {"organisation_number": org, "error": f"evidence {evidence_id} missing {field}"}
                        )

    suppressed_orgs = sorted(observation_orgs - published_orgs)
    orphan_published_orgs = sorted(published_orgs - observation_orgs)
    checks = {
        "unique_profile_orgs": len(profiles_by_org) == len(profiles),
        "unique_output_orgs": len(outputs_by_org) == len(outputs),
        "no_duplicate_annual_description_observations": not duplicate_observation_orgs,
        "published_descriptions_have_source_observations": not orphan_published_orgs,
        "published_description_evidence_complete": not evidence_errors,
    }

    return {
        "profiles": len(profiles),
        "outputs": len(outputs),
        "annual_description_observations": len(description_rows),
        "companies_with_annual_description_observation": len(observation_orgs),
        "published_annual_description_claims": len(published_orgs),
        "companies_suppressed_by_stronger_existing_description": len(suppressed_orgs),
        "suppressed_organisation_numbers": suppressed_orgs,
        "companies_reusing_same_report_as_workforce": len(shared_report_orgs),
        "shared_report_organisation_numbers": sorted(shared_report_orgs),
        "duplicate_observation_organisation_numbers": duplicate_observation_orgs,
        "orphan_published_organisation_numbers": orphan_published_orgs,
        "evidence_errors": evidence_errors,
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit V3 annual-report company-description projection")
    parser.add_argument("--profiles", required=True, help="profiles.jsonl produced by run_signalpost_final.py")
    parser.add_argument("--output", required=True, help="final output JSONL produced by run_signalpost_final.py")
    parser.add_argument("--report", help="optional JSON report path")
    args = parser.parse_args()

    report = audit(read_jsonl(Path(args.profiles)), read_jsonl(Path(args.output)))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
