from __future__ import annotations

from typing import Any

from build_v2_product import _evidence_map, _fact_view, compact_company, ensure_canonical


def _decision_trace_view(trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": trace.get("evidence_id"),
        "url": trace.get("source_url"),
        "sourceClass": trace.get("source_class"),
        "retrievedAt": trace.get("retrieved_at"),
        "effectiveAt": trace.get("effective_at"),
        "publishedDate": trace.get("published_date"),
        "reportingPeriod": trace.get("reporting_period"),
        "span": trace.get("claim_span"),
        "hash": trace.get("content_sha256"),
    }


def _decision_brief_view(synthesis: dict[str, Any]) -> dict[str, Any]:
    brief = synthesis.get("decision_brief") or {}
    output: dict[str, Any] = {}
    for key, value in brief.items():
        if key == "what_is_unknown":
            output[key] = list(value or [])
            continue
        if not isinstance(value, dict):
            continue
        output[key] = {
            "key": value.get("key") or key,
            "text": value.get("text"),
            "evidence": [
                _decision_trace_view(trace)
                for trace in (value.get("evidence") or [])
                if isinstance(trace, dict)
            ],
        }
    return output


def compact_company_v6(row: dict[str, Any]) -> dict[str, Any]:
    """Adapt the current canonical contract into the legacy V6 workspace payload.

    The adapter does not create facts or alter canonical/synthesis semantics. It only exposes
    canonical fields added after the original V6 branch was cut and retains the richer
    decision-brief evidence trace for later UI rendering.
    """

    item = ensure_canonical(row)
    compact = compact_company(item)
    profile = item.get("canonical_profile") or {}
    evidence = _evidence_map(item)

    hiring_signals = [
        _fact_view(fact, evidence)
        for fact in (profile.get("hiring_signals") or [])
        if isinstance(fact, dict)
    ]
    existing_public_activity = list((compact.get("areas") or {}).get("hiring_and_public_activity") or [])
    compact.setdefault("areas", {})["hiring_and_public_activity"] = [
        *hiring_signals,
        *existing_public_activity,
    ]

    synthesis = item.get("synthesis") or {}
    compact.setdefault("synthesis", {})["decisionBrief"] = _decision_brief_view(synthesis)
    return compact
