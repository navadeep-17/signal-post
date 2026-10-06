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
from norway_company_agent.hiring_intent_contract import project_company_authored_hiring_intent  # noqa: E402
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.synthesis import build_company_synthesis, validate_company_synthesis  # noqa: E402

INTENT_FIELD = "external.hiring_intent"
PRESERVED_HIRING_FIELDS = {"external.careers_page", "external.job_posting"}


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


def _available(row: dict[str, Any], field: str) -> list[dict[str, Any]]:
    return [
        claim
        for claim in row.get("claims") or []
        if isinstance(claim, dict)
        and claim.get("field") == field
        and claim.get("availability") == "available"
        and claim.get("value") not in (None, "")
    ]


def _claim_signature(row: dict[str, Any], *, exclude_intent: bool = False) -> list[str]:
    values: list[str] = []
    for claim in row.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        if exclude_intent and claim.get("field") == INTENT_FIELD:
            continue
        values.append(json.dumps(claim, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    return sorted(values)


def _audit_new_intent(row: dict[str, Any], baseline: dict[str, Any]) -> list[dict[str, Any]]:
    before = {
        json.dumps(claim.get("value"), sort_keys=True, ensure_ascii=False)
        for claim in _available(baseline, INTENT_FIELD)
    }
    evidence = {
        str(item.get("id")): item
        for item in row.get("evidence") or []
        if isinstance(item, dict) and item.get("id")
    }
    audit: list[dict[str, Any]] = []
    for claim in _available(row, INTENT_FIELD):
        value_key = json.dumps(claim.get("value"), sort_keys=True, ensure_ascii=False)
        if value_key in before:
            continue
        linked = [
            evidence[str(eid)]
            for eid in claim.get("evidence_ids") or []
            if str(eid) in evidence
        ]
        complete = bool(linked) and all(
            str(item.get("source_url") or "").startswith(("http://", "https://"))
            and bool(str(item.get("retrieved_at") or ""))
            and len(str(item.get("content_sha256") or "")) == 64
            and bool(str(item.get("claim_span") or ""))
            and bool(item.get("identity_proof"))
            and str(item.get("extraction_method") or "").startswith(
                "explicit_company_authored_recruitment_language:"
            )
            for item in linked
        )
        audit.append(
            {
                "organisation_number": row.get("organisation_number"),
                "field": INTENT_FIELD,
                "value": claim.get("value"),
                "claim_scope": claim.get("claim_scope"),
                "evidence_complete": complete,
                "evidence": [
                    {
                        "source_url": item.get("source_url"),
                        "retrieved_at": item.get("retrieved_at"),
                        "content_sha256": item.get("content_sha256"),
                        "claim_span": item.get("claim_span"),
                        "identity_proof": item.get("identity_proof"),
                        "extraction_method": item.get("extraction_method"),
                    }
                    for item in linked
                ],
            }
        )
    return audit


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
    manual: list[dict[str, Any]] = []
    baseline_sets = {field: set() for field in [*PRESERVED_HIRING_FIELDS, INTENT_FIELD]}
    challenger_sets = {field: set() for field in [*PRESERVED_HIRING_FIELDS, INTENT_FIELD]}
    errors: list[dict[str, Any]] = []

    for baseline_row in baseline:
        org = str(baseline_row.get("organisation_number") or "")
        profile = profiles.get(org)
        if profile is None:
            raise ValueError(f"missing retained profile for {org}")

        for field, target in (
            ("external.careers_page", baseline_sets["external.careers_page"]),
            (INTENT_FIELD, baseline_sets[INTENT_FIELD]),
            ("external.job_posting", baseline_sets["external.job_posting"]),
        ):
            if _available(baseline_row, field):
                target.add(org)

        before_nonintent = _claim_signature(baseline_row, exclude_intent=True)
        projected = project_company_authored_hiring_intent(deepcopy(baseline_row), profile)
        if _claim_signature(projected, exclude_intent=True) != before_nonintent:
            raise AssertionError(f"M5 changed a non-intent claim for {org}")

        projected = project_canonical_profile(projected)
        projected["synthesis"] = build_company_synthesis(projected)

        contract_errors = validate_contract_object(projected)
        canonical_errors = validate_canonical_projection(projected)
        synthesis_errors = validate_company_synthesis(projected)
        if contract_errors or canonical_errors or synthesis_errors:
            errors.append(
                {
                    "organisation_number": org,
                    "contract": contract_errors,
                    "canonical": canonical_errors,
                    "synthesis": synthesis_errors,
                }
            )

        for field, target in (
            ("external.careers_page", challenger_sets["external.careers_page"]),
            (INTENT_FIELD, challenger_sets[INTENT_FIELD]),
            ("external.job_posting", challenger_sets["external.job_posting"]),
        ):
            if _available(projected, field):
                target.add(org)

        challenger.append(projected)
        manual.extend(_audit_new_intent(projected, baseline_row))

    if errors:
        raise AssertionError(f"M5 replay validation errors: {errors[:5]}")

    report = {
        "screen_type": "v9_m5_zero_request_hiring_semantics_replay",
        "companies": len(challenger),
        "network_requests_added": 0,
        "third_party_cost_usd": 0.0,
        "search_api_requests": 0,
        "baseline_careers_surface_companies": len(baseline_sets["external.careers_page"]),
        "challenger_careers_surface_companies": len(challenger_sets["external.careers_page"]),
        "baseline_hiring_intent_companies": len(baseline_sets[INTENT_FIELD]),
        "challenger_hiring_intent_companies": len(challenger_sets[INTENT_FIELD]),
        "net_new_hiring_intent_companies": len(challenger_sets[INTENT_FIELD] - baseline_sets[INTENT_FIELD]),
        "baseline_specific_job_companies": len(baseline_sets["external.job_posting"]),
        "challenger_specific_job_companies": len(challenger_sets["external.job_posting"]),
        "lost_careers_surface_companies": len(
            baseline_sets["external.careers_page"] - challenger_sets["external.careers_page"]
        ),
        "lost_specific_job_companies": len(
            baseline_sets["external.job_posting"] - challenger_sets["external.job_posting"]
        ),
        "new_hiring_intent_claims": len(manual),
        "all_new_intent_evidence_complete": all(bool(row.get("evidence_complete")) for row in manual),
        "non_intent_claims_changed": 0,
        "contract_canonical_synthesis_errors": 0,
        "manual_audit_required_for_every_new_intent": True,
        "fresh_companies_used": 0,
        "semantic_boundary": {
            "careers_surface": "presence only",
            "hiring_intent": "explicit company-authored recruitment language; generic careers text excluded; no specific vacancy asserted",
            "specific_job": "existing strict external.job_posting semantics unchanged",
        },
    }
    return challenger, report, manual


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

    challenger, report, manual = replay(
        profiles_dir=args.profiles_dir,
        baseline_output=args.baseline_output,
    )
    _write_jsonl(args.challenger_output, challenger, gzip_output=args.challenger_output.suffix == ".gz")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_jsonl(args.manual_audit, manual)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print("--- M5 manual audit rows ---")
    for item in manual:
        print(json.dumps(item, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
