from __future__ import annotations

from typing import Any

from .domain_discovery import _domain_identity_strength, registry_email_domain_candidates


# M2 RETUNE policy:
# - preserve V8 candidates whose registry-email domain has any legal-name relationship;
# - substitute only clearly unrelated ("none") domains;
# - publication still requires the unchanged independent exact-company verifier.
#
# The targeted consumed gate showed that excluding "partial" domains removed real exact
# sites (for example legal-name abbreviations / concatenations such as kokkers.no for
# KOKKERSVOLD AS and opusas.no for OPUS AS). Candidate morphology is therefore only a
# request-allocation heuristic, never publication evidence.
PRESERVED_DOMAIN_STRENGTHS = {"exact", "acronym", "multi", "partial"}
DOMAIN_STRENGTH_RANK = {"exact": 4, "acronym": 3, "multi": 2, "partial": 1}


def ranked_registry_email_domain_candidates(
    profile: dict[str, Any],
    *,
    plan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return admissible BRREG email-domain nominations in deterministic priority order.

    A candidate is only a nomination. The independent site fetch, exact-company identity
    gate, conflicting-organisation veto and registry-risk guard remain authoritative.
    M2 filters only domains with no legal-name relationship at all.
    """
    candidate_plan = plan if plan is not None else registry_email_domain_candidates(profile)
    if not candidate_plan.get("eligible"):
        return []

    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for candidate in candidate_plan.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        domain = str(candidate.get("domain") or "").strip().casefold()
        if not domain:
            continue
        strength = _domain_identity_strength(profile, domain)
        if strength not in PRESERVED_DOMAIN_STRENGTHS:
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


def select_registry_email_domain_candidate(
    profile: dict[str, Any],
    *,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Select at most one admissible registry-email nomination for the M2 request slot."""
    candidates = ranked_registry_email_domain_candidates(profile, plan=plan)
    return candidates[0] if candidates else None


# Backward-compatible names retained while the V9 experiment is open. These wrappers
# deliberately follow the retuned policy above; "strong" in the legacy symbol name must
# not be interpreted as publication proof.
def ranked_strong_registry_email_domain_candidates(
    profile: dict[str, Any],
    *,
    plan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return ranked_registry_email_domain_candidates(profile, plan=plan)


def select_strong_registry_email_domain_candidate(
    profile: dict[str, Any],
    *,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    return select_registry_email_domain_candidate(profile, plan=plan)
