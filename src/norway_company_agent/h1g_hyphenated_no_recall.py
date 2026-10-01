from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from .domain_discovery import (
    _page_contains_full_legal_name,
    _page_contains_org_number,
    _page_matches_registry_location,
    distinctive_legal_name_tokens,
)
from .evidence import evidence
from .final_site_discovery import (
    BRREG_BULK_URL,
    MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
    _has_conflicting_explicit_org_number,
    _publishable,
    fetch_bounded_homepage,
)
from .identity import apply_website_identity_gate
from .zero_cost_registry_guard import apply_registry_risk_guard

OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE = 5
V6_SOURCE_TYPE = "deterministic_legal_name_ranked_fallback"


def _safe_domain(label: str, suffix: str) -> str | None:
    label = label.strip("-")
    if not (3 <= len(label) <= 63):
        return None
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label):
        return None
    return f"{label}.{suffix}"


def hyphenated_no_candidate(profile: dict[str, Any]) -> dict[str, str] | None:
    """Return the historical H1g candidate for regression/audit compatibility."""
    tokens = distinctive_legal_name_tokens(profile.get("name"))
    if len(tokens) < 2:
        return None
    domain = _safe_domain("-".join(tokens), "no")
    if not domain:
        return None
    return {"domain": domain, "url": f"https://{domain}/", "strategy": "legal_name_hyphenated_no"}


def _attempted_domains(profile: dict[str, Any]) -> set[str]:
    """Domains already nominated earlier in the same production discovery path."""
    evidence_map = profile.get("evidence") or {}
    domains: set[str] = set()
    for key in (
        "website_email_discovery",
        "website_discovery_zero_cost",
        "website_h1g_hyphenated_no_discovery",
        "website_v6_ranked_domain_discovery",
    ):
        row = evidence_map.get(key) or {}
        value = row.get("value") or {}
        domain = str(value.get("candidate_domain") or "").strip().casefold().rstrip(".")
        if domain:
            domains.add(domain)
    return domains


def ranked_fallback_candidate(profile: dict[str, Any]) -> dict[str, str] | None:
    """Rank a request-free legal-name fallback without increasing the V5 site budget.

    The V5 fresh-100 spent this final slot on a hyphenated `.no` candidate 64 times and
    verified zero sites; 63 of those hosts did not resolve. V6 uses the same slot for a
    compact `.com` first, then a hyphenated `.com` only if the compact form was already
    attempted through a stronger official-domain path. The historical hyphenated `.no`
    remains last for compatibility. Candidate nomination is never identity evidence.
    """
    website = (profile.get("evidence") or {}).get("website") or {}
    if _publishable(website):
        return None

    tokens = distinctive_legal_name_tokens(profile.get("name"))
    if not tokens:
        return None

    attempted = _attempted_domains(profile)
    candidates: list[dict[str, str]] = []

    compact_com = _safe_domain("".join(tokens), "com")
    if compact_com:
        candidates.append({
            "domain": compact_com,
            "url": f"https://{compact_com}/",
            "strategy": "legal_name_compact_com",
        })

    if len(tokens) >= 2:
        hyphen_com = _safe_domain("-".join(tokens), "com")
        if hyphen_com:
            candidates.append({
                "domain": hyphen_com,
                "url": f"https://{hyphen_com}/",
                "strategy": "legal_name_hyphenated_com",
            })
        old = hyphenated_no_candidate(profile)
        if old:
            candidates.append(old)

    for candidate in candidates:
        if candidate["domain"] not in attempted:
            return candidate
    return None


def _quarantine(assessment: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **assessment,
        "status": "review",
        "score": min(float(assessment.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [*list(assessment.get("reasons") or []), reason],
        "method": "v6_ranked_fallback_exact_entity_guard_v1",
    }


def qualify_hyphenated_no_identity(
    profile: dict[str, Any],
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Historical function name; now guards any V6 final-slot guessed domain.

    Publication is deliberately stricter than nomination. A guessed `.com`/`.no` can
    publish only when the independently fetched page has the exact target organisation
    number, or the complete legal name plus independent BRREG location corroboration.
    Title/hostname/name similarity alone never publishes this fallback.
    """
    if not assessment or not assessment.get("publishable") or website.get("status") != "available":
        return assessment

    if _has_conflicting_explicit_org_number(profile, website):
        return _quarantine(
            assessment,
            "V6 guessed-domain page explicitly identifies a different organisation number",
        )

    if _page_contains_org_number(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "V6 guessed-domain page contains the exact target organisation number",
            ],
            "method": "v6_ranked_fallback_exact_entity_guard_v1",
        }

    if _page_contains_full_legal_name(profile, website) and _page_matches_registry_location(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": max(float(assessment.get("score") or 0.95), 0.98),
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "V6 guessed-domain page has complete legal name plus independent BRREG location corroboration",
            ],
            "method": "v6_ranked_fallback_exact_entity_guard_v1",
        }

    return _quarantine(
        assessment,
        "V6 guessed-domain candidate lacks exact organisation-number or legal-name-plus-BRREG-location proof",
    )


def _base_site_logical_requests(profile: dict[str, Any]) -> int | None:
    metrics = profile.get("run_metrics") or {}
    try:
        logical = int(metrics.get("logical_requests"))
    except (TypeError, ValueError):
        return None
    site = logical - OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE
    return site if 0 <= site <= MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE else None


def evaluate_hyphenated_no_fallback(
    profile: dict[str, Any],
    *,
    timeout: float = 6.0,
    base_site_logical_requests: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Use V6 ranked fallback inside the exact request headroom formerly used by H1g.

    The public function name is retained so the production orchestrator and existing
    contract tests do not fork into a parallel implementation. The structural ceiling is
    unchanged: this stage can run only when two of the four site logical slots remain.
    """
    row = deepcopy(profile)
    website = (row.get("evidence") or {}).get("website") or {}
    candidate = ranked_fallback_candidate(row)
    if base_site_logical_requests is None:
        base_site_requests = _base_site_logical_requests(row)
    else:
        try:
            requested = int(base_site_logical_requests)
        except (TypeError, ValueError):
            requested = -1
        base_site_requests = requested if 0 <= requested <= MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE else None

    result: dict[str, Any] = {
        "organisation_number": str(row.get("organisation_number") or ""),
        "candidate_available": bool(candidate),
        "candidate_domain": candidate.get("domain") if candidate else None,
        "candidate_strategy": candidate.get("strategy") if candidate else None,
        "attempted": False,
        "verified": False,
        "base_site_logical_requests": base_site_requests,
        "requests_added": 0,
        "post_site_logical_requests": base_site_requests,
        "bytes_added": 0,
        "latencies_ms": [],
        "skipped_reason": None,
        "guard_reasons": [],
    }

    if _publishable(website):
        result["skipped_reason"] = "verified_website_present"
        return row, result
    if base_site_requests is None:
        result["skipped_reason"] = "base_site_request_accounting_unavailable"
        return row, result
    if not candidate:
        result["skipped_reason"] = "no_untried_ranked_candidate"
        return row, result
    if base_site_requests + 2 > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        result["skipped_reason"] = "site_request_budget_consumed"
        return row, result

    result["attempted"] = True
    record, operations = fetch_bounded_homepage(
        candidate["url"],
        source_type=V6_SOURCE_TYPE,
        timeout=timeout,
    )
    added_requests = int(operations.get("requests") or 0)
    post_site_requests = base_site_requests + added_requests
    if post_site_requests > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        raise RuntimeError(
            f"V6 ranked fallback exceeded site request ceiling for {row.get('organisation_number')}: "
            f"{post_site_requests}>{MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE}"
        )
    result["requests_added"] = added_requests
    result["post_site_logical_requests"] = post_site_requests
    result["bytes_added"] = int(operations.get("bytes") or 0)
    result["latencies_ms"] = [int(value) for value in operations.get("latencies_ms") or []]

    record["source_class"] = "company_owned_candidate"
    gated = apply_website_identity_gate(row, record)
    candidate_record = gated["website"]
    assessment = qualify_hyphenated_no_identity(row, candidate_record, gated.get("assessment"))
    if assessment is not None:
        value = candidate_record.get("value") or {}
        value["identity_assessment"] = assessment
        candidate_record["value"] = value

    selected = bool(
        assessment
        and assessment.get("publishable")
        and candidate_record.get("status") == "available"
    )
    evidence_map = row.setdefault("evidence", {})
    evidence_map["website_v6_ranked_domain_discovery"] = evidence(
        "website_v6_ranked_domain_discovery",
        "available" if selected else "not_found",
        V6_SOURCE_TYPE,
        BRREG_BULK_URL,
        value={
            "candidate_strategy": candidate["strategy"],
            "candidate_domain": candidate["domain"],
            "independent_page_url": (candidate_record.get("value") or {}).get("final_url") if selected else None,
            "publishable_before_registry_guard": selected,
            "base_site_logical_requests": base_site_requests,
            "requests_added": added_requests,
            "post_site_logical_requests": post_site_requests,
            "third_party_cost_usd": 0.0,
        },
        source_row_key=row.get("organisation_number"),
        note=(
            "V6 ranked legal-name candidate is a request-free discovery hint only. "
            "Publication requires exact org-number or legal-name-plus-location proof."
        ),
    )
    evidence_map["website_v6_ranked_domain_candidate"] = candidate_record

    if selected:
        trial = deepcopy(row)
        trial.setdefault("evidence", {})["website"] = candidate_record
        trial["website"] = (
            (candidate_record.get("value") or {}).get("final_url")
            or candidate_record.get("source_url")
            or ""
        )
        trial, guard_reasons = apply_registry_risk_guard(trial)
        result["guard_reasons"] = list(guard_reasons or [])
        guarded_website = (trial.get("evidence") or {}).get("website") or {}
        if _publishable(guarded_website):
            row["evidence"]["website"] = guarded_website
            row["website"] = trial.get("website") or ""
            result["verified"] = True
            result["selected_url"] = row["website"]
        else:
            result["selected_url"] = None
    else:
        result["selected_url"] = None

    return row, result
