from __future__ import annotations

import json
from collections import defaultdict
from typing import Any


CANONICAL_SCHEMA_VERSION = "signalpost-canonical-v2"


def _claim_index(contract: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in contract.get("claims") or []:
        if isinstance(claim, dict) and claim.get("field"):
            index[str(claim["field"])].append(claim)
    return index


def _fact(
    fact_type: str,
    claim: dict[str, Any],
    *,
    value: Any | None = None,
    ordinal: int | None = None,
) -> dict[str, Any]:
    item = {
        "type": fact_type,
        "value": claim.get("value") if value is None else value,
        "availability": claim.get("availability"),
        "confidence": claim.get("confidence"),
        "evidence_ids": list(claim.get("evidence_ids") or []),
    }
    for key in ("currency", "reporting_period", "platform", "claim_scope", "signal_type", "observation_id"):
        if claim.get(key) is not None:
            item[key] = claim.get(key)
    if ordinal is not None:
        item["ordinal"] = ordinal
    return item


def _first(index: dict[str, list[dict[str, Any]]], field: str) -> dict[str, Any] | None:
    rows = index.get(field) or []
    return rows[0] if rows else None


def _available(claim: dict[str, Any] | None) -> bool:
    return bool(claim and claim.get("availability") == "available")


def _normalize_industry(value: Any) -> dict[str, Any] | Any:
    if not isinstance(value, dict):
        return value
    return {
        "code": value.get("kode") or value.get("code"),
        "description": value.get("beskrivelse") or value.get("description"),
    }


def _flatten_roles(claim: dict[str, Any]) -> list[dict[str, Any]]:
    if not _available(claim):
        return []
    value = claim.get("value") or {}
    rows = value.get("roles") if isinstance(value, dict) else None
    if not isinstance(rows, list):
        return []
    facts: list[dict[str, Any]] = []
    for ordinal, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        # Keep inactive rows explicit instead of silently deleting history. The canonical
        # value exposes the source's inactive flag so a scorer/product can distinguish it.
        facts.append(_fact("person_role", claim, value=dict(row), ordinal=ordinal))
    return facts


def _flatten_locations(claim: dict[str, Any]) -> list[dict[str, Any]]:
    if not _available(claim):
        return []
    value = claim.get("value") or {}
    rows = value.get("locations") if isinstance(value, dict) else None
    if not isinstance(rows, list):
        return []
    facts: list[dict[str, Any]] = []
    for ordinal, row in enumerate(rows):
        if isinstance(row, dict):
            facts.append(_fact("registered_location", claim, value=dict(row), ordinal=ordinal))
    return facts


def project_canonical_profile(contract: dict[str, Any]) -> dict[str, Any]:
    """Add an evaluator-friendly canonical projection without changing source claims.

    Builderr feedback on the first 700-company diagnostic indicated that the generic
    claims envelope was not being mapped into enough canonical official/external facts.
    This layer is deliberately zero-network and lossless: it only normalizes already-
    published claims and reuses their evidence IDs. Existing ``claims`` and ``evidence``
    remain the source of truth and are left untouched.
    """

    index = _claim_index(contract)
    facts: list[dict[str, Any]] = []

    scalar_mapping = (
        ("legal_name", "company_name"),
        ("legal_form", "legal_form"),
        ("municipality", "municipality"),
        ("employee_count", "registered_employee_count"),
        ("latest_submitted_accounts", "latest_submitted_accounts"),
        ("accounting_obligation", "accounting_obligation"),
        ("group_structure", "group_structure"),
        ("official_website", "website"),
        ("company_description", "company_description"),
    )
    for field, fact_type in scalar_mapping:
        claim = _first(index, field)
        if claim is not None:
            facts.append(_fact(fact_type, claim))

    industry = _first(index, "industry")
    if industry is not None:
        facts.append(_fact("industry", industry, value=_normalize_industry(industry.get("value"))))

    for key in (
        "revenue",
        "operating_result",
        "profit_before_tax",
        "annual_result",
        "assets",
        "equity",
        "debt",
    ):
        for claim in index.get(f"financial.{key}") or []:
            facts.append(_fact(f"financial_{key}", claim))

    roles = _first(index, "roles")
    if roles is not None:
        facts.extend(_flatten_roles(roles))

    locations = _first(index, "locations")
    if locations is not None:
        facts.extend(_flatten_locations(locations))

    for claim in index.get("external.profile_handle") or []:
        facts.append(_fact("social_profile", claim))
    for claim in index.get("external.contact_email") or []:
        facts.append(_fact("contact_email", claim))
    for claim in index.get("external.workforce_snapshot") or []:
        facts.append(_fact("workforce_snapshot", claim))

    company_keys = {
        "company_name",
        "legal_form",
        "municipality",
        "industry",
        "registered_employee_count",
        "latest_submitted_accounts",
        "accounting_obligation",
        "group_structure",
    }
    external_keys = {"website", "company_description", "social_profile", "contact_email", "workforce_snapshot"}

    canonical = {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "organisation_number": str(contract.get("organisation_number") or ""),
        "company_record": [item for item in facts if item["type"] in company_keys],
        "financials": [item for item in facts if str(item["type"]).startswith("financial_")],
        "people": [item for item in facts if item["type"] == "person_role"],
        "locations": [item for item in facts if item["type"] == "registered_location"],
        "company_website": [item for item in facts if item["type"] in external_keys],
        # Jobs and dated public activity remain intentionally empty until a strict real-role
        # or dated-activity extractor qualifies them. A generic careers page is never hiring.
        "jobs": [],
        "public_activity": [],
    }
    canonical["data_areas"] = {
        "company_record": bool(canonical["company_record"]),
        "financials": bool(canonical["financials"]),
        "people_and_locations": bool(canonical["people"] or canonical["locations"]),
        "company_website": any(item.get("availability") == "available" for item in canonical["company_website"]),
        "hiring_and_public_activity": bool(canonical["jobs"] or canonical["public_activity"]),
    }

    return {
        **contract,
        "canonical_facts": facts,
        "canonical_profile": canonical,
    }


def _stable_fact_key(item: dict[str, Any]) -> str:
    return json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def validate_canonical_projection(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    org = str(contract.get("organisation_number") or "")
    canonical = contract.get("canonical_profile")
    facts = contract.get("canonical_facts")
    if not isinstance(canonical, dict):
        return ["missing canonical_profile"]
    if canonical.get("schema_version") != CANONICAL_SCHEMA_VERSION:
        errors.append("unexpected canonical schema version")
    if str(canonical.get("organisation_number") or "") != org:
        errors.append("canonical organisation number mismatch")
    if not isinstance(facts, list):
        return errors + ["canonical_facts must be a list"]

    evidence_ids = {str(item.get("id")) for item in contract.get("evidence") or [] if isinstance(item, dict) and item.get("id")}
    for position, fact in enumerate(facts):
        if not isinstance(fact, dict):
            errors.append(f"canonical fact {position} is not an object")
            continue
        if not fact.get("type"):
            errors.append(f"canonical fact {position} missing type")
        refs = fact.get("evidence_ids") or []
        if not refs:
            errors.append(f"canonical fact {position} lacks evidence ids")
        for ref in refs:
            if str(ref) not in evidence_ids:
                errors.append(f"canonical fact {position} references missing evidence {ref}")
        if fact.get("availability") != "available" and fact.get("value") is not None:
            errors.append(f"canonical fact {position} has value while unavailable")

    flattened: list[dict[str, Any]] = []
    for key in ("company_record", "financials", "people", "locations", "company_website", "jobs", "public_activity"):
        rows = canonical.get(key)
        if not isinstance(rows, list):
            errors.append(f"canonical_profile.{key} must be a list")
            continue
        flattened.extend(rows)
    if sorted(_stable_fact_key(item) for item in flattened) != sorted(_stable_fact_key(item) for item in facts):
        errors.append("canonical profile categories do not losslessly partition canonical_facts")
    return errors
