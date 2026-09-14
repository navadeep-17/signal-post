from __future__ import annotations

import hashlib
from typing import Any, Iterable


def _change_id(event: dict[str, Any]) -> str:
    material = "|".join(
        [
            str(event.get("organisation_number") or ""),
            str(event.get("field") or ""),
            str(event.get("old_content_sha256") or ""),
            str(event.get("new_content_sha256") or ""),
            str(event.get("retrieved_at") or ""),
        ]
    )
    return "chg-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def normalize_refresh_event(event: dict[str, Any], *, expected_org: str | None = None) -> dict[str, Any]:
    org = "".join(character for character in str(event.get("organisation_number") or "") if character.isdigit())
    if len(org) != 9:
        raise ValueError("Refresh change requires a valid 9-digit organisation number")
    if expected_org is not None and org != expected_org:
        raise ValueError(f"Refresh change belongs to {org}, expected {expected_org}")

    field = str(event.get("field") or "").strip()
    if not field:
        raise ValueError("Refresh change requires a field")
    if event.get("old_value") == event.get("new_value"):
        raise ValueError(f"Refresh change {org}:{field} does not change the value")

    normalized = {
        "id": _change_id(event),
        "organisation_number": org,
        "field": field,
        "previous_value": event.get("old_value"),
        "current_value": event.get("new_value"),
        "source_url": event.get("source_url"),
        "source_class": event.get("source_class"),
        "retrieved_at": event.get("retrieved_at"),
        "effective_at": event.get("effective_at"),
        "previous_content_sha256": event.get("old_content_sha256"),
        "current_content_sha256": event.get("new_content_sha256"),
        "current_status": event.get("status"),
    }
    return normalized


def validate_refresh_change(change: dict[str, Any], *, expected_org: str | None = None) -> list[str]:
    errors: list[str] = []
    org = str(change.get("organisation_number") or "")
    if len(org) != 9 or not org.isdigit():
        errors.append("invalid organisation number")
    if expected_org is not None and org != expected_org:
        errors.append(f"change organisation {org} does not match contract object {expected_org}")
    if not change.get("id"):
        errors.append("missing change id")
    if not change.get("field"):
        errors.append("missing field")
    if change.get("previous_value") == change.get("current_value"):
        errors.append("previous_value equals current_value")
    if not change.get("source_url"):
        errors.append("missing source_url")
    if not change.get("retrieved_at"):
        errors.append("missing retrieved_at")
    if not change.get("source_class"):
        errors.append("missing source_class")
    if not change.get("current_status"):
        errors.append("missing current_status")
    for key in ("previous_content_sha256", "current_content_sha256"):
        value = str(change.get(key) or "")
        if len(value) != 64 or any(character not in "0123456789abcdefABCDEF" for character in value):
            errors.append(f"invalid {key}")
    return errors


def group_refresh_events(
    events: Iterable[dict[str, Any]],
    *,
    expected_organisation_numbers: set[str],
) -> dict[str, list[dict[str, Any]]]:
    grouped = {org: [] for org in expected_organisation_numbers}
    seen_fields: set[tuple[str, str]] = set()
    seen_ids: set[str] = set()
    for raw in events:
        normalized = normalize_refresh_event(raw)
        org = normalized["organisation_number"]
        if org not in expected_organisation_numbers:
            raise ValueError(f"Refresh report contains organisation outside output batch: {org}")
        key = (org, normalized["field"])
        if key in seen_fields:
            raise ValueError(f"Duplicate refresh field event: {org}:{normalized['field']}")
        if normalized["id"] in seen_ids:
            raise ValueError(f"Duplicate refresh change id: {normalized['id']}")
        errors = validate_refresh_change(normalized, expected_org=org)
        if errors:
            raise ValueError(f"Invalid refresh event {org}:{normalized['field']}: {', '.join(errors)}")
        seen_fields.add(key)
        seen_ids.add(normalized["id"])
        grouped[org].append(normalized)
    for org in grouped:
        grouped[org].sort(key=lambda item: (item["field"], item["id"]))
    return grouped
