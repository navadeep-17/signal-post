from __future__ import annotations

from typing import Any, Iterable


CONTACT_FIELDS = ("external.contact_email", "external.contact_phone")


def _index(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        org = str(row.get("organisation_number") or "").strip()
        if len(org) != 9 or not org.isdigit():
            raise ValueError(f"invalid organisation number: {org!r}")
        if org in out:
            raise ValueError(f"duplicate organisation number: {org}")
        out[org] = row
    return out


def _available_claims(row: dict[str, Any], field: str) -> list[dict[str, Any]]:
    return [
        claim
        for claim in row.get("claims") or []
        if isinstance(claim, dict)
        and claim.get("field") == field
        and claim.get("availability") == "available"
        and claim.get("value") not in (None, "")
    ]


def _value_key(value: Any) -> str:
    return str(value).strip().casefold()


def _evidence_index(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in row.get("evidence") or []
        if isinstance(item, dict) and str(item.get("id") or "")
    }


def audit_zero_request_contacts(
    baseline_rows: Iterable[dict[str, Any]],
    challenger_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    baseline = _index(baseline_rows)
    challenger = _index(challenger_rows)
    if set(baseline) != set(challenger):
        raise ValueError("baseline/challenger organisation sets differ")

    field_summary: dict[str, dict[str, int]] = {}
    manual_rows: list[dict[str, Any]] = []
    all_lost: list[dict[str, str]] = []

    for field in CONTACT_FIELDS:
        baseline_companies: set[str] = set()
        challenger_companies: set[str] = set()
        new_claims = 0
        lost_claims = 0

        for org in sorted(baseline):
            before_claims = _available_claims(baseline[org], field)
            after_claims = _available_claims(challenger[org], field)
            before = {_value_key(claim.get("value")): claim for claim in before_claims}
            after = {_value_key(claim.get("value")): claim for claim in after_claims}
            if before:
                baseline_companies.add(org)
            if after:
                challenger_companies.add(org)

            for value in sorted(set(before) - set(after)):
                lost_claims += 1
                all_lost.append(
                    {
                        "organisation_number": org,
                        "field": field,
                        "value": value,
                    }
                )

            evidence_by_id = _evidence_index(challenger[org])
            for value in sorted(set(after) - set(before)):
                new_claims += 1
                claim = after[value]
                evidence = [
                    evidence_by_id[str(eid)]
                    for eid in claim.get("evidence_ids") or []
                    if str(eid) in evidence_by_id
                ]
                complete = bool(evidence) and all(
                    str(item.get("source_url") or "").startswith(("http://", "https://"))
                    and bool(str(item.get("retrieved_at") or ""))
                    and len(str(item.get("content_sha256") or "")) == 64
                    for item in evidence
                )
                manual_rows.append(
                    {
                        "organisation_number": org,
                        "field": field,
                        "value": claim.get("value"),
                        "claim_scope": claim.get("claim_scope"),
                        "evidence": [
                            {
                                "id": item.get("id"),
                                "source_url": item.get("source_url"),
                                "retrieved_at": item.get("retrieved_at"),
                                "content_sha256": item.get("content_sha256"),
                                "claim_span": item.get("claim_span"),
                            }
                            for item in evidence
                        ],
                        "evidence_complete": complete,
                        "manual_exact_entity_review_required": True,
                    }
                )

        field_summary[field] = {
            "baseline_companies": len(baseline_companies),
            "challenger_companies": len(challenger_companies),
            "net_new_companies": len(challenger_companies - baseline_companies),
            "lost_companies": len(baseline_companies - challenger_companies),
            "new_claims": new_claims,
            "lost_claims": lost_claims,
        }

    return {
        "companies": len(baseline),
        "fields": field_summary,
        "new_contact_publications": len(manual_rows),
        "lost_contact_publications": len(all_lost),
        "lost_contacts": all_lost,
        "manual_audit_rows": manual_rows,
        "all_new_evidence_complete": all(
            bool(row.get("evidence_complete")) for row in manual_rows
        ),
        "network_requests_added_by_feature": 0,
        "manual_audit_required_for_every_new_contact": True,
        "notes": [
            "This audit compares evaluator-visible contact publications on the same company set.",
            "The feature is defined as zero-network; observed whole-run request variation is not treated as feature request cost.",
            "New structured contacts still require human exact-entity review before promotion.",
        ],
    }
