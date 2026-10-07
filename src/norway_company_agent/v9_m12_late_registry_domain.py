from __future__ import annotations

from copy import deepcopy
from typing import Any

from .domain_discovery import (
    _domain_identity_strength,
    _page_contains_full_legal_name,
    _page_contains_org_number,
    _page_matches_registry_location,
    distinctive_legal_name_compact,
    registry_email_domain_candidates,
)
from .evidence import evidence
from .final_site_discovery import (
    BRREG_BULK_URL,
    MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
    _has_conflicting_explicit_org_number,
    _publishable,
    fetch_bounded_homepage,
)
from .h1g_hyphenated_no_recall import evaluate_hyphenated_no_fallback, hyphenated_no_candidate
from .identity import apply_website_identity_gate
from .zero_cost_registry_guard import apply_registry_risk_guard


_CONSUMER_PROVIDER_LABELS = {
    "aol", "fastmail", "gmail", "googlemail", "hey", "hotmail", "icloud",
    "live", "mail", "me", "msn", "online", "outlook", "proton",
    "protonmail", "yahoo",
}


def _consumer_mail_domain(domain: str) -> bool:
    labels = [part for part in str(domain or "").strip(". ").casefold().split(".") if part]
    if len(labels) < 2:
        return True
    # Provider families such as hotmail.es are consumer mail even if the exact TLD
    # is not in the legacy static list.
    return labels[-2] in _CONSUMER_PROVIDER_LABELS


def _collapsed_exact_alias(profile: dict[str, Any], domain: str) -> str | None:
    """Collapse a malformed multi-label email host only when it equals the legal name.

    Example from the consumed development set:
        EMILSEN FISK AS + post@emilsen.fisk.com -> emilsenfisk.com

    This is nomination only. Publication still requires independent page identity.
    """
    labels = [part for part in str(domain or "").strip(". ").casefold().split(".") if part]
    if len(labels) < 3 or any(not part for part in labels):
        return None
    compact = distinctive_legal_name_compact(profile.get("name"))
    candidate_label = "".join(labels[:-1])
    if not compact or candidate_label != compact:
        return None
    return f"{candidate_label}.{labels[-1]}"


def select_late_registry_domain_candidate(profile: dict[str, Any]) -> dict[str, Any] | None:
    """Nominate one request-neutral late BRREG email-domain candidate.

    Existing V9 deliberately rejects email domains with no legal-name relationship in
    the *early* site slot. M12 does not weaken that policy. Instead, after the normal
    deterministic/Wikidata path is unresolved, it may replace H1g's final two-request
    slot with one official-registry email-domain candidate.

    Candidate morphology is never ownership proof.
    """
    # Strict observed-request neutrality: M12 can only substitute a final probe that
    # the frozen baseline H1g path would itself have a deterministic candidate for.
    # Single-token/no-H1g profiles therefore remain untouched.
    if hyphenated_no_candidate(profile) is None:
        return None

    plan = registry_email_domain_candidates(profile)
    if not plan.get("eligible"):
        return None

    for item in plan.get("candidates") or []:
        if not isinstance(item, dict):
            continue
        domain = str(item.get("domain") or "").strip().casefold()
        if not domain or _consumer_mail_domain(domain):
            continue
        if _domain_identity_strength(profile, domain) != "none":
            # Strong/partial candidates are already handled by the existing M2 path.
            continue

        collapsed = _collapsed_exact_alias(profile, domain)
        if collapsed:
            return {
                "domain": collapsed,
                "url": f"https://{collapsed}/",
                "registry_email_domain": domain,
                "strategy": "collapsed_exact_registry_email_domain",
            }
        return {
            "domain": domain,
            "url": f"https://{domain}/",
            "registry_email_domain": domain,
            "strategy": "late_unrelated_registry_email_domain",
        }
    return None


def _quarantine(assessment: dict[str, Any] | None, reason: str) -> dict[str, Any]:
    base = dict(assessment or {})
    return {
        **base,
        "status": "review",
        "score": min(float(base.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [*list(base.get("reasons") or []), reason],
        "method": "v9_m12_late_registry_domain_identity_v1",
    }


def qualify_late_registry_domain_identity(
    profile: dict[str, Any],
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> dict[str, Any]:
    """Fail closed: the BRREG email domain nominates but never proves identity."""

    if website.get("status") != "available":
        return _quarantine(assessment, "late registry-domain candidate page is unavailable")
    if _has_conflicting_explicit_org_number(profile, website):
        return _quarantine(
            assessment,
            "late registry-domain candidate explicitly identifies a different organisation number",
        )

    if _page_contains_org_number(profile, website):
        return {
            **dict(assessment or {}),
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "reasons": [
                *list((assessment or {}).get("reasons") or []),
                "independently fetched late registry-domain page contains exact target organisation number",
            ],
            "method": "v9_m12_late_registry_domain_identity_v1",
        }

    if (
        _page_contains_full_legal_name(profile, website)
        and _page_matches_registry_location(profile, website)
    ):
        return {
            **dict(assessment or {}),
            "status": "exact",
            "score": max(float((assessment or {}).get("score") or 0.95), 0.98),
            "publishable": True,
            "reasons": [
                *list((assessment or {}).get("reasons") or []),
                "independently fetched late registry-domain page has full legal name plus BRREG location",
            ],
            "method": "v9_m12_late_registry_domain_identity_v1",
        }

    return _quarantine(
        assessment,
        "registry email domain is nomination only; page lacks exact org-number or legal-name-plus-location proof",
    )


def evaluate_request_neutral_late_fallback(
    profile: dict[str, Any],
    *,
    timeout: float = 6.0,
    base_site_logical_requests: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replace H1g only for unresolved M12-eligible profiles; never add requests."""

    row = deepcopy(profile)
    website = (row.get("evidence") or {}).get("website") or {}

    # Preserve all existing behavior when a site is already verified. This also preserves
    # H1g's spare-slot feed behavior.
    if _publishable(website):
        fallback_row, fallback = evaluate_hyphenated_no_fallback(
            row,
            timeout=timeout,
            base_site_logical_requests=base_site_logical_requests,
        )
        fallback["m12_strategy"] = "preserve_existing_verified_behavior"
        fallback["m12_candidate_attempted"] = False
        return fallback_row, fallback

    candidate = select_late_registry_domain_candidate(row)
    if candidate is None:
        fallback_row, fallback = evaluate_hyphenated_no_fallback(
            row,
            timeout=timeout,
            base_site_logical_requests=base_site_logical_requests,
        )
        fallback["m12_strategy"] = "preserve_h1g_no_m12_candidate"
        fallback["m12_candidate_attempted"] = False
        return fallback_row, fallback

    try:
        base_requests = int(base_site_logical_requests) if base_site_logical_requests is not None else -1
    except (TypeError, ValueError):
        base_requests = -1

    result: dict[str, Any] = {
        "organisation_number": str(row.get("organisation_number") or ""),
        "candidate_available": True,
        "candidate_domain": candidate["domain"],
        "attempted": False,
        "verified": False,
        "base_site_logical_requests": base_requests if base_requests >= 0 else None,
        "requests_added": 0,
        "post_site_logical_requests": base_requests if base_requests >= 0 else None,
        "bytes_added": 0,
        "latencies_ms": [],
        "skipped_reason": None,
        "guard_reasons": [],
        "activity_feed_attempted": False,
        "activity_feed_retained": False,
        "activity_feed_status": None,
        "activity_feed_skipped_reason": "website_not_verified",
        "m12_strategy": candidate["strategy"],
        "m12_candidate_attempted": False,
        "m12_registry_email_domain": candidate["registry_email_domain"],
    }

    if base_requests < 0:
        result["skipped_reason"] = "base_site_request_accounting_unavailable"
        return row, result
    if base_requests + 2 > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        result["skipped_reason"] = "site_request_budget_consumed"
        return row, result

    result["attempted"] = True
    result["m12_candidate_attempted"] = True
    result["activity_feed_skipped_reason"] = "m12_consumed_spare_slot"

    record, operations = fetch_bounded_homepage(
        candidate["url"],
        source_type="registry_email_domain_late_brand_candidate_website",
        timeout=timeout,
    )
    added = int(operations.get("requests") or 0)
    post = base_requests + added
    if post > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        raise RuntimeError(
            f"M12 exceeded site request ceiling for {row.get('organisation_number')}: "
            f"{post}>{MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE}"
        )
    result["requests_added"] = added
    result["post_site_logical_requests"] = post
    result["bytes_added"] = int(operations.get("bytes") or 0)
    result["latencies_ms"] = [
        int(value) for value in operations.get("latencies_ms") or [] if value is not None
    ]

    record["source_class"] = "company_owned_candidate"
    gated = apply_website_identity_gate(row, record)
    candidate_record = gated["website"]
    assessment = qualify_late_registry_domain_identity(
        row, candidate_record, gated.get("assessment")
    )
    value = candidate_record.get("value") or {}
    value["identity_assessment"] = assessment
    candidate_record["value"] = value

    evidence_map = row.setdefault("evidence", {})
    selected_before_guard = bool(
        assessment.get("publishable") and candidate_record.get("status") == "available"
    )
    evidence_map["website_m12_late_registry_domain_discovery"] = evidence(
        "website_m12_late_registry_domain_discovery",
        "available" if selected_before_guard else "not_found",
        "official_registry_email_domain_late_fallback",
        BRREG_BULK_URL,
        value={
            "registry_email_domain": candidate["registry_email_domain"],
            "candidate_domain": candidate["domain"],
            "candidate_strategy": candidate["strategy"],
            "candidate_is_identity_proof": False,
            "independent_page_url": (
                (candidate_record.get("value") or {}).get("final_url")
                if selected_before_guard else None
            ),
            "base_site_logical_requests": base_requests,
            "requests_added": added,
            "post_site_logical_requests": post,
            "third_party_cost_usd": 0.0,
        },
        source_row_key=row.get("organisation_number"),
        note=(
            "Public BRREG email-domain data nominates one late candidate in place of H1g; "
            "publication requires independent exact organisation-number or full legal-name "
            "plus registry-location proof. The email domain itself is not ownership evidence."
        ),
    )
    evidence_map["website_m12_late_registry_domain_candidate"] = candidate_record

    if selected_before_guard:
        trial = deepcopy(row)
        trial.setdefault("evidence", {})["website"] = candidate_record
        trial["website"] = (
            (candidate_record.get("value") or {}).get("final_url")
            or candidate_record.get("source_url")
            or ""
        )
        trial, guard_reasons = apply_registry_risk_guard(trial)
        result["guard_reasons"] = list(guard_reasons or [])
        guarded = (trial.get("evidence") or {}).get("website") or {}
        if _publishable(guarded):
            row["evidence"]["website"] = guarded
            row["website"] = trial.get("website") or ""
            result["verified"] = True
            result["selected_url"] = row["website"]
        else:
            result["selected_url"] = None
    else:
        result["selected_url"] = None

    return row, result
