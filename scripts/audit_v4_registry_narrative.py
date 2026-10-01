#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import (  # noqa: E402
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.registry_narrative import OWN_SIGNAL_TYPE  # noqa: E402
from norway_company_agent.synthesis import (  # noqa: E402
    build_company_synthesis,
    validate_company_synthesis,
)
from norway_company_agent.v2_registry_projection import project_v2_registry_claims  # noqa: E402


def _read_jsonl(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError(f"Expected object rows in {path}")
                rows.append(item)
    return rows


def _index(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        org = str(row.get("organisation_number") or "")
        if not org:
            raise ValueError(f"{label} row missing organisation_number")
        if org in result:
            raise ValueError(f"Duplicate {label} organisation_number: {org}")
        result[org] = row
    return result


def _available_claims(row: dict[str, Any], field: str) -> list[dict[str, Any]]:
    return [
        claim
        for claim in (row.get("claims") or [])
        if isinstance(claim, dict)
        and claim.get("field") == field
        and claim.get("availability") == "available"
        and str(claim.get("value") or "").strip()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline audit of zero-network BRREG narrative projection over archived certified profiles."
    )
    parser.add_argument("--profiles", nargs="+", required=True)
    parser.add_argument("--contracts", nargs="+", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--samples", required=True)
    args = parser.parse_args()

    profiles = _index(_read_jsonl([Path(value) for value in args.profiles]), "profile")
    contracts = _index(_read_jsonl([Path(value) for value in args.contracts]), "contract")
    if set(profiles) != set(contracts):
        missing_profiles = sorted(set(contracts) - set(profiles))
        missing_contracts = sorted(set(profiles) - set(contracts))
        raise SystemExit(
            "Profile/contract organisation sets differ: "
            f"missing_profiles={missing_profiles[:10]} missing_contracts={missing_contracts[:10]}"
        )

    description_before = 0
    description_after = 0
    registry_description = 0
    stronger_description_preserved = 0
    registered_purpose = 0
    canonical_description = 0
    idempotence_errors: list[str] = []
    contract_errors: list[dict[str, str]] = []
    canonical_errors: list[dict[str, str]] = []
    synthesis_errors: list[dict[str, str]] = []
    evidence_errors: list[dict[str, str]] = []
    sample_rows: list[dict[str, Any]] = []

    for org in sorted(profiles):
        profile = profiles[org]
        base = contracts[org]
        before = _available_claims(base, "company_description")
        description_before += int(bool(before))

        projected = project_v2_registry_claims(base, profile)
        rerun = project_v2_registry_claims(projected, profile)
        if rerun != projected:
            idempotence_errors.append(org)

        descriptions = _available_claims(projected, "company_description")
        purposes = _available_claims(projected, "registered_purpose")
        description_after += int(bool(descriptions))
        registered_purpose += int(bool(purposes))
        own_descriptions = [claim for claim in descriptions if claim.get("signal_type") == OWN_SIGNAL_TYPE]
        registry_description += int(bool(own_descriptions))
        if before:
            stronger_description_preserved += int(
                any(
                    claim.get("value") == before[0].get("value")
                    and claim.get("signal_type") != OWN_SIGNAL_TYPE
                    for claim in descriptions
                )
            )

        evidence_by_id = {
            str(item.get("id")): item
            for item in (projected.get("evidence") or [])
            if isinstance(item, dict) and item.get("id")
        }
        for claim in own_descriptions + purposes:
            for evidence_id in claim.get("evidence_ids") or []:
                item = evidence_by_id.get(str(evidence_id))
                if item is None:
                    evidence_errors.append({"organisation_number": org, "error": f"missing evidence {evidence_id}"})
                    continue
                if item.get("source_class") != "official":
                    evidence_errors.append({"organisation_number": org, "error": f"non-official evidence {evidence_id}"})
                if str(item.get("source_row_key") or "") != org:
                    evidence_errors.append({"organisation_number": org, "error": f"row-key mismatch {evidence_id}"})
                if not item.get("content_sha256") or not item.get("retrieved_at") or not item.get("source_url"):
                    evidence_errors.append({"organisation_number": org, "error": f"incomplete evidence {evidence_id}"})

        canonical = project_canonical_profile(projected)
        canonical_description += int(
            any(
                fact.get("type") == "company_description" and fact.get("availability") == "available"
                for fact in (canonical.get("canonical_facts") or [])
            )
        )
        canonical["synthesis"] = build_company_synthesis(canonical)

        for error in validate_contract_object(canonical):
            contract_errors.append({"organisation_number": org, "error": error})
        for error in validate_canonical_projection(canonical):
            canonical_errors.append({"organisation_number": org, "error": error})
        for error in validate_company_synthesis(canonical):
            synthesis_errors.append({"organisation_number": org, "error": error})

        if own_descriptions and len(sample_rows) < 20:
            company_section = next(
                section
                for section in canonical["synthesis"]["sections"]
                if section.get("key") == "company"
            )
            sample_rows.append(
                {
                    "organisation_number": org,
                    "name": profile.get("name"),
                    "description": own_descriptions[0].get("value"),
                    "registered_purpose": purposes[0].get("value") if purposes else None,
                    "company_synthesis": company_section.get("text"),
                    "evidence_ids": own_descriptions[0].get("evidence_ids"),
                }
            )

    companies = len(profiles)
    report = {
        "companies": companies,
        "network_requests_added": 0,
        "source": "exact-org BRREG bulk registry evidence retained by certified collector",
        "company_description_before": description_before,
        "company_description_after": description_after,
        "company_description_company_coverage_before": round(description_before / companies, 6) if companies else 0.0,
        "company_description_company_coverage_after": round(description_after / companies, 6) if companies else 0.0,
        "net_new_company_description_companies": description_after - description_before,
        "registry_activity_description_fallbacks": registry_description,
        "stronger_existing_descriptions_preserved": stronger_description_preserved,
        "registered_purpose_companies": registered_purpose,
        "canonical_description_companies": canonical_description,
        "idempotence_errors": idempotence_errors,
        "evidence_errors": evidence_errors,
        "contract_errors": contract_errors,
        "canonical_errors": canonical_errors,
        "synthesis_errors": synthesis_errors,
        "passed": not (
            idempotence_errors
            or evidence_errors
            or contract_errors
            or canonical_errors
            or synthesis_errors
        ),
    }

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.samples).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.samples).open("w", encoding="utf-8") as handle:
        for row in sample_rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
