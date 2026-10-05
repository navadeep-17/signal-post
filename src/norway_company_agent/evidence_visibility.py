from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import urlparse

CORE_EVIDENCE_FIELDS = ("source_url", "retrieved_at", "claim_span", "content_sha256")
IDENTITY_SENSITIVE_FIELDS = {"official_website", "social_links"}
IDENTITY_SENSITIVE_PREFIXES = ("external.", "official.support_")
DATE_KEYS = (
    "reporting_period",
    "publication_date",
    "published_at",
    "effective_at",
    "as_of",
    "deadline",
    "awarded_at",
)


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _valid_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(char in "0123456789abcdefABCDEF" for char in text)


def _reopenable_http_url(value: Any) -> bool:
    try:
        parsed = urlparse(str(value or ""))
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_identity_sensitive_claim(claim: dict[str, Any], evidence_rows: list[dict[str, Any]]) -> bool:
    field = str(claim.get("field") or "")
    if field in IDENTITY_SENSITIVE_FIELDS or field.startswith(IDENTITY_SENSITIVE_PREFIXES):
        return True
    return any(str(row.get("source_class") or "") == "company_owned" for row in evidence_rows)


def _visible_date(claim: dict[str, Any], evidence_rows: list[dict[str, Any]]) -> bool:
    for key in DATE_KEYS:
        if _present(claim.get(key)):
            return True
    for row in evidence_rows:
        for key in DATE_KEYS:
            if _present(row.get(key)):
                return True
    return False


def audit_contract_item(item: dict[str, Any]) -> dict[str, Any]:
    """Audit evaluator-visible evidence without performing network access.

    This intentionally inspects only the submitted/result-facing contract. Internal provenance
    that is not projected into claims/evidence does not count as visible here.
    """

    organisation_number = str(item.get("organisation_number") or "")
    evidence_by_id = {
        str(row.get("id")): row
        for row in (item.get("evidence") or [])
        if isinstance(row, dict) and row.get("id")
    }

    claim_rows: list[dict[str, Any]] = []
    for index, claim in enumerate(item.get("claims") or []):
        if not isinstance(claim, dict) or claim.get("availability") != "available":
            continue
        field = str(claim.get("field") or "unknown")
        evidence_ids = [str(value) for value in (claim.get("evidence_ids") or []) if value]
        backing = [evidence_by_id[value] for value in evidence_ids if value in evidence_by_id]
        missing_evidence_ids = [value for value in evidence_ids if value not in evidence_by_id]

        missing_core: set[str] = set()
        if not backing:
            missing_core.add("evidence")
        for row in backing:
            for key in CORE_EVIDENCE_FIELDS:
                value = row.get(key)
                if key == "content_sha256":
                    if not _valid_sha256(value):
                        missing_core.add(key)
                elif not _present(value):
                    missing_core.add(key)
        reopenable = bool(backing) and all(_reopenable_http_url(row.get("source_url")) for row in backing)
        if backing and not reopenable:
            missing_core.add("reopenable_source_url")

        identity_sensitive = _is_identity_sensitive_claim(claim, backing)
        identity_proof_visible = any(_present(row.get("identity_proof")) for row in backing) or _present(
            claim.get("identity_proof")
        )
        extraction_method_visible = any(_present(row.get("extraction_method")) for row in backing) or _present(
            claim.get("extraction_method")
        )

        missing_external_trace: list[str] = []
        if identity_sensitive:
            if not identity_proof_visible:
                missing_external_trace.append("identity_proof")
            if not extraction_method_visible:
                missing_external_trace.append("extraction_method")

        claim_rows.append(
            {
                "claim_index": index,
                "field": field,
                "evidence_ids": evidence_ids,
                "missing_evidence_ids": missing_evidence_ids,
                "missing_core_evidence": sorted(missing_core),
                "core_evidence_complete": not missing_core and not missing_evidence_ids,
                "reopenable_source": reopenable,
                "identity_sensitive_claim": identity_sensitive,
                "identity_proof_visible": identity_proof_visible,
                "extraction_method_visible": extraction_method_visible,
                "date_visible": _visible_date(claim, backing),
                "missing_external_trace": missing_external_trace,
            }
        )

    return {
        "organisation_number": organisation_number,
        "available_claims": len(claim_rows),
        "claims": claim_rows,
    }


def audit_contract_rows(items: list[dict[str, Any]]) -> dict[str, Any]:
    company_reports = [audit_contract_item(item) for item in items]
    claims = [claim for report in company_reports for claim in report["claims"]]
    identity_sensitive = [claim for claim in claims if claim["identity_sensitive_claim"]]

    by_field_total = Counter(claim["field"] for claim in claims)
    by_field_core_complete = Counter(claim["field"] for claim in claims if claim["core_evidence_complete"])
    by_field_identity_sensitive = Counter(claim["field"] for claim in identity_sensitive)
    by_field_identity = Counter(
        claim["field"] for claim in identity_sensitive if claim["identity_proof_visible"]
    )

    issues = []
    for report in company_reports:
        for claim in report["claims"]:
            missing = list(claim["missing_core_evidence"])
            if claim["missing_evidence_ids"]:
                missing.append("referenced_evidence")
            missing.extend(claim["missing_external_trace"])
            if missing:
                issues.append(
                    {
                        "organisation_number": report["organisation_number"],
                        "field": claim["field"],
                        "missing": sorted(set(missing)),
                    }
                )

    return {
        "companies": len(items),
        "available_claims": len(claims),
        "core_evidence_complete_claims": sum(claim["core_evidence_complete"] for claim in claims),
        "reopenable_source_claims": sum(claim["reopenable_source"] for claim in claims),
        "identity_sensitive_claims": len(identity_sensitive),
        "identity_proof_visible": sum(claim["identity_proof_visible"] for claim in identity_sensitive),
        "extraction_method_visible": sum(claim["extraction_method_visible"] for claim in identity_sensitive),
        "claims_with_visible_date": sum(claim["date_visible"] for claim in claims),
        "by_field": {
            field: {
                "available_claims": by_field_total[field],
                "core_evidence_complete": by_field_core_complete[field],
                "identity_sensitive_claims": by_field_identity_sensitive[field],
                "identity_proof_visible": by_field_identity[field],
            }
            for field in sorted(by_field_total)
        },
        "issues": issues,
    }
