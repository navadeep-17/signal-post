from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXACT_FIELDS = {
    "registered_purpose": ("official_registry_narrative_projection", "/vedtektsfestetFormaal"),
    "registration_date": ("official_registry_live_projection", "/registreringsdatoEnhetsregisteret"),
    "registered_address": ("official_registry_live_projection", "/forretningsadresse"),
    "registered_contact_email": ("official_registry_live_projection", "/epostadresse"),
    "registered_phone": ("official_registry_live_projection", "/telefon"),
    "registered_mobile": ("official_registry_live_projection", "/mobil"),
}


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _available_count(rows: list[dict[str, Any]], field: str) -> int:
    return sum(
        any(
            claim.get("field") == field and claim.get("availability") == "available"
            for claim in row.get("claims") or []
        )
        for row in rows
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    args = parser.parse_args()

    rows = _rows(args.input)
    report = json.loads(args.report.read_text(encoding="utf-8"))
    tracked = ("company_description", *EXACT_FIELDS)
    coverage = {field: _available_count(rows, field) for field in tracked}
    evidence_errors: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    registry_activity_fallback_companies = 0

    for row in rows:
        org = str(row.get("organisation_number") or "")
        evidence = {
            str(item.get("id")): item
            for item in row.get("evidence") or []
            if isinstance(item, dict) and item.get("id")
        }
        company_audit: dict[str, Any] = {"organisation_number": org, "exact_live_claims": {}}
        saw_registry_activity = False
        for claim in row.get("claims") or []:
            if not isinstance(claim, dict) or claim.get("availability") != "available":
                continue
            field = str(claim.get("field") or "")
            signal_type = claim.get("signal_type")
            expected_source_field: str | None = None
            if field == "company_description" and signal_type == "official_registry_narrative_projection":
                expected_source_field = "/aktivitet"
                saw_registry_activity = True
            elif field in EXACT_FIELDS:
                expected_signal_type, expected_source_field = EXACT_FIELDS[field]
                if signal_type != expected_signal_type:
                    evidence_errors.append(
                        {
                            "organisation_number": org,
                            "field": field,
                            "error": f"unexpected signal_type {signal_type!r}",
                        }
                    )
            if expected_source_field is None:
                continue
            if field in {"company_description", "registered_purpose"}:
                text_value = str(claim.get("value") or "").strip()
                if text_value.startswith("[") and text_value.endswith("]"):
                    evidence_errors.append(
                        {
                            "organisation_number": org,
                            "field": field,
                            "error": "narrative leaked Python list syntax",
                        }
                    )

            traces = []
            for evidence_id in claim.get("evidence_ids") or []:
                item = evidence.get(str(evidence_id))
                if item is None:
                    evidence_errors.append(
                        {
                            "organisation_number": org,
                            "field": field,
                            "evidence_id": evidence_id,
                            "error": "missing evidence",
                        }
                    )
                    continue
                expected_url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{org}"
                checks = {
                    "source_class": item.get("source_class") == "official",
                    "source_row_key": str(item.get("source_row_key") or "") == org,
                    "source_field": item.get("source_field") == expected_source_field,
                    "source_url": str(item.get("source_url") or "").rstrip("/") == expected_url,
                }
                for check, passed in checks.items():
                    if not passed:
                        evidence_errors.append(
                            {
                                "organisation_number": org,
                                "field": field,
                                "evidence_id": evidence_id,
                                "error": f"{check} check failed",
                                "actual": item.get(check),
                            }
                        )
                traces.append(
                    {
                        "evidence_id": evidence_id,
                        "source_url": item.get("source_url"),
                        "source_field": item.get("source_field"),
                        "claim_span": item.get("claim_span"),
                    }
                )
            company_audit["exact_live_claims"][field] = {
                "value": claim.get("value"),
                "signal_type": signal_type,
                "evidence": traces,
            }
        registry_activity_fallback_companies += int(saw_registry_activity)
        if company_audit["exact_live_claims"]:
            audit_rows.append(company_audit)

    request_budget = report.get("request_budget") or {}
    source_policy = report.get("source_policy") or {}
    runtime = report.get("runtime") or {}
    operations = {
        "observed_conservative_request_charge": request_budget.get("observed_conservative_challenge_request_charge"),
        "theoretical_conservative_request_ceiling": request_budget.get("theoretical_challenge_request_charge_ceiling"),
        "third_party_cost_usd": source_policy.get("third_party_cost_usd"),
        "search_api_requests": source_policy.get("search_api_requests", 0),
        "wall_runtime_seconds": runtime.get("wall_runtime_seconds"),
    }
    result = {
        "schema_version": "signalpost-phase1-fresh-qualification-v1",
        "companies": len(rows),
        "unique_companies": len({str(row.get("organisation_number") or "") for row in rows}),
        "coverage": coverage,
        "registry_activity_fallback_companies": registry_activity_fallback_companies,
        "evidence_errors": evidence_errors,
        "operations": operations,
    }
    result["passed"] = (
        len(rows) == 100
        and result["unique_companies"] == 100
        and not evidence_errors
        and coverage["company_description"] >= 98
        and registry_activity_fallback_companies >= 70
        and coverage["registered_purpose"] >= 90
        and coverage["registration_date"] >= 98
        and coverage["registered_address"] >= 95
        and (operations["observed_conservative_request_charge"] or 0) <= 2000
        and (operations["theoretical_conservative_request_ceiling"] or 0) <= 2000
        and float(operations["third_party_cost_usd"] or 0.0) == 0.0
        and int(operations["search_api_requests"] or 0) == 0
        and bool(report.get("passed"))
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    with args.audit.open("w", encoding="utf-8") as handle:
        for item in audit_rows:
            handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit("Phase 1 fresh qualification failed")


if __name__ == "__main__":
    main()
