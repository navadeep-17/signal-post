from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

ALLOWED_AVAILABILITY = {
    "available",
    "not_available",
    "blocked",
    "not_applicable",
    "ambiguous",
    "failed",
}

STATUS_TO_AVAILABILITY = {
    "available": "available",
    "not_found": "not_available",
    "blocked": "blocked",
    "not_applicable": "not_applicable",
    "source_error": "failed",
}

CORE_PROFILE_FIELDS = (
    ("legal_name", "name"),
    ("legal_form", "legal_form"),
    ("employee_count", "employees"),
    ("municipality", "municipality"),
    ("industry", "industry"),
    ("latest_submitted_accounts", "latest_submitted_accounts"),
)

FINANCIAL_FIELDS = (
    "revenue",
    "operating_result",
    "profit_before_tax",
    "annual_result",
    "assets",
    "equity",
    "debt",
)


def _source_class(record: dict[str, Any]) -> str:
    source = str(record.get("source_class") or record.get("source_type") or "unknown")
    lowered = source.casefold()
    if lowered.startswith("official_") or "brreg" in lowered or ("registry" in lowered and "website" not in lowered):
        return "official"
    if "website" in lowered or "company_site" in lowered or "company_owned" in lowered:
        return "company_owned"
    return source


def _evidence_id(org: str, key: str, record: dict[str, Any]) -> str:
    material = "|".join(
        [
            org,
            key,
            str(record.get("source_url") or ""),
            str(record.get("content_sha256") or ""),
            str(record.get("source_row_key") or ""),
        ]
    )
    return "ev-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _availability(record: dict[str, Any] | None) -> str | None:
    if not record:
        return "failed"
    status = str(record.get("status") or "")
    if status == "not_fetched":
        return None
    return STATUS_TO_AVAILABILITY.get(status, "failed")


def _confidence(record: dict[str, Any], availability: str) -> float:
    if availability != "available":
        return 1.0
    value = record.get("value") or {}
    if isinstance(value, dict):
        identity = value.get("identity_assessment") or {}
        if identity.get("score") is not None:
            return max(0.0, min(1.0, float(identity["score"])))
    return 1.0 if _source_class(record) == "official" else 0.95


def _claim_span(record: dict[str, Any], *, fallback: str = "") -> str:
    note = str(record.get("note") or "").strip()
    if fallback:
        return fallback[:1000]
    if note:
        return note[:1000]
    value = record.get("value")
    if value is None:
        return str(record.get("status") or "unknown")[:1000]
    text = str(value)
    return text[:1000]


def _evidence_entry(org: str, key: str, record: dict[str, Any], *, claim_span: str = "") -> dict[str, Any]:
    item = {
        "id": _evidence_id(org, key, record),
        "source_url": record.get("source_url"),
        "source_class": _source_class(record),
        "retrieved_at": record.get("retrieved_at"),
        "content_sha256": record.get("content_sha256"),
        "claim_span": _claim_span(record, fallback=claim_span),
    }
    if record.get("as_of") is not None:
        item["as_of"] = record.get("as_of")
    if record.get("effective_at") is not None:
        item["effective_at"] = record.get("effective_at")
    if record.get("source_row_key") is not None:
        item["source_row_key"] = record.get("source_row_key")
    return item


def _add_claim(
    claims: list[dict[str, Any]],
    evidence_entries: dict[str, dict[str, Any]],
    *,
    org: str,
    evidence_key: str,
    record: dict[str, Any],
    field: str,
    value: Any,
    availability: str | None = None,
    claim_span: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    state = availability or _availability(record)
    if state is None:
        return
    if state not in ALLOWED_AVAILABILITY:
        raise ValueError(f"Unsupported availability state: {state}")
    evidence = _evidence_entry(org, f"{evidence_key}:{field}", record, claim_span=claim_span)
    evidence_entries[evidence["id"]] = evidence
    claim = {
        "field": field,
        "value": value if state == "available" else None,
        "availability": state,
        "confidence": _confidence(record, state),
        "evidence_ids": [evidence["id"]],
    }
    if extra:
        claim.update({key: val for key, val in extra.items() if val is not None})
    claims.append(claim)


def _website_claims(
    profile: dict[str, Any],
    record: dict[str, Any] | None,
    claims: list[dict[str, Any]],
    evidence_entries: dict[str, dict[str, Any]],
) -> None:
    if not record:
        return
    org = str(profile["organisation_number"])
    state = _availability(record)
    value = record.get("value") or {}
    if state == "available":
        identity = value.get("identity_assessment") or {}
        if not identity.get("publishable"):
            state = "ambiguous"
    final_url = value.get("final_url") or record.get("source_url")
    _add_claim(
        claims,
        evidence_entries,
        org=org,
        evidence_key="website",
        record=record,
        field="official_website",
        value=final_url,
        availability=state,
        claim_span=(
            f"Verified company website: {final_url}" if state == "available" else str(record.get("note") or "Website identity not publishable")
        ),
    )
    if state != "available":
        return
    description = str(value.get("description") or "").strip()
    if description:
        _add_claim(
            claims,
            evidence_entries,
            org=org,
            evidence_key="website",
            record=record,
            field="company_description",
            value=description,
            availability="available",
            claim_span=description,
        )
    social_links = value.get("social_links") or []
    if social_links:
        _add_claim(
            claims,
            evidence_entries,
            org=org,
            evidence_key="website",
            record=record,
            field="social_links",
            value=social_links,
            availability="available",
            claim_span=f"Verified social links published on {final_url}",
        )


def _financial_claims(
    profile: dict[str, Any],
    record: dict[str, Any] | None,
    claims: list[dict[str, Any]],
    evidence_entries: dict[str, dict[str, Any]],
) -> None:
    if not record:
        return
    org = str(profile["organisation_number"])
    state = _availability(record)
    if state != "available":
        _add_claim(
            claims,
            evidence_entries,
            org=org,
            evidence_key="financials",
            record=record,
            field="financials",
            value=None,
            availability=state,
        )
        return
    records = (record.get("value") or {}).get("records") or []
    if not records:
        _add_claim(
            claims,
            evidence_entries,
            org=org,
            evidence_key="financials",
            record=record,
            field="financials",
            value=None,
            availability="not_available",
            claim_span="Official annual-accounts endpoint returned no normalized financial records.",
        )
        return
    for item in records:
        period = item.get("period")
        currency = item.get("currency")
        for key in FINANCIAL_FIELDS:
            amount = item.get(key)
            if amount is None:
                continue
            _add_claim(
                claims,
                evidence_entries,
                org=org,
                evidence_key=f"financials:{period}",
                record=record,
                field=f"financial.{key}",
                value=amount,
                availability="available",
                claim_span=f"period={period}; currency={currency}; {key}={amount}",
                extra={"reporting_period": period, "currency": currency},
            )


def _structured_module_claim(
    profile: dict[str, Any],
    key: str,
    field: str,
    claims: list[dict[str, Any]],
    evidence_entries: dict[str, dict[str, Any]],
) -> None:
    record = (profile.get("evidence") or {}).get(key)
    if not record:
        return
    state = _availability(record)
    if state is None:
        return
    value = record.get("value") if state == "available" else None
    _add_claim(
        claims,
        evidence_entries,
        org=str(profile["organisation_number"]),
        evidence_key=key,
        record=record,
        field=field,
        value=value,
        availability=state,
    )


def _runtime_ms(started_at: str | None, completed_at: str | None) -> int | None:
    try:
        start = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(completed_at).replace("Z", "+00:00"))
        return max(0, int((end - start).total_seconds() * 1000))
    except (TypeError, ValueError):
        return None


def _profile_runtime_ms(profile: dict[str, Any], envelope: dict[str, Any]) -> int | None:
    metrics = profile.get("run_metrics") or {}
    latencies = metrics.get("latencies_ms") or []
    cleaned = []
    for value in latencies:
        try:
            cleaned.append(max(0, int(value)))
        except (TypeError, ValueError):
            continue
    if cleaned:
        return sum(cleaned)
    return _runtime_ms(envelope.get("started_at"), envelope.get("completed_at"))


def project_terminal_envelope(
    envelope: dict[str, Any],
    *,
    third_party_cost_usd: float = 0.0,
    changes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    profile = envelope.get("profile") or {}
    org = str(envelope.get("organisation_number") or profile.get("organisation_number") or "")
    if len(org) != 9 or not org.isdigit():
        raise ValueError("Output contract requires a valid 9-digit organisation number")

    claims: list[dict[str, Any]] = []
    evidence_entries: dict[str, dict[str, Any]] = {}
    registry = (profile.get("evidence") or {}).get("registry")
    if registry:
        for field, profile_key in CORE_PROFILE_FIELDS:
            if profile_key not in profile or profile.get(profile_key) is None:
                continue
            _add_claim(
                claims,
                evidence_entries,
                org=org,
                evidence_key="registry",
                record=registry,
                field=field,
                value=profile.get(profile_key),
                availability="available",
                claim_span=f"{field}={profile.get(profile_key)}",
            )

    _website_claims(profile, (profile.get("evidence") or {}).get("website"), claims, evidence_entries)
    _financial_claims(profile, (profile.get("evidence") or {}).get("financials"), claims, evidence_entries)
    for key, field in (
        ("accounting_obligation", "accounting_obligation"),
        ("roles", "roles"),
        ("group", "group_structure"),
        ("locations", "locations"),
    ):
        _structured_module_claim(profile, key, field, claims, evidence_entries)

    errors = []
    for key, record in sorted((profile.get("evidence") or {}).items()):
        status = str((record or {}).get("status") or "")
        if status in {"source_error", "blocked", "not_fetched"}:
            errors.append(
                {
                    "module": key,
                    "status": status,
                    "message": (record or {}).get("note"),
                    "source_url": (record or {}).get("source_url"),
                }
            )

    metrics = profile.get("run_metrics") or {}
    terminal_status = "completed" if envelope.get("state") == "complete" else "failed"
    operations = {
        "requests": int(metrics.get("requests") or 0),
        "runtime_ms": _profile_runtime_ms(profile, envelope),
        "third_party_cost_usd": float(third_party_cost_usd),
    }
    return {
        "organisation_number": org,
        "run": {
            "run_id": envelope.get("run_id"),
            "started_at": envelope.get("started_at"),
            "completed_at": envelope.get("completed_at"),
            "terminal_status": terminal_status,
        },
        "claims": claims,
        "evidence": sorted(evidence_entries.values(), key=lambda item: item["id"]),
        "changes": list(changes or []),
        "errors": errors,
        "operations": operations,
    }


def validate_contract_object(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    org = str(item.get("organisation_number") or "")
    if len(org) != 9 or not org.isdigit():
        errors.append("invalid organisation number")
    run = item.get("run") or {}
    for field in ("run_id", "started_at", "completed_at", "terminal_status"):
        if not run.get(field):
            errors.append(f"missing run.{field}")
    evidence = {entry.get("id"): entry for entry in item.get("evidence") or [] if entry.get("id")}
    if len(evidence) != len(item.get("evidence") or []):
        errors.append("duplicate or missing evidence ids")
    for entry in evidence.values():
        if not entry.get("source_url"):
            errors.append(f"evidence {entry.get('id')} missing source_url")
        if not entry.get("retrieved_at"):
            errors.append(f"evidence {entry.get('id')} missing retrieved_at")
        if entry.get("claim_span") in {None, ""}:
            errors.append(f"evidence {entry.get('id')} missing claim_span")
    for claim in item.get("claims") or []:
        availability = claim.get("availability")
        if availability not in ALLOWED_AVAILABILITY:
            errors.append(f"claim {claim.get('field')} has invalid availability")
        if availability != "available" and claim.get("value") is not None:
            errors.append(f"claim {claim.get('field')} has value while unavailable")
        if availability == "available" and not claim.get("evidence_ids"):
            errors.append(f"claim {claim.get('field')} lacks evidence ids")
        for evidence_id in claim.get("evidence_ids") or []:
            if evidence_id not in evidence:
                errors.append(f"claim {claim.get('field')} references missing evidence {evidence_id}")
    operations = item.get("operations") or {}
    if int(operations.get("requests") or 0) < 0:
        errors.append("operations.requests is negative")
    if float(operations.get("third_party_cost_usd") or 0) < 0:
        errors.append("operations.third_party_cost_usd is negative")
    return errors
