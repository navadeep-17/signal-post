from __future__ import annotations

import hashlib
from typing import Any

from .external_footprint import publishable_observation


def _employee_count(profile: dict[str, Any]) -> int | None:
    live = ((profile.get("evidence") or {}).get("registry_live") or {})
    if live.get("status") != "available":
        return None
    value = live.get("value") or {}
    org = str(profile.get("organisation_number") or "")
    if str(value.get("organisation_number") or "") != org:
        return None
    raw = value.get("employees")
    if isinstance(raw, bool):
        return None
    try:
        count = int(raw)
    except (TypeError, ValueError):
        return None
    if count < 0 or count > 1_000_000:
        return None
    return count


def registry_workforce_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Project an already-fetched exact BRREG employee count into a workforce signal.

    This performs no network access. The narrow claim is only the employee count reported by
    the exact organisation's official registry response at retrieval time; it is not an FTE,
    current payroll, headcount trend, or group-wide workforce claim.
    """

    org = str(profile.get("organisation_number") or "")
    if len(org) != 9 or not org.isdigit():
        return []
    count = _employee_count(profile)
    if count is None:
        return []

    live = ((profile.get("evidence") or {}).get("registry_live") or {})
    source_url = str(live.get("source_url") or "").strip()
    retrieved_at = str(live.get("retrieved_at") or "").strip()
    content_sha256 = str(live.get("content_sha256") or "").strip()
    if not source_url.startswith(("http://", "https://")) or not retrieved_at or len(content_sha256) != 64:
        return []

    observation = {
        "id": "brreg-workforce-" + hashlib.sha256(
            f"{org}|{count}|{source_url}|{content_sha256}".encode("utf-8")
        ).hexdigest()[:24],
        "organisation_number": org,
        "platform": "brreg",
        "signal_type": "workforce_snapshot",
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "content_sha256": content_sha256,
        "exact_entity": True,
        "identity_proof": [
            {
                "type": "official_registry_exact_organisation_number",
                "organisation_number": org,
            },
            {
                "type": "official_registry_employee_count",
                "employees": count,
            },
        ],
        "acquisition_mode": "official_api",
        "rights_status": "approved",
        "source_class": "official_registry_live",
        "evidence_span": f"Official BRREG entity response reports employees={count} for organisation {org}.",
        "effective_at": retrieved_at,
        "metrics": {
            "workforce_value": count,
            "employees": count,
            "measure": "employees",
            "scope": "registry_entity",
            "claim_scope": (
                "Employee count reported by the exact BRREG legal-entity record at retrieval time; "
                "not FTE, group workforce, or a trend claim."
            ),
        },
        "strategy": "official_registry_employee_count_v1",
    }
    return [observation] if publishable_observation(observation) else []


def attach_registry_workforce_observations(profile: dict[str, Any]) -> dict[str, Any]:
    existing = [item for item in (profile.get("external_observations") or []) if isinstance(item, dict)]
    generated = registry_workforce_observations(profile)
    by_id = {
        str(item.get("id")): item
        for item in [*existing, *generated]
        if str(item.get("id") or "").strip()
    }
    profile["external_observations"] = sorted(
        by_id.values(),
        key=lambda row: (
            str(row.get("signal_type") or ""),
            str(row.get("platform") or ""),
            str(row.get("id") or ""),
        ),
    )
    return profile
