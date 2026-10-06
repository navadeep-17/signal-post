from __future__ import annotations

from typing import Any, Iterable


HIRING_FIELDS = (
    "external.careers_page",
    "external.hiring_intent",
    "external.job_posting",
)


def _index(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        org = str(row.get("organisation_number") or "").strip()
        if len(org) != 9 or not org.isdigit():
            raise ValueError(f"invalid organisation number: {org!r}")
        if org in indexed:
            raise ValueError(f"duplicate organisation number: {org}")
        indexed[org] = row
    return indexed


def _available(row: dict[str, Any], field: str) -> list[dict[str, Any]]:
    return [
        claim
        for claim in row.get("claims") or []
        if isinstance(claim, dict)
        and claim.get("field") == field
        and claim.get("availability") == "available"
        and claim.get("value") not in (None, "")
    ]


def _claim_key(claim: dict[str, Any]) -> str:
    return repr(claim.get("value"))


def _evidence_index(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in row.get("evidence") or []
        if isinstance(item, dict) and str(item.get("id") or "")
    }


def _complete_evidence(row: dict[str, Any], claim: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    by_id = _evidence_index(row)
    evidence = [
        by_id[str(evidence_id)]
        for evidence_id in claim.get("evidence_ids") or []
        if str(evidence_id) in by_id
    ]
    complete = bool(evidence) and all(
        str(item.get("source_url") or "").startswith(("http://", "https://"))
        and bool(str(item.get("retrieved_at") or ""))
        and len(str(item.get("content_sha256") or "")) == 64
        and bool(str(item.get("claim_span") or ""))
        for item in evidence
    )
    return complete, evidence


def _strict_job_shape(claim: dict[str, Any]) -> bool:
    value = claim.get("value")
    if not isinstance(value, dict):
        return False
    return bool(
        str(value.get("title") or "").strip()
        and str(value.get("url") or "").startswith(("http://", "https://"))
        and str(value.get("application_url") or "").startswith(("http://", "https://"))
        and str(value.get("deadline") or "").strip()
    )


def audit_hiring_semantics(
    baseline_rows: Iterable[dict[str, Any]],
    challenger_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    baseline = _index(baseline_rows)
    challenger = _index(challenger_rows)
    if set(baseline) != set(challenger):
        raise ValueError("baseline/challenger organisation sets differ")

    summary: dict[str, dict[str, int]] = {}
    manual_rows: list[dict[str, Any]] = []
    semantic_errors: list[dict[str, str]] = []

    for field in HIRING_FIELDS:
        before_companies: set[str] = set()
        after_companies: set[str] = set()
        new_claims = 0
        lost_claims = 0

        for org in sorted(baseline):
            before_claims = _available(baseline[org], field)
            after_claims = _available(challenger[org], field)
            before = {_claim_key(claim): claim for claim in before_claims}
            after = {_claim_key(claim): claim for claim in after_claims}
            if before:
                before_companies.add(org)
            if after:
                after_companies.add(org)

            lost = set(before) - set(after)
            lost_claims += len(lost)
            for key in sorted(lost):
                semantic_errors.append(
                    {
                        "organisation_number": org,
                        "field": field,
                        "error": "previous hiring publication lost",
                    }
                )

            for key in sorted(set(after) - set(before)):
                new_claims += 1
                claim = after[key]
                complete, evidence = _complete_evidence(challenger[org], claim)
                if not complete:
                    semantic_errors.append(
                        {
                            "organisation_number": org,
                            "field": field,
                            "error": "new hiring publication lacks complete page evidence",
                        }
                    )

                if field == "external.hiring_intent":
                    scope = str(claim.get("claim_scope") or "").casefold()
                    if "not a claim that a specific vacancy" not in scope:
                        semantic_errors.append(
                            {
                                "organisation_number": org,
                                "field": field,
                                "error": "hiring intent does not explicitly preserve vacancy boundary",
                            }
                        )
                elif field == "external.job_posting" and not _strict_job_shape(claim):
                    semantic_errors.append(
                        {
                            "organisation_number": org,
                            "field": field,
                            "error": "specific job lacks title/url/application/deadline shape",
                        }
                    )

                if field in {"external.hiring_intent", "external.job_posting"}:
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
                            "manual_exact_entity_review_required": True,
                            "manual_semantic_level_review_required": True,
                        }
                    )

        summary[field] = {
            "baseline_companies": len(before_companies),
            "challenger_companies": len(after_companies),
            "net_new_companies": len(after_companies - before_companies),
            "lost_companies": len(before_companies - after_companies),
            "new_claims": new_claims,
            "lost_claims": lost_claims,
        }

    return {
        "companies": len(baseline),
        "fields": summary,
        "semantic_errors": semantic_errors,
        "semantic_error_count": len(semantic_errors),
        "new_intent_or_job_publications": len(manual_rows),
        "manual_audit_rows": manual_rows,
        "network_requests_added_by_projection": 0,
        "three_level_model": {
            "careers_surface": "external.careers_page",
            "company_authored_intent": "external.hiring_intent",
            "specific_active_job": "external.job_posting",
        },
        "manual_audit_required_for_every_new_intent_or_job": True,
    }
