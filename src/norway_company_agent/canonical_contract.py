from __future__ import annotations

from collections import defaultdict
from typing import Any

CANONICAL_SCHEMA_VERSION = "signalpost.canonical.v1"

# These aliases deliberately describe evaluator-facing concepts rather than
# collector modules. The original claims[] envelope remains the source of truth.
FIELD_ALIASES = {
    "legal_name": "company.legal_name",
    "legal_form": "company.legal_form",
    "municipality": "company.municipality",
    "industry": "company.industry",
    "employee_count": "company.employee_count",
    "business_address": "company.business_address",
    "postal_address": "company.postal_address",
    "bankrupt": "company.bankrupt",
    "liquidating": "company.liquidating",
    "latest_submitted_accounts": "accounts.latest_submitted",
    "accounting_obligation": "accounts.accounting_obligation",
    "official_website": "web.official_website",
    "company_description": "web.company_description",
    "external.contact_email": "web.contact_email",
    "external.profile_handle": "web.social_profile",
    "external.workforce_snapshot": "workforce.snapshot",
    "group_structure": "company.group_structure",
    "roles": "people.role",
    "locations": "locations.location",
    "financial.revenue": "accounts.revenue",
    "financial.operating_result": "accounts.operating_result",
    "financial.profit_before_tax": "accounts.profit_before_tax",
    "financial.annual_result": "accounts.annual_result",
    "financial.assets": "accounts.assets",
    "financial.equity": "accounts.equity",
    "financial.debt": "accounts.debt",
}


def _fact_from_claim(claim: dict[str, Any], *, canonical_field: str, value: Any | None = None) -> dict[str, Any]:
    fact = {
        "field": canonical_field,
        "value": claim.get("value") if value is None else value,
        "availability": claim.get("availability"),
        "confidence": claim.get("confidence"),
        "evidence_ids": list(claim.get("evidence_ids") or []),
    }
    for key in ("currency", "reporting_period", "platform", "signal_type", "claim_scope"):
        if claim.get(key) is not None:
            fact[key] = claim[key]
    return fact


def _split_values(claim: dict[str, Any]) -> list[Any]:
    """Split list-valued canonical families without inventing new information."""
    if claim.get("availability") != "available":
        return [None]
    value = claim.get("value")
    if isinstance(value, list):
        return value or [None]
    if isinstance(value, dict):
        for key in ("roles", "locations", "items", "records"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested or [None]
    return [value]


def _canonical_facts(item: dict[str, Any]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for claim in item.get("claims") or []:
        field = str(claim.get("field") or "")
        canonical_field = FIELD_ALIASES.get(field)
        if not canonical_field:
            continue
        if field in {"roles", "locations"}:
            for value in _split_values(claim):
                facts.append(_fact_from_claim(claim, canonical_field=canonical_field, value=value))
        else:
            facts.append(_fact_from_claim(claim, canonical_field=canonical_field))
    return facts


def _available_values(facts: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    return [fact for fact in facts if fact.get("field") == field and fact.get("availability") == "available"]


def _first(facts: list[dict[str, Any]], field: str) -> dict[str, Any] | None:
    matches = [fact for fact in facts if fact.get("field") == field]
    return matches[0] if matches else None


def project_canonical_contract(item: dict[str, Any]) -> dict[str, Any]:
    """Add a scorer/product-friendly view over final evidence-backed claims.

    This is intentionally a projection, not a second truth store: no value is
    generated unless it already exists in claims[], and evidence ids are copied
    verbatim so provenance remains one hop away.
    """
    facts = _canonical_facts(item)
    financial_fields = (
        "accounts.revenue",
        "accounts.operating_result",
        "accounts.profit_before_tax",
        "accounts.annual_result",
        "accounts.assets",
        "accounts.equity",
        "accounts.debt",
    )
    financials: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for field in financial_fields:
        financials[field.removeprefix("accounts.")] = [fact for fact in facts if fact.get("field") == field]

    canonical = {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "organisation_number": str(item.get("organisation_number") or ""),
        "company": {
            "legal_name": _first(facts, "company.legal_name"),
            "legal_form": _first(facts, "company.legal_form"),
            "municipality": _first(facts, "company.municipality"),
            "industry": _first(facts, "company.industry"),
            "employee_count": _first(facts, "company.employee_count"),
            "business_address": _first(facts, "company.business_address"),
            "postal_address": _first(facts, "company.postal_address"),
            "bankrupt": _first(facts, "company.bankrupt"),
            "liquidating": _first(facts, "company.liquidating"),
            "group_structure": _first(facts, "company.group_structure"),
        },
        "accounts": {
            "latest_submitted": _first(facts, "accounts.latest_submitted"),
            "accounting_obligation": _first(facts, "accounts.accounting_obligation"),
            "financials": dict(financials),
        },
        "people": _available_values(facts, "people.role"),
        "locations": _available_values(facts, "locations.location"),
        "workforce": _available_values(facts, "workforce.snapshot"),
        "web": {
            "official_website": _first(facts, "web.official_website"),
            "company_description": _first(facts, "web.company_description"),
            "contact_emails": _available_values(facts, "web.contact_email"),
            "social_profiles": _available_values(facts, "web.social_profile"),
        },
        # Reserved explicit families. They stay empty until the pipeline has a
        # concrete dated activity item or role/apply action. A generic careers
        # page is never promoted to hiring.
        "public_activity": [],
        "hiring": [],
        "facts": facts,
    }
    item["canonical"] = canonical
    return item


def validate_canonical_contract(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    canonical = item.get("canonical")
    if not isinstance(canonical, dict):
        return ["missing canonical projection"]
    if canonical.get("schema_version") != CANONICAL_SCHEMA_VERSION:
        errors.append("canonical schema version mismatch")
    if str(canonical.get("organisation_number") or "") != str(item.get("organisation_number") or ""):
        errors.append("canonical organisation number mismatch")

    evidence_ids = {str(entry.get("id")) for entry in item.get("evidence") or [] if entry.get("id")}
    source_claim_fingerprints = {
        (
            FIELD_ALIASES.get(str(claim.get("field") or "")),
            str(claim.get("availability")),
            tuple(str(eid) for eid in claim.get("evidence_ids") or []),
        )
        for claim in item.get("claims") or []
        if FIELD_ALIASES.get(str(claim.get("field") or ""))
    }
    for fact in canonical.get("facts") or []:
        field = str(fact.get("field") or "")
        refs = tuple(str(eid) for eid in fact.get("evidence_ids") or [])
        if not field:
            errors.append("canonical fact missing field")
        if fact.get("availability") == "available" and not refs:
            errors.append(f"canonical fact {field} lacks evidence ids")
        for evidence_id in refs:
            if evidence_id not in evidence_ids:
                errors.append(f"canonical fact {field} references missing evidence {evidence_id}")
        fingerprint = (field, str(fact.get("availability")), refs)
        if fingerprint not in source_claim_fingerprints:
            errors.append(f"canonical fact {field} has no source claim")

    if canonical.get("hiring"):
        errors.append("canonical hiring must remain empty until concrete job facts are projected")
    return errors
