from __future__ import annotations

from typing import Any

SYNTHESIS_SCHEMA_VERSION = "signalpost-synthesis-v1"


def _available_facts(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        fact
        for fact in (contract.get("canonical_facts") or [])
        if isinstance(fact, dict) and fact.get("availability") == "available"
    ]


def _facts_by_type(contract: dict[str, Any], fact_type: str) -> list[dict[str, Any]]:
    return [fact for fact in _available_facts(contract) if fact.get("type") == fact_type]


def _first(contract: dict[str, Any], fact_type: str) -> dict[str, Any] | None:
    rows = _facts_by_type(contract, fact_type)
    return rows[0] if rows else None


def _period_end(fact: dict[str, Any]) -> str:
    period = fact.get("reporting_period")
    if isinstance(period, dict):
        return str(period.get("tilDato") or period.get("end") or period.get("year") or "")
    return str(period or "")


def _latest(contract: dict[str, Any], fact_type: str) -> dict[str, Any] | None:
    rows = _facts_by_type(contract, fact_type)
    if not rows:
        return None
    return sorted(rows, key=lambda fact: (_period_end(fact), str(fact.get("value"))), reverse=True)[0]


def _evidence_ids(*facts: dict[str, Any] | None) -> list[str]:
    values: list[str] = []
    for fact in facts:
        if not fact:
            continue
        for evidence_id in fact.get("evidence_ids") or []:
            text = str(evidence_id)
            if text and text not in values:
                values.append(text)
    return values


def _industry_text(value: Any) -> str | None:
    if isinstance(value, dict):
        description = str(value.get("description") or value.get("beskrivelse") or "").strip()
        code = str(value.get("code") or value.get("kode") or "").strip()
        if description and code:
            return f"{description} ({code})"
        return description or code or None
    text = str(value or "").strip()
    return text or None


def _currency_amount(fact: dict[str, Any] | None) -> str | None:
    if not fact:
        return None
    value = fact.get("value")
    if value is None:
        return None
    currency = str(fact.get("currency") or "").strip()
    try:
        amount = f"{float(value):,.0f}"
    except (TypeError, ValueError):
        amount = str(value)
    return f"{amount} {currency}".strip()


def _workforce_text(fact: dict[str, Any] | None) -> str | None:
    if not fact:
        return None
    value = fact.get("value")
    if isinstance(value, dict):
        measure = str(value.get("measure") or "workforce").replace("_", " ")
        number = value.get("value")
        if number is not None:
            return f"{number} {measure}"
    return str(value) if value is not None else None


def _leader(contract: dict[str, Any]) -> dict[str, Any] | None:
    roles = _facts_by_type(contract, "person_role")
    if not roles:
        return None
    priority = {"DAGL": 0, "LEDE": 1}

    def key(fact: dict[str, Any]) -> tuple[int, str]:
        value = fact.get("value") or {}
        code = str(value.get("role_code") or "") if isinstance(value, dict) else ""
        return (priority.get(code, 9), str(value.get("name") or "") if isinstance(value, dict) else "")

    return sorted(roles, key=key)[0]


def _section(key: str, title: str, text: str, facts: list[dict[str, Any]]) -> dict[str, Any]:
    ids: list[str] = []
    source_fields: list[str] = []
    for fact in facts:
        for evidence_id in fact.get("evidence_ids") or []:
            value = str(evidence_id)
            if value and value not in ids:
                ids.append(value)
        source_field = str(fact.get("source_field") or "")
        if source_field and source_field not in source_fields:
            source_fields.append(source_field)
    return {
        "key": key,
        "title": title,
        "text": text,
        "evidence_ids": ids,
        "source_fields": source_fields,
    }


def _registry_change_sort_key(fact: dict[str, Any]) -> tuple[str, str]:
    value = fact.get("value") or {}
    if not isinstance(value, dict):
        return ("", "")
    return (str(value.get("effective_at") or ""), str(value.get("event_id") or ""))


def build_company_synthesis(contract: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic, zero-network brief from already-published canonical facts.

    The synthesis never adds a new fact. Each positive statement is derived from canonical
    facts that already carry evidence. Missing/unknown statements are explicit boundaries,
    not inferences about the company. Official registry changes remain explicitly labelled
    as registry events rather than being presented as company-authored public activity.
    """

    name = _first(contract, "company_name")
    description = _first(contract, "company_description")
    industry = _first(contract, "industry")
    municipality = _first(contract, "municipality")
    revenue = _latest(contract, "financial_revenue")
    operating = _latest(contract, "financial_operating_result")
    leader = _leader(contract)
    locations = _facts_by_type(contract, "registered_location")
    workforce = _first(contract, "workforce_snapshot")
    website = _first(contract, "website")
    jobs = _facts_by_type(contract, "job_posting")
    updates = _facts_by_type(contract, "company_update")
    social = _facts_by_type(contract, "social_profile")
    registry_changes = sorted(
        _facts_by_type(contract, "registry_change"),
        key=_registry_change_sort_key,
        reverse=True,
    )

    identity_bits: list[str] = []
    identity_facts: list[dict[str, Any]] = []
    if description:
        identity_bits.append(str(description.get("value")))
        identity_facts.append(description)
    else:
        industry_text = _industry_text((industry or {}).get("value"))
        if industry_text:
            identity_bits.append(f"Registered industry: {industry_text}.")
            identity_facts.append(industry)  # type: ignore[arg-type]
    if municipality:
        identity_bits.append(f"Registered municipality: {municipality.get('value')}.")
        identity_facts.append(municipality)
    if not identity_bits:
        identity_bits.append("No qualified business description or industry summary is published for this company.")

    financial_bits: list[str] = []
    financial_facts: list[dict[str, Any]] = []
    revenue_text = _currency_amount(revenue)
    operating_text = _currency_amount(operating)
    if revenue_text:
        financial_bits.append(f"Latest published revenue: {revenue_text}")
        if _period_end(revenue):
            financial_bits[-1] += f" for period ending {_period_end(revenue)}"
        financial_bits[-1] += "."
        financial_facts.append(revenue)  # type: ignore[arg-type]
    if operating_text:
        financial_bits.append(f"Latest published operating result: {operating_text}")
        if _period_end(operating):
            financial_bits[-1] += f" for period ending {_period_end(operating)}"
        financial_bits[-1] += "."
        financial_facts.append(operating)  # type: ignore[arg-type]
    if not financial_bits:
        financial_bits.append("No qualified revenue or operating-result fact is published for this company.")

    organisation_bits: list[str] = []
    organisation_facts: list[dict[str, Any]] = []
    if leader:
        value = leader.get("value") or {}
        if isinstance(value, dict):
            person_name = str(value.get("name") or "").strip()
            role = str(value.get("role") or value.get("role_code") or "").strip()
            if person_name:
                organisation_bits.append(f"Current published leadership: {person_name}{f' — {role}' if role else ''}.")
                organisation_facts.append(leader)
    if locations:
        organisation_bits.append(f"Registered workplaces published: {len(locations)}.")
        organisation_facts.extend(locations)
    workforce_text = _workforce_text(workforce)
    if workforce_text:
        organisation_bits.append(f"Latest workforce snapshot: {workforce_text}.")
        organisation_facts.append(workforce)  # type: ignore[arg-type]
    if not organisation_bits:
        organisation_bits.append("No qualified current leadership, registered workplace, or workforce fact is published.")

    external_bits: list[str] = []
    external_facts: list[dict[str, Any]] = []
    if website:
        external_bits.append(f"Verified company website: {website.get('value')}.")
        external_facts.append(website)
    if jobs:
        external_bits.append(f"Strict job postings published: {len(jobs)}.")
        external_facts.extend(jobs)
    else:
        external_bits.append("No strict job posting is published for this run.")
    if updates:
        external_bits.append(f"Dated company updates published: {len(updates)}.")
        external_facts.extend(updates)
    else:
        external_bits.append("No dated company update is published for this run.")
    if social:
        external_bits.append(f"Company-declared social profiles published: {len(social)}.")
        external_facts.extend(social)

    changes = [item for item in (contract.get("changes") or []) if isinstance(item, dict)]
    change_evidence_ids: list[str] = []
    registry_change_values: list[dict[str, Any]] = []
    if changes:
        change_text = "; ".join(
            f"{item.get('field')}: {item.get('previous_value')} → {item.get('current_value')}"
            for item in changes[:5]
        )
        if len(changes) > 5:
            change_text += f"; plus {len(changes) - 5} more material change(s)"
        change_text += "."
    elif registry_changes:
        parts: list[str] = []
        for fact in registry_changes[:3]:
            value = fact.get("value") or {}
            if not isinstance(value, dict):
                continue
            effective_at = str(value.get("effective_at") or "")
            date = effective_at[:10] if effective_at else "date unknown"
            summary = str(value.get("summary") or "").strip()
            if not summary:
                continue
            parts.append(f"{date}: official BRREG registry change — {summary}")
            registry_change_values.append(dict(value))
            for evidence_id in fact.get("evidence_ids") or []:
                text = str(evidence_id)
                if text and text not in change_evidence_ids:
                    change_evidence_ids.append(text)
        change_text = "; ".join(parts) + "." if parts else (
            "No material change is published for this run; this does not imply that nothing changed outside checked sources."
        )
    else:
        change_text = "No material change is published for this run; this does not imply that nothing changed outside checked sources."

    profile = contract.get("canonical_profile") or {}
    data_areas = profile.get("data_areas") or {}
    unknowns: list[str] = []
    area_labels = {
        "company_record": "company record",
        "financials": "financials",
        "people_and_locations": "people or registered locations",
        "company_website": "verified company website",
        "hiring_and_public_activity": "qualified hiring/public activity",
    }
    for key, label in area_labels.items():
        if not data_areas.get(key):
            unknowns.append(f"No qualified {label} fact is published.")
    if not jobs:
        unknowns.append("No strict job posting is published.")
    if not updates:
        unknowns.append("No dated company update is published.")

    sections = [
        _section("company", "What the company does", " ".join(identity_bits), identity_facts),
        _section("financials", "Financial snapshot", " ".join(financial_bits), financial_facts),
        _section("organisation", "People & footprint", " ".join(organisation_bits), organisation_facts),
        _section("external", "Website & public activity", " ".join(external_bits), external_facts),
    ]
    all_evidence: list[str] = []
    for section in sections:
        for evidence_id in section["evidence_ids"]:
            if evidence_id not in all_evidence:
                all_evidence.append(evidence_id)
    for evidence_id in change_evidence_ids:
        if evidence_id not in all_evidence:
            all_evidence.append(evidence_id)

    effective_change_count = len(changes) if changes else len(registry_change_values)
    what_changed: dict[str, Any] = {
        "text": change_text,
        "change_count": effective_change_count,
        "changes": changes,
    }
    # Preserve the exact pre-V5 synthesis shape for historical/certified contracts that do
    # not contain registry-change facts. This keeps the committed certified product artifact
    # byte-for-byte reproducible while exposing the richer provenance only on new V5 output.
    if registry_change_values:
        what_changed.update(
            {
                "registry_changes": registry_change_values,
                "evidence_ids": change_evidence_ids,
                "source_boundary": (
                    "registry_changes are official BRREG registry events, not company-authored news or social activity"
                ),
            }
        )

    return {
        "schema_version": SYNTHESIS_SCHEMA_VERSION,
        "organisation_number": str(contract.get("organisation_number") or ""),
        "company_name": (name or {}).get("value"),
        "sections": sections,
        "what_changed": what_changed,
        "unknowns": unknowns,
        "evidence_ids": all_evidence,
        "generation": {
            "mode": "deterministic_zero_network",
            "llm_used": False,
            "new_facts_created": False,
        },
    }


def validate_company_synthesis(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    synthesis = contract.get("synthesis")
    if not isinstance(synthesis, dict):
        return ["missing synthesis"]
    if synthesis.get("schema_version") != SYNTHESIS_SCHEMA_VERSION:
        errors.append("unexpected synthesis schema version")
    if str(synthesis.get("organisation_number") or "") != str(contract.get("organisation_number") or ""):
        errors.append("synthesis organisation number mismatch")
    generation = synthesis.get("generation") or {}
    if generation.get("mode") != "deterministic_zero_network" or generation.get("llm_used") is not False:
        errors.append("synthesis generation declaration is invalid")
    if generation.get("new_facts_created") is not False:
        errors.append("synthesis must not declare new facts")

    available_evidence = {
        str(item.get("id"))
        for item in (contract.get("evidence") or [])
        if isinstance(item, dict) and item.get("id")
    }
    for section in synthesis.get("sections") or []:
        if not isinstance(section, dict) or not section.get("text"):
            errors.append("synthesis section missing text")
            continue
        for evidence_id in section.get("evidence_ids") or []:
            if str(evidence_id) not in available_evidence:
                errors.append(f"synthesis references missing evidence {evidence_id}")
    what_changed = synthesis.get("what_changed") or {}
    for evidence_id in what_changed.get("evidence_ids") or []:
        if str(evidence_id) not in available_evidence:
            errors.append(f"synthesis what_changed references missing evidence {evidence_id}")
    for evidence_id in synthesis.get("evidence_ids") or []:
        if str(evidence_id) not in available_evidence:
            errors.append(f"synthesis evidence list references missing evidence {evidence_id}")
    return errors
