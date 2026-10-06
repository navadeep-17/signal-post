#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

MANAGED_FIELDS = {"external.contact_email", "external.contact_phone"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected object")
        rows.append(value)
    return rows


def available_contacts(row: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for claim in row.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        field = str(claim.get("field") or "")
        if field not in MANAGED_FIELDS or claim.get("availability") != "available":
            continue
        value = str(claim.get("value") or "").strip()
        if value:
            out[(field, value)] = claim
    return out


def evidence_for(row: dict[str, Any], claim: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {
        str(item.get("id")): item
        for item in row.get("evidence") or []
        if isinstance(item, dict) and item.get("id")
    }
    return [
        by_id[str(evidence_id)]
        for evidence_id in claim.get("evidence_ids") or []
        if str(evidence_id) in by_id
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit integrated V9 contact publication deltas.")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--challenger", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manual-audit", type=Path, required=True)
    args = parser.parse_args()

    baseline_rows = {str(row.get("organisation_number") or ""): row for row in read_jsonl(args.baseline)}
    challenger_rows = {str(row.get("organisation_number") or ""): row for row in read_jsonl(args.challenger)}
    if set(baseline_rows) != set(challenger_rows):
        raise ValueError("baseline/challenger company sets differ")

    new_rows: list[dict[str, Any]] = []
    lost_rows: list[dict[str, Any]] = []
    baseline_company_sets = {field: set() for field in MANAGED_FIELDS}
    challenger_company_sets = {field: set() for field in MANAGED_FIELDS}

    for org in sorted(baseline_rows):
        baseline = baseline_rows[org]
        challenger = challenger_rows[org]
        before = available_contacts(baseline)
        after = available_contacts(challenger)

        for field, _ in before:
            baseline_company_sets[field].add(org)
        for field, _ in after:
            challenger_company_sets[field].add(org)

        for key in sorted(set(after) - set(before)):
            claim = after[key]
            linked = evidence_for(challenger, claim)
            complete = bool(linked) and all(
                str(item.get("source_url") or "").startswith(("http://", "https://"))
                and bool(str(item.get("retrieved_at") or ""))
                and len(str(item.get("content_sha256") or "")) == 64
                for item in linked
            )
            new_rows.append(
                {
                    "organisation_number": org,
                    "field": key[0],
                    "value": key[1],
                    "claim_scope": claim.get("claim_scope"),
                    "observation_id": claim.get("observation_id"),
                    "evidence_complete": complete,
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

        for key in sorted(set(before) - set(after)):
            lost_rows.append(
                {
                    "organisation_number": org,
                    "field": key[0],
                    "value": key[1],
                }
            )

    field_counts = Counter(row["field"] for row in new_rows)
    report = {
        "screen_type": "v9_integrated_contact_delta_audit",
        "companies": len(baseline_rows),
        "network_requests_added_by_audit": 0,
        "third_party_cost_usd": 0.0,
        "baseline_contact_email_companies": len(baseline_company_sets["external.contact_email"]),
        "challenger_contact_email_companies": len(challenger_company_sets["external.contact_email"]),
        "baseline_contact_phone_companies": len(baseline_company_sets["external.contact_phone"]),
        "challenger_contact_phone_companies": len(challenger_company_sets["external.contact_phone"]),
        "new_contact_claims": len(new_rows),
        "new_contact_claims_by_field": dict(sorted(field_counts.items())),
        "lost_contact_claims": len(lost_rows),
        "all_new_contact_evidence_complete": all(row["evidence_complete"] for row in new_rows),
        "manual_audit_required_for_every_new_contact_claim": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.manual_audit.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in new_rows),
        encoding="utf-8",
    )
    if lost_rows:
        (args.report.parent / "integrated-lost-contact-publications.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in lost_rows),
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
