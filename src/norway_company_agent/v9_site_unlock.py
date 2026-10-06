from __future__ import annotations

from typing import Any, Iterable

from .v9_measurement import FAMILY_FIELDS


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


def _available_claims(row: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for claim in row.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        field = str(claim.get("field") or "")
        if (
            field
            and claim.get("availability") == "available"
            and claim.get("value") not in (None, "")
        ):
            out.setdefault(field, []).append(claim)
    return out


def _family_presence(row: dict[str, Any]) -> dict[str, bool]:
    claims = _available_claims(row)
    fields = set(claims)
    return {
        family: bool(fields.intersection(family_fields))
        for family, family_fields in FAMILY_FIELDS.items()
    }


def _evidence_index(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in row.get("evidence") or []
        if isinstance(item, dict) and str(item.get("id") or "")
    }


def _claim_evidence(row: dict[str, Any], field: str) -> list[dict[str, Any]]:
    evidence = _evidence_index(row)
    found: list[dict[str, Any]] = []
    for claim in _available_claims(row).get(field) or []:
        for evidence_id in claim.get("evidence_ids") or []:
            item = evidence.get(str(evidence_id))
            if item is not None:
                found.append(item)
    return found




def _publication_rows(row: dict[str, Any], fields: set[str]) -> list[dict[str, Any]]:
    evidence = _evidence_index(row)
    publications: list[dict[str, Any]] = []
    for field in sorted(fields):
        for claim in _available_claims(row).get(field) or []:
            linked = [
                evidence[str(evidence_id)]
                for evidence_id in claim.get("evidence_ids") or []
                if str(evidence_id) in evidence
            ]
            publications.append(
                {
                    "field": field,
                    "value": claim.get("value"),
                    "confidence": claim.get("confidence"),
                    "evidence": [
                        {
                            "id": item.get("id"),
                            "source_url": item.get("source_url"),
                            "retrieved_at": item.get("retrieved_at"),
                            "content_sha256": item.get("content_sha256"),
                            "claim_span": item.get("claim_span"),
                        }
                        for item in linked
                    ],
                }
            )
    return publications

def _evidence_complete(item: dict[str, Any]) -> bool:
    source_url = str(item.get("source_url") or "")
    retrieved_at = str(item.get("retrieved_at") or "")
    digest = str(item.get("content_sha256") or "")
    return bool(
        source_url.startswith(("http://", "https://"))
        and retrieved_at
        and len(digest) == 64
    )


def audit_new_verified_site_unlock(
    baseline_rows: Iterable[dict[str, Any]],
    challenger_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    baseline = _index(baseline_rows)
    challenger = _index(challenger_rows)
    if set(baseline) != set(challenger):
        raise ValueError("baseline/challenger organisation sets differ")

    audit_rows: list[dict[str, Any]] = []
    lost_sites: list[str] = []
    total_edges = 0

    for org in sorted(baseline):
        before = _family_presence(baseline[org])
        after = _family_presence(challenger[org])
        if before["verified_website"] and not after["verified_website"]:
            lost_sites.append(org)
        if before["verified_website"] or not after["verified_website"]:
            continue

        unlocked = [
            family
            for family in FAMILY_FIELDS
            if family != "verified_website" and not before[family] and after[family]
        ]
        total_edges += len(unlocked)
        website_evidence = _claim_evidence(challenger[org], "official_website")
        external_evidence: list[dict[str, Any]] = []
        for family in unlocked:
            for field in FAMILY_FIELDS[family]:
                external_evidence.extend(_claim_evidence(challenger[org], field))

        source_urls = sorted(
            {
                str(item.get("source_url"))
                for item in [*website_evidence, *external_evidence]
                if str(item.get("source_url") or "").startswith(("http://", "https://"))
            }
        )
        all_evidence = [*website_evidence, *external_evidence]
        publication_fields = {"official_website"}
        for family in unlocked:
            publication_fields.update(FAMILY_FIELDS[family])
        audit_rows.append(
            {
                "organisation_number": org,
                "new_verified_website": True,
                "unlocked_families": unlocked,
                "company_family_edges_unlocked": len(unlocked),
                "source_urls": source_urls,
                "new_external_publications": _publication_rows(
                    challenger[org],
                    publication_fields,
                ),
                "evidence_rows": len(all_evidence),
                "all_relevant_evidence_hashed_and_timestamped": bool(all_evidence)
                and all(_evidence_complete(item) for item in all_evidence),
                "manual_wrong_entity_review_required": True,
                "manual_page_scope_review_required": True,
            }
        )

    return {
        "companies": len(baseline),
        "new_verified_website_companies": len(audit_rows),
        "lost_verified_website_companies": len(lost_sites),
        "lost_verified_website_organisation_numbers": lost_sites,
        "net_new_company_family_edges_from_new_sites": total_edges,
        "new_site_audit_rows": audit_rows,
        "manual_audit_required_for_all_new_external_publications": True,
        "notes": [
            "A new website is counted only when official_website was unavailable in baseline and available in challenger.",
            "Downstream value is measured as net-new scored-family company coverage, not raw claim count.",
            "Evidence completeness here checks source URL, retrieval timestamp and 64-character content hash; human review still decides wrong-entity and page-scope ambiguity.",
        ],
    }
