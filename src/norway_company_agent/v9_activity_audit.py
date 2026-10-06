from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable


FIELD = "external.company_update"


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


def _claims(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        claim
        for claim in row.get("claims") or []
        if isinstance(claim, dict)
        and claim.get("field") == FIELD
        and claim.get("availability") == "available"
        and claim.get("value") not in (None, "")
    ]


def _key(claim: dict[str, Any]) -> tuple[str, str, str]:
    value = claim.get("value") if isinstance(claim.get("value"), dict) else {}
    return (
        str(value.get("url") or ""),
        str(value.get("published_date") or ""),
        str(value.get("title") or ""),
    )


def _evidence_index(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in row.get("evidence") or []
        if isinstance(item, dict) and str(item.get("id") or "")
    }


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or "").strip()[:10])
    except ValueError:
        return None


def _retrieval_date(value: Any) -> date | None:
    raw = str(value or "").strip().replace("Z", "+00:00")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return None


def audit_dated_first_party_activity(
    baseline_rows: Iterable[dict[str, Any]],
    challenger_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    baseline = _index(baseline_rows)
    challenger = _index(challenger_rows)
    if set(baseline) != set(challenger):
        raise ValueError("baseline/challenger organisation sets differ")

    before_companies: set[str] = set()
    after_companies: set[str] = set()
    new_rows: list[dict[str, Any]] = []
    lost_rows: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for org in sorted(baseline):
        before_claims = {_key(claim): claim for claim in _claims(baseline[org])}
        after_claims = {_key(claim): claim for claim in _claims(challenger[org])}
        if before_claims:
            before_companies.add(org)
        if after_claims:
            after_companies.add(org)

        for key in sorted(set(before_claims) - set(after_claims)):
            lost_rows.append(
                {
                    "organisation_number": org,
                    "url": key[0],
                    "published_date": key[1],
                    "title": key[2],
                }
            )

        evidence_by_id = _evidence_index(challenger[org])
        for key in sorted(set(after_claims) - set(before_claims)):
            claim = after_claims[key]
            value = claim.get("value") if isinstance(claim.get("value"), dict) else {}
            evidence = [
                evidence_by_id[str(eid)]
                for eid in claim.get("evidence_ids") or []
                if str(eid) in evidence_by_id
            ]
            complete = bool(evidence) and all(
                str(item.get("source_url") or "").startswith(("http://", "https://"))
                and bool(str(item.get("retrieved_at") or ""))
                and len(str(item.get("content_sha256") or "")) == 64
                and bool(str(item.get("claim_span") or ""))
                for item in evidence
            )
            page_local = bool(evidence) and all(
                str(item.get("source_url") or "").rstrip("/")
                == str(value.get("url") or "").rstrip("/")
                for item in evidence
            )
            published = _date(value.get("published_date"))
            retrieval_dates = [_retrieval_date(item.get("retrieved_at")) for item in evidence]
            not_future = bool(
                published
                and retrieval_dates
                and all(observed is not None and published <= observed for observed in retrieval_dates)
            )
            spans = " ".join(str(item.get("claim_span") or "") for item in evidence)
            structured_date = "jsonld_" in spans.casefold()

            if not complete:
                errors.append({"organisation_number": org, "error": "new update evidence incomplete"})
            if not page_local:
                errors.append({"organisation_number": org, "error": "new update is not supported by its own page URL"})
            if not not_future:
                errors.append({"organisation_number": org, "error": "new update publication date is invalid or future"})

            new_rows.append(
                {
                    "organisation_number": org,
                    "title": value.get("title"),
                    "url": value.get("url"),
                    "published_date": value.get("published_date"),
                    "structured_jsonld_date_evidence": structured_date,
                    "evidence_complete": complete,
                    "page_local_evidence": page_local,
                    "not_future": not_future,
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
                    "manual_date_scope_review_required": True,
                }
            )

    return {
        "companies": len(baseline),
        "baseline_dated_activity_companies": len(before_companies),
        "challenger_dated_activity_companies": len(after_companies),
        "net_new_dated_activity_companies": len(after_companies - before_companies),
        "lost_dated_activity_companies": len(before_companies - after_companies),
        "new_update_publications": len(new_rows),
        "new_updates_with_structured_jsonld_date_evidence": sum(
            bool(item["structured_jsonld_date_evidence"]) for item in new_rows
        ),
        "lost_update_publications": len(lost_rows),
        "lost_updates": lost_rows,
        "audit_errors": errors,
        "audit_error_count": len(errors),
        "manual_audit_rows": new_rows,
        "network_requests_added_by_m6_extraction": 0,
        "manual_audit_required_for_every_new_update": True,
        "notes": [
            "M6 only adds page-local structured publication-date extraction to already-fetched first-party HTML.",
            "Homepage teaser dates remain nomination-only and are not promoted by this audit.",
            "Each new activity fact must cite the same detail page whose content hash contains the publication-date evidence.",
        ],
    }
