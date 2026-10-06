from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from .domain_discovery import _domain_identity_strength, registry_email_domain_candidates
from .v9_email_domain import select_registry_email_domain_candidate


def classify_m2_candidate_slot(profile: dict[str, Any]) -> dict[str, Any]:
    """Classify whether V9 M2 changes the existing V8 email-domain request slot."""
    plan = registry_email_domain_candidates(profile)
    candidates = plan.get("candidates") or []
    baseline = candidates[0] if plan.get("eligible") and candidates else None
    challenger = select_registry_email_domain_candidate(profile, plan=plan)

    baseline_domain = str((baseline or {}).get("domain") or "").casefold() or None
    challenger_domain = str((challenger or {}).get("domain") or "").casefold() or None
    baseline_strength = (
        _domain_identity_strength(profile, baseline_domain)
        if baseline_domain
        else None
    )
    challenger_strength = (
        str((challenger or {}).get("strength") or "") or None
    )

    if baseline_domain != challenger_domain:
        bucket = "m2_delta"
    elif baseline_domain:
        bucket = "preserved_email_control"
    else:
        bucket = "no_email_control"

    return {
        "organisation_number": str(profile.get("organisation_number") or ""),
        "bucket": bucket,
        "baseline_candidate_domain": baseline_domain,
        "baseline_candidate_strength": baseline_strength,
        "challenger_candidate_domain": challenger_domain,
        "challenger_candidate_strength": challenger_strength,
        "registry_website_present": bool(str(profile.get("website") or "").strip()),
        "plan_reason": plan.get("reason"),
    }


def build_targeted_m2_cohort(
    profiles: Iterable[dict[str, Any]],
    *,
    target_count: int = 100,
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    """Build a consumed M2 cohort with maximum causal exposure and deterministic controls.

    Priority:
    1. every company whose V8 and V9 email-domain slot differs;
    2. preserved-email controls where V8 and V9 nominate the same domain;
    3. no-email controls, only to reach the requested cohort size.

    Companies with a registry website are excluded because M2 never owns their first site slot.
    """
    if target_count < 1:
        raise ValueError("target_count must be positive")

    classifications: list[dict[str, Any]] = []
    for profile in profiles:
        if str(profile.get("website") or "").strip():
            continue
        item = classify_m2_candidate_slot(profile)
        org = item["organisation_number"]
        if len(org) != 9 or not org.isdigit():
            continue
        classifications.append(item)

    by_bucket: dict[str, list[dict[str, Any]]] = {
        "m2_delta": [],
        "preserved_email_control": [],
        "no_email_control": [],
    }
    for item in classifications:
        by_bucket[item["bucket"]].append(item)
    for values in by_bucket.values():
        values.sort(key=lambda row: row["organisation_number"])

    delta = by_bucket["m2_delta"]
    if len(delta) > target_count:
        raise ValueError(
            f"M2 delta population {len(delta)} exceeds target_count={target_count}; "
            "do not silently drop behaviorally affected consumed companies"
        )

    selected = list(delta)
    remaining = target_count - len(selected)
    selected.extend(by_bucket["preserved_email_control"][:remaining])
    remaining = target_count - len(selected)
    selected.extend(by_bucket["no_email_control"][:remaining])

    if len(selected) != target_count:
        raise ValueError(
            f"insufficient eligible consumed profiles for target_count={target_count}: "
            f"selected={len(selected)}"
        )

    selected_orgs = [row["organisation_number"] for row in selected]
    selected_bucket_counts = Counter(row["bucket"] for row in selected)
    all_bucket_counts = Counter(row["bucket"] for row in classifications)
    strength_counts = Counter(
        str(row.get("baseline_candidate_strength") or "none")
        for row in classifications
        if row.get("baseline_candidate_domain")
    )
    report = {
        "target_count": target_count,
        "selected_companies": len(selected_orgs),
        "selected_bucket_counts": dict(sorted(selected_bucket_counts.items())),
        "eligible_population_bucket_counts": dict(sorted(all_bucket_counts.items())),
        "baseline_candidate_strength_counts": dict(sorted(strength_counts.items())),
        "m2_behaviorally_affected_companies": len(delta),
        "m2_behavioral_exposure_in_target": sum(
            1 for row in selected if row["bucket"] == "m2_delta"
        ),
        "fresh_companies_used": 0,
        "selection_rule": [
            "include all consumed companies whose V8 and V9 email-domain slot differs",
            "then same-domain preserved-email controls (exact/acronym/multi/partial)",
            "then deterministic no-email controls by organisation number",
        ],
    }
    return selected_orgs, selected, report
