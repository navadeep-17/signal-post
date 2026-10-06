from __future__ import annotations

from typing import Any

from .domain_discovery import _domain_identity_strength, registry_email_domain_candidates


STRONG_DOMAIN_STRENGTHS = {"exact", "multi", "acronym"}
DOMAIN_STRENGTH_RANK = {"exact": 3, "acronym": 2, "multi": 1}


def ranked_strong_registry_email_domain_candidates(
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return strong BRREG email-domain nominations in deterministic priority order.

    This is candidate selection only. A returned domain is never ownership proof and
    must still pass the unchanged independent website fetch + exact-company verifier.
    """
    plan = registry_email_domain_candidates(profile)
    if not plan.get("eligible"):
        return []

    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for candidate in plan.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        domain = str(candidate.get("domain") or "").strip().casefold()
        if not domain:
            continue
        strength = _domain_identity_strength(profile, domain)
        if strength not in STRONG_DOMAIN_STRENGTHS:
            continue
        ranked.append(
            (
                DOMAIN_STRENGTH_RANK[strength],
                domain,
                {**candidate, "strength": strength},
            )
        )

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [candidate for _, _, candidate in ranked]


def select_strong_registry_email_domain_candidate(
    profile: dict[str, Any],
) -> dict[str, Any] | None:
    """Select at most one strong email-domain nomination for the V9 M2 slot."""
    candidates = ranked_strong_registry_email_domain_candidates(profile)
    return candidates[0] if candidates else None
