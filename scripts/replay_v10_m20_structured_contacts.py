#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection  # noqa: E402
from norway_company_agent.company_site_contact import attach_company_site_contact_email_observations  # noqa: E402
from norway_company_agent.company_site_phone import attach_company_site_contact_phone_observations  # noqa: E402
from norway_company_agent.external_contract import (  # noqa: E402
    project_contact_email_observations,
    project_contact_phone_observations,
)
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.synthesis import build_company_synthesis, validate_company_synthesis  # noqa: E402

MANAGED_FIELDS = {"external.contact_email", "external.contact_phone"}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _read_profiles(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    files = sorted(path.rglob("profiles.jsonl"))
    if not files:
        raise ValueError("no profiles.jsonl found")
    for file in files:
        for profile in _read_jsonl(file):
            org = str(profile.get("organisation_number") or "")
            if len(org) != 9 or not org.isdigit() or org in rows:
                raise ValueError(f"invalid or duplicate profile organisation number: {org!r}")
            rows[org] = profile
    return rows


def _contact_pairs(row: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (str(claim.get("field")), json.dumps(claim.get("value"), sort_keys=True, ensure_ascii=False))
        for claim in row.get("claims") or []
        if isinstance(claim, dict)
        and claim.get("field") in MANAGED_FIELDS
        and claim.get("availability") == "available"
        and claim.get("value") not in (None, "")
    }


def _noncontact_claim_signature(row: dict[str, Any]) -> list[str]:
    values = []
    for claim in row.get("claims") or []:
        if not isinstance(claim, dict) or claim.get("field") in MANAGED_FIELDS:
            continue
        values.append(json.dumps(claim, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    return sorted(values)


def _audit_new_claims(
    row: dict[str, Any],
    new_pairs: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    evidence = {
        str(item.get("id")): item
        for item in row.get("evidence") or []
        if isinstance(item, dict) and item.get("id")
    }
    audit: list[dict[str, Any]] = []
    for claim in row.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        pair = (
            str(claim.get("field")),
            json.dumps(claim.get("value"), sort_keys=True, ensure_ascii=False),
        )
        if pair not in new_pairs:
            continue
        linked = [
            evidence[str(eid)]
            for eid in claim.get("evidence_ids") or []
            if str(eid) in evidence
        ]
        audit.append(
            {
                "organisation_number": row.get("organisation_number"),
                "field": claim.get("field"),
                "value": claim.get("value"),
                "claim_scope": claim.get("claim_scope"),
                "evidence": [
                    {
                        "source_url": item.get("source_url"),
                        "retrieved_at": item.get("retrieved_at"),
                        "content_sha256": item.get("content_sha256"),
                        "claim_span": item.get("claim_span"),
                    }
                    for item in linked
                ],
            }
        )
    return audit


def reproject_row(
    baseline_row: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    before_pairs = _contact_pairs(baseline_row)
    before_noncontact = _noncontact_claim_signature(baseline_row)

    working_profile = attach_company_site_contact_email_observations(deepcopy(profile))
    working_profile = attach_company_site_contact_phone_observations(working_profile)

    projected = project_contact_email_observations(deepcopy(baseline_row), working_profile)
    projected = project_contact_phone_observations(projected, working_profile)
    if _noncontact_claim_signature(projected) != before_noncontact:
        raise AssertionError("structured-contact replay changed a non-contact claim")

    projected = project_canonical_profile(projected)
    projected["synthesis"] = build_company_synthesis(projected)

    contract_errors = validate_contract_object(projected)
    canonical_errors = validate_canonical_projection(projected)
    synthesis_errors = validate_company_synthesis(projected)
    if contract_errors or canonical_errors or synthesis_errors:
        raise AssertionError(
            f"validation errors contract={contract_errors} canonical={canonical_errors} synthesis={synthesis_errors}"
        )

    after_pairs = _contact_pairs(projected)
    if not before_pairs.issubset(after_pairs):
        raise AssertionError("structured-contact replay lost an existing contact publication")

    return projected, _audit_new_claims(projected, after_pairs - before_pairs)


def replay(
    *,
    profiles_dir: Path,
    baseline_output: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    profiles = _read_profiles(profiles_dir)
    baseline = _read_jsonl(baseline_output)
    if len(baseline) != len(profiles):
        raise ValueError(f"profile/output count mismatch: {len(profiles)} != {len(baseline)}")

    challenger: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    baseline_email_orgs: set[str] = set()
    baseline_phone_orgs: set[str] = set()
    challenger_email_orgs: set[str] = set()
    challenger_phone_orgs: set[str] = set()

    for row in baseline:
        org = str(row.get("organisation_number") or "")
        profile = profiles.get(org)
        if profile is None:
            raise ValueError(f"missing retained profile for {org}")
        for field, target in (
            ("external.contact_email", baseline_email_orgs),
            ("external.contact_phone", baseline_phone_orgs),
        ):
            if any(
                isinstance(claim, dict)
                and claim.get("field") == field
                and claim.get("availability") == "available"
                for claim in row.get("claims") or []
            ):
                target.add(org)

        updated, new_claims = reproject_row(row, profile)
        challenger.append(updated)
        audit.extend(new_claims)

        for field, target in (
            ("external.contact_email", challenger_email_orgs),
            ("external.contact_phone", challenger_phone_orgs),
        ):
            if any(
                isinstance(claim, dict)
                and claim.get("field") == field
                and claim.get("availability") == "available"
                for claim in updated.get("claims") or []
            ):
                target.add(org)

    report = {
        "screen_type": "v10_m20_zero_request_structured_contact_replay",
        "companies": len(challenger),
        "network_requests_added": 0,
        "third_party_cost_usd": 0.0,
        "baseline_contact_email_companies": len(baseline_email_orgs),
        "challenger_contact_email_companies": len(challenger_email_orgs),
        "net_new_contact_email_companies": len(challenger_email_orgs - baseline_email_orgs),
        "baseline_contact_phone_companies": len(baseline_phone_orgs),
        "challenger_contact_phone_companies": len(challenger_phone_orgs),
        "net_new_contact_phone_companies": len(challenger_phone_orgs - baseline_phone_orgs),
        "baseline_any_external_contact_companies": len(baseline_email_orgs | baseline_phone_orgs),
        "challenger_any_external_contact_companies": len(challenger_email_orgs | challenger_phone_orgs),
        "net_new_any_external_contact_companies": len(
            (challenger_email_orgs | challenger_phone_orgs)
            - (baseline_email_orgs | baseline_phone_orgs)
        ),
        "new_contact_claims": len(audit),
        "existing_contact_publications_lost": 0,
        "non_contact_claims_changed": 0,
        "contract_canonical_synthesis_errors": 0,
        "manual_audit_required": True,
    }
    return challenger, report, audit


def _write_jsonl(path: Path, rows: list[dict[str, Any]], *, gzip_output: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if gzip_output else open
    with opener(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--baseline-output", type=Path, required=True)
    parser.add_argument("--challenger-output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manual-audit", type=Path, required=True)
    args = parser.parse_args()

    challenger, report, audit = replay(
        profiles_dir=args.profiles_dir,
        baseline_output=args.baseline_output,
    )
    _write_jsonl(args.challenger_output, challenger, gzip_output=args.challenger_output.suffix == ".gz")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_jsonl(args.manual_audit, audit)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print("--- manual audit rows ---")
    for item in audit:
        print(json.dumps(item, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
