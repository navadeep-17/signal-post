from __future__ import annotations

from typing import Any

SYNTHESIS_SCHEMA_VERSION = "signalpost-synthesis-v2.1"


def _facts_by_type(contract: dict[str, Any], fact_type: str) -> list[dict[str, Any]]:
    return [
        item
        for item in (contract.get("canonical_facts") or [])
        if item.get("type") == fact_type and item.get("availability") == "available"
    ]


def _first(contract: dict[str, Any], fact_type: str) -> dict[str, Any] | None:
    facts = _facts_by_type(contract, fact_type)
    return facts[0] if facts else None


def _latest(contract: dict[str, Any], fact_type: str) -> dict[str, Any] | None:
    facts = _facts_by_type(contract, fact_type)
    if not facts:
        return None
    return sorted(
        facts,
        key=lambda item: (
            str((item.get("period") or {}).get("end") or ""),
            str((item.get("period") or {}).get("start") or ""),
        ),
        reverse=True,
    )[0]


def _evidence_ids(facts: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for fact in facts:
        for evidence_id in fact.get("evidence_ids") or []:
            text = str(evidence_id)
            if text and text not in result:
                result.append(text)
    return result


def _section(key: str, title: str, text: str, facts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "text": text,
        "evidence_ids": _evidence_ids(facts),
    }


def _period_end(fact: dict[str, Any] | None) -> str | None:
    if not fact:
        return None
    period = fact.get("period") or {}
    return str(period.get("end") or "").strip() or None


def _currency_amount(fact: dict[str, Any] | None) -> str | None:
    if not fact:
        return None
    value = fact.get("value")
    if isinstance(value, dict):
        amount = value.get("amount")
        currency = str(value.get("currency") or "").strip()
        if amount is not None:
            return f"{amount:,}{f' {currency}' if currency else ''}"
    if value is not None:
        return str(value)
    return None


def _workforce_text(fact: dict[str, Any] | None) -> str | None:
    if not fact:
        return None
    value = fact.get("value") or {}
    if isinstance(value, dict):
        numeric = value.get("value")
        unit = str(value.get("unit") or "").strip()
        effective_at = str(value.get("effective_at") or "").strip()
        if numeric is not None:
            suffix = f" {unit}" if unit else ""
            date = f" as of {effective_at}" if effective_at else ""
            return f"{numeric}{suffix}{date}"
    return str(value) if value not in (None, "") else None


def _industry_text(value: Any) -> str | None:
    if not isinstance(value, dict):
        return str(value) if value not in (None, "") else None
    primary = value.get("primary") or {}
    code = str(primary.get("code") or "").strip()
    description = str(primary.get("description") or "").strip()
    if code or description:
        return " — ".join(part for part in [code, description] if part)
    return None


def _leader(contract: dict[str, Any]) -> dict[str, Any] | None:
    roles = _facts_by_type(contract, "person_role")
    if not roles:
        return None
    priority = ("DAGL", "LEDE", "CEO", "STYR", "BEST")
    for role_code in priority:
        for fact in roles:
            value = fact.get("value") or {}
            if str(value.get("role_code") or "").upper() == role_code:
                return fact
    return roles[0]


def _registry_change_sort_key(fact: dict[str, Any]) -> tuple[str, str, str]:
    value = fact.get("value") or {}
    if not isinstance(value, dict):
        return ("", "", "")
    return (
        str(value.get("effective_at") or ""),
        str(value.get("registered_at") or ""),
        str(value.get("source_event_id") or ""),
    )


def _fact_trace(fact: dict[str, Any], evidence_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    reporting = fact.get("reporting_period") or fact.get("period")
    for evidence_id in fact.get("evidence_ids") or []:
        evidence = evidence_by_id.get(str(evidence_id))
        if not evidence:
            continue
        traces.append(
            {
                "evidence_id": str(evidence_id),
                "source_url": evidence.get("source_url"),
                "source_class": evidence.get("source_class"),
                "retrieved_at": evidence.get("retrieved_at"),
                "effective_at": evidence.get("effective_at") or fact.get("effective_at"),
                "reporting_period": reporting,
                "claim_span": evidence.get("claim_span"),
                "content_sha256": evidence.get("content_sha256"),
            }
        )
    return traces


def _decision_item(
    key: str,
    text: str,
    facts: list[dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for fact in facts:
        for trace in _fact_trace(fact, evidence_by_id):
            marker = (str(trace.get("evidence_id") or ""), str(trace.get("source_url") or ""))
            if marker in seen:
                continue
            seen.add(marker)
            evidence.append(trace)
    return {"key": key, "text": text, "evidence": evidence}


def build_company_synthesis(contract: dict[str, Any]) -> dict[str, Any]:
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
    careers_pages = _facts_by_type(contract, "careers_page")
    jobs = _facts_by_type(contract, "job_posting")
    updates = _facts_by_type(contract, "company_update")
    social = _facts_by_type(contract, "social_profile")
    registry_changes = sorted(
        _facts_by_type(contract, "registry_change"),
        key=_registry_change_sort_key,
        reverse=True,
    )
    evidence_by_id = {
        str(item.get("id")): item
        for item in (contract.get("evidence") or [])
        if isinstance(item, dict) and item.get("id")
    }

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
    if careers_pages:
        external_bits.append(f"Verified company-owned careers surfaces published: {len(careers_pages)}.")
        external_facts.extend(careers_pages)
    if jobs:
        external_bits.append(f"Strict job postings published: {len(jobs)}.")
        external_facts.extend(jobs)
    elif careers_pages:
        external_bits.append("No specific active job posting is independently verified for this run.")
    else:
        # Preserve the established evaluator-facing wording when no new M2C evidence exists.
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
    if not careers_pages and not jobs:
        unknowns.append("No strict job posting is published.")
    elif careers_pages and not jobs:
        unknowns.append("A verified careers surface is published, but no specific active job posting is independently verified.")
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

    company_name = str((name or {}).get("value") or contract.get("organisation_number") or "Unknown company")
    industry_text = _industry_text((industry or {}).get("value"))
    company_intro = f"{company_name} (Org.nr {contract.get('organisation_number')})"
    if industry_text:
        company_intro += f" is registered in {industry_text}"
    if municipality:
        company_intro += f" in {municipality.get('value')}"
    company_intro += "."

    size_parts: list[str] = []
    if workforce_text:
        size_parts.append(f"workforce {workforce_text}")
    if revenue_text:
        size_parts.append(f"revenue {revenue_text}")
    if operating_text:
        size_parts.append(f"operating result {operating_text}")
    size_text = "; ".join(size_parts).capitalize() + "." if size_parts else "No qualified size metric is published."

    leader_text = organisation_bits[0] if leader else "No qualified current leadership fact is published."
    if jobs:
        hiring_text = f"{len(jobs)} strict job posting(s) are published."
        if careers_pages:
            hiring_text += f" {len(careers_pages)} verified company-owned careers surface(s) are also published."
    elif careers_pages:
        hiring_text = (
            f"{len(careers_pages)} verified company-owned careers surface(s) are published; "
            "no specific active job posting is independently verified."
        )
    else:
        hiring_text = "No strict job posting is published for this run. No verified careers surface is published."
    footprint_parts: list[str] = []
    if website:
        footprint_parts.append(f"verified website {website.get('value')}")
    if social:
        footprint_parts.append(f"{len(social)} company-declared social profile(s)")
    if updates:
        footprint_parts.append(f"{len(updates)} dated company update(s)")
    digital_text = "; ".join(footprint_parts).capitalize() + "." if footprint_parts else "No qualified external digital-footprint fact is published."

    decision_brief = {
        "what_is_this_company": _decision_item("what_is_this_company", company_intro, [fact for fact in [name, industry, municipality] if fact], evidence_by_id),
        "what_does_it_do": _decision_item("what_does_it_do", " ".join(identity_bits), identity_facts, evidence_by_id),
        "how_big_is_it": _decision_item("how_big_is_it", size_text, [fact for fact in [workforce, revenue, operating] if fact], evidence_by_id),
        "who_runs_it": _decision_item("who_runs_it", leader_text, [leader] if leader else [], evidence_by_id),
        "hiring": _decision_item("hiring", hiring_text, [*careers_pages, *jobs], evidence_by_id),
        "digital_footprint": _decision_item("digital_footprint", digital_text, [fact for fact in [website, *social, *updates] if fact], evidence_by_id),
        "what_changed": {
            "key": "what_changed",
            "text": change_text,
            "evidence": [
                trace
                for fact in registry_changes[:3]
                for trace in _fact_trace(fact, evidence_by_id)
            ],
        },
        "what_is_unknown": list(dict.fromkeys(unknowns)),
    }

    return {
        "schema_version": SYNTHESIS_SCHEMA_VERSION,
        "organisation_number": str(contract.get("organisation_number") or ""),
        "company_name": (name or {}).get("value"),
        "sections": sections,
        "what_changed": what_changed,
        "unknowns": unknowns,
        "decision_brief": decision_brief,
        "evidence_ids": all_evidence,
        "deterministic": True,
        "llm_used": False,
        "new_facts_created": False,
    }


def validate_company_synthesis(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    synthesis = contract.get("synthesis")
    if not isinstance(synthesis, dict):
        return ["missing synthesis"]
    if synthesis.get("schema_version") != SYNTHESIS_SCHEMA_VERSION:
        errors.append("unexpected synthesis schema version")
    if synthesis.get("deterministic") is not True or synthesis.get("llm_used") is not False:
        errors.append("synthesis must remain deterministic and non-LLM")
    if synthesis.get("new_facts_created") is not False:
        errors.append("synthesis must not claim to create new facts")
    evidence_ids = {str(item.get("id")) for item in (contract.get("evidence") or []) if item.get("id")}
    for section in synthesis.get("sections") or []:
        for evidence_id in section.get("evidence_ids") or []:
            if str(evidence_id) not in evidence_ids:
                errors.append(f"synthesis evidence id missing: {evidence_id}")
    for evidence_id in synthesis.get("evidence_ids") or []:
        if str(evidence_id) not in evidence_ids:
            errors.append(f"top-level synthesis evidence id missing: {evidence_id}")
    decision_brief = synthesis.get("decision_brief")
    if not isinstance(decision_brief, dict):
        errors.append("missing decision_brief")
        return errors
    required = {
        "what_is_this_company",
        "what_does_it_do",
        "how_big_is_it",
        "who_runs_it",
        "hiring",
        "digital_footprint",
        "what_changed",
        "what_is_unknown",
    }
    if set(decision_brief) != required:
        errors.append("decision_brief keys do not match required evaluator-facing sections")
    for key in required - {"what_is_unknown"}:
        item = decision_brief.get(key)
        if not isinstance(item, dict) or not str(item.get("text") or "").strip():
            errors.append(f"decision_brief.{key} missing text")
            continue
        for trace in item.get("evidence") or []:
            evidence_id = str(trace.get("evidence_id") or "")
            if evidence_id not in evidence_ids:
                errors.append(f"decision_brief.{key} evidence id missing: {evidence_id}")
            if not str(trace.get("source_url") or "").strip():
                errors.append(f"decision_brief.{key} evidence missing source_url")
            if not str(trace.get("retrieved_at") or "").strip():
                errors.append(f"decision_brief.{key} evidence missing retrieved_at")
            if not str(trace.get("claim_span") or "").strip():
                errors.append(f"decision_brief.{key} evidence missing claim_span")
            if not str(trace.get("content_sha256") or "").strip():
                errors.append(f"decision_brief.{key} evidence missing content_sha256")
    unknowns = decision_brief.get("what_is_unknown")
    if not isinstance(unknowns, list):
        errors.append("decision_brief.what_is_unknown must be a list")
    return errors
