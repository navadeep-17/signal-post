#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import (  # noqa: E402
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.first_party_activity import (  # noqa: E402
    extract_strict_first_party_facts,
    project_first_party_activity_claims,
)
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.synthesis import (  # noqa: E402
    build_company_synthesis,
    validate_company_synthesis,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _profile_without_m6_jsonld_dates(profile: dict[str, Any]) -> dict[str, Any]:
    """Model the exact M5 collector over the same retained M6 HTTP snapshots."""
    row = deepcopy(profile)
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    for key in ("website", "website_news_detail"):
        record = evidence.get(key)
        if not isinstance(record, dict):
            continue
        value = record.get("value") if isinstance(record.get("value"), dict) else {}
        pages = []
        for page in value.get("pages") or []:
            if not isinstance(page, dict):
                continue
            item = dict(page)
            item["published_date_candidates"] = [
                candidate
                for candidate in item.get("published_date_candidates") or []
                if not str((candidate or {}).get("method") or "").startswith("jsonld_")
            ]
            pages.append(item)
        value["pages"] = pages
        if key == "website":
            value["published_date_candidates"] = [
                candidate
                for candidate in value.get("published_date_candidates") or []
                if not str((candidate or {}).get("method") or "").startswith("jsonld_")
            ]
        record["value"] = value
        evidence[key] = record
    row["evidence"] = evidence
    return row


def _activity_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(item.get("url") or ""),
        str(item.get("published_date") or ""),
        str(item.get("title") or ""),
    )


def _reproject_activity(
    final_row: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Recompute strict company-site activity while preserving feed/update claims.

    project_first_party_activity_claims owns external.company_update and external.job_posting.
    Feed updates are a later V8 layer, so they are temporarily removed and then restored.
    """
    row = deepcopy(final_row)
    claims = [dict(item) for item in row.get("claims") or [] if isinstance(item, dict)]
    evidence_by_id = {
        str(item.get("id")): dict(item)
        for item in row.get("evidence") or []
        if isinstance(item, dict) and str(item.get("id") or "")
    }

    later_updates = [
        claim
        for claim in claims
        if claim.get("field") == "external.company_update"
        and str(claim.get("platform") or "") != "company_site"
    ]
    later_evidence_ids = {
        str(evidence_id)
        for claim in later_updates
        for evidence_id in claim.get("evidence_ids") or []
    }
    later_evidence = {
        evidence_id: evidence_by_id[evidence_id]
        for evidence_id in later_evidence_ids
        if evidence_id in evidence_by_id
    }

    row["claims"] = [claim for claim in claims if claim not in later_updates]
    projected = project_first_party_activity_claims(row, profile)

    projected_claims = [dict(item) for item in projected.get("claims") or []]
    projected_claims.extend(later_updates)
    projected["claims"] = projected_claims

    merged_evidence = {
        str(item.get("id")): dict(item)
        for item in projected.get("evidence") or []
        if isinstance(item, dict) and str(item.get("id") or "")
    }
    merged_evidence.update(later_evidence)
    projected["evidence"] = sorted(
        merged_evidence.values(),
        key=lambda item: str(item.get("id") or ""),
    )

    projected = project_canonical_profile(projected)
    projected["synthesis"] = build_company_synthesis(projected)
    return projected


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build same-snapshot M5 baseline and M6 challenger outputs by filtering only "
            "M6 JSON-LD date candidates from retained M6 profiles."
        )
    )
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--collector-output", type=Path, required=True)
    parser.add_argument("--baseline-output", type=Path, required=True)
    parser.add_argument("--challenger-output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    profiles = read_jsonl(args.profiles)
    outputs = read_jsonl(args.collector_output)
    pindex = {str(row.get("organisation_number") or ""): row for row in profiles}
    oindex = {str(row.get("organisation_number") or ""): row for row in outputs}
    if len(pindex) != len(profiles) or len(oindex) != len(outputs) or set(pindex) != set(oindex):
        raise ValueError("profile/output organisation sets differ or contain duplicates")

    baseline_rows: list[dict[str, Any]] = []
    challenger_rows: list[dict[str, Any]] = []
    affected: list[dict[str, Any]] = []
    validation_errors: list[dict[str, Any]] = []

    for org in sorted(pindex):
        profile = pindex[org]
        baseline_profile = _profile_without_m6_jsonld_dates(profile)
        baseline_facts = extract_strict_first_party_facts(baseline_profile)["updates"]
        challenger_facts = extract_strict_first_party_facts(profile)["updates"]
        before = {_activity_key(item) for item in baseline_facts}
        after = {_activity_key(item) for item in challenger_facts}
        if before != after:
            affected.append(
                {
                    "organisation_number": org,
                    "baseline_strict_updates": len(before),
                    "challenger_strict_updates": len(after),
                    "net_new_update_keys": len(after - before),
                    "lost_update_keys": len(before - after),
                }
            )

        baseline = _reproject_activity(oindex[org], baseline_profile)
        challenger = _reproject_activity(oindex[org], profile)
        for label, row in (("baseline", baseline), ("challenger", challenger)):
            contract_errors = validate_contract_object(row)
            canonical_errors = validate_canonical_projection(row)
            synthesis_errors = validate_company_synthesis(row)
            if contract_errors or canonical_errors or synthesis_errors:
                validation_errors.append(
                    {
                        "organisation_number": org,
                        "side": label,
                        "contract": contract_errors,
                        "canonical": canonical_errors,
                        "synthesis": synthesis_errors,
                    }
                )
        baseline_rows.append(baseline)
        challenger_rows.append(challenger)

    if validation_errors:
        raise AssertionError(f"M6 same-snapshot validation errors: {validation_errors[:5]}")

    write_jsonl(args.baseline_output, baseline_rows)
    write_jsonl(args.challenger_output, challenger_rows)
    report = {
        "screen_type": "v9_m6_same_snapshot_jsonld_date_causal_replay",
        "companies": len(profiles),
        "affected_companies": len(affected),
        "net_new_strict_update_keys": sum(row["net_new_update_keys"] for row in affected),
        "lost_strict_update_keys": sum(row["lost_update_keys"] for row in affected),
        "validation_errors": 0,
        "network_requests_added_by_replay": 0,
        "fresh_companies_used": 0,
        "baseline_model": (
            "same retained HTTP snapshots with only jsonld_* published-date candidates removed"
        ),
        "challenger_model": "same retained HTTP snapshots with M6 structured article dates enabled",
        "affected_rows": affected,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
