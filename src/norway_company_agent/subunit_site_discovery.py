from __future__ import annotations

import re
import time
import urllib.parse
from collections import Counter
from typing import Any

from .domain_discovery import _page_contains_org_number, _page_matches_registry_location
from .final_site_discovery import (
    _add_metrics,
    _has_conflicting_explicit_org_number,
    fetch_bounded_homepage,
)
from .identity import _tokens, apply_website_identity_gate
from .website import _registered_domain, normalize_homepage

V6H_SCHEMA = "signalpost.brreg_subunit_site_discovery.v1"

FREE_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "hotmail.com", "hotmail.no", "outlook.com", "live.com",
    "icloud.com", "me.com", "yahoo.com", "yahoo.no", "proton.me", "protonmail.com",
    "online.no", "start.no", "telenor.no", "broadpark.no", "mail.com",
}


def _email_domain(value: str) -> str:
    text = str(value or "").strip().casefold()
    if "@" not in text:
        return ""
    domain = text.rsplit("@", 1)[1].strip(" .,:;<>[]()")
    registered = _registered_domain("https://" + domain)
    return registered or ""


def _candidate_from_website(value: str) -> tuple[str, str] | None:
    normalized = normalize_homepage(value)
    if not normalized:
        return None
    domain = _registered_domain(normalized)
    if not domain:
        return None
    return domain, normalized


def _domain_name_overlap(profile: dict[str, Any], domain: str) -> float:
    core = set(_tokens(profile.get("name")))
    if not core:
        return 0.0
    label = domain.split(".", 1)[0]
    observed = set(_tokens(re.sub(r"[-_]", " ", label)))
    if not observed:
        compact = "".join(_tokens(label))
        matched = {token for token in core if token in compact}
    else:
        matched = core & observed
    return len(matched) / len(core)


def subunit_site_candidates(profile: dict[str, Any], *, max_candidates: int = 3) -> list[dict[str, Any]]:
    """Nominate domains already filed on exact BRREG child subunits of the target.

    The BRREG values are discovery hints only. They do not establish that a fetched web
    page represents the target parent company, so an independent page identity gate is
    still mandatory before publication.
    """
    record = ((profile.get("evidence") or {}).get("locations") or {})
    rows = ((record.get("value") or {}).get("locations") or []) if record.get("status") == "available" else []
    raw: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        subunit_org = str(item.get("organisation_number") or "")
        subunit_name = str(item.get("name") or "")
        website_hint = str(item.get("website_hint") or "").strip()
        if website_hint:
            parsed = _candidate_from_website(website_hint)
            if parsed:
                domain, url = parsed
                raw.append({
                    "domain": domain,
                    "url": url,
                    "strategy": "brreg_subunit_registered_website",
                    "subunit_org": subunit_org,
                    "subunit_name": subunit_name,
                    "base_score": 100,
                })
        email_hint = str(item.get("email_hint") or "").strip()
        if email_hint:
            domain = _email_domain(email_hint)
            if domain and domain not in FREE_EMAIL_DOMAINS:
                raw.append({
                    "domain": domain,
                    "url": "https://" + domain + "/",
                    "strategy": "brreg_subunit_registered_email_domain",
                    "subunit_org": subunit_org,
                    "subunit_name": subunit_name,
                    "base_score": 65,
                })

    frequency = Counter(item["domain"] for item in raw)
    best: dict[str, dict[str, Any]] = {}
    for item in raw:
        domain = str(item["domain"])
        score = int(item["base_score"])
        reasons = [
            "domain is filed on a BRREG subunit returned by the target parent-org query",
            "candidate remains nomination-only until independently fetched page proves parent identity",
        ]
        if frequency[domain] >= 2:
            score += 20
            reasons.append(f"same domain repeated across {frequency[domain]} retained subunit hints")
        overlap = _domain_name_overlap(profile, domain)
        if overlap >= 0.75:
            score += 15
            reasons.append("domain label strongly overlaps parent legal name")
        elif overlap >= 0.5:
            score += 7
            reasons.append("domain label partially overlaps parent legal name")
        if domain.endswith(".no"):
            score += 5
            reasons.append("Norwegian .no domain")
        candidate = {
            **item,
            "rank_score": score,
            "rank_reasons": reasons,
            "hint_frequency": frequency[domain],
        }
        prior = best.get(domain)
        if prior is None or int(candidate["rank_score"]) > int(prior["rank_score"]):
            best[domain] = candidate

    ordered = sorted(
        best.values(),
        key=lambda item: (
            -int(item["rank_score"]),
            0 if item["strategy"] == "brreg_subunit_registered_website" else 1,
            item["domain"],
        ),
    )
    return ordered[: max(0, int(max_candidates))]


def _already_verified(profile: dict[str, Any]) -> bool:
    website = ((profile.get("evidence") or {}).get("website") or {})
    identity = ((website.get("value") or {}).get("identity_assessment") or {})
    return website.get("status") == "available" and bool(identity.get("publishable"))


def _strong_parent_identity(
    profile: dict[str, Any],
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> tuple[bool, str]:
    if website.get("status") != "available" or not assessment or not assessment.get("publishable"):
        return False, "base exact-company website gate did not publish"
    if _has_conflicting_explicit_org_number(profile, website):
        return False, "fetched page explicitly identifies a conflicting organisation number"
    if _page_contains_org_number(profile, website):
        return True, "fetched page independently shows the target parent organisation number"
    core = _tokens(profile.get("name"))
    if len(core) < 2:
        return False, "single-token parent name requires exact parent organisation number"
    if float(assessment.get("score") or 0.0) < 0.95:
        return False, "parent legal-name identity below exact threshold"
    if not _page_matches_registry_location(profile, website):
        return False, "fetched page does not corroborate the target parent BRREG location"
    return True, "exact parent legal name plus BRREG location independently corroborated on fetched page"


def probe_subunit_site_candidates(
    profiles: list[dict[str, Any]],
    *,
    max_logical_requests: int,
    timeout: float = 6.0,
    max_candidates_per_company: int = 1,
    request_charge_multiplier: int = 2,
) -> dict[str, Any]:
    start = time.monotonic()
    max_logical_requests = max(0, int(max_logical_requests))
    total: dict[str, Any] = {"requests": 0, "bytes": 0, "latencies_ms": []}
    attempts: list[dict[str, Any]] = []
    companies_with_candidates = 0
    verified = 0

    for profile in profiles:
        if _already_verified(profile):
            continue
        candidates = subunit_site_candidates(profile, max_candidates=max_candidates_per_company)
        if not candidates:
            continue
        companies_with_candidates += 1
        for candidate in candidates:
            # Existing bounded homepage fetch is robots + homepage = up to 2 logical requests.
            if int(total["requests"]) + 2 > max_logical_requests:
                break
            record, metrics = fetch_bounded_homepage(
                candidate.get("url"),
                source_type="brreg_subunit_domain_candidate",
                timeout=timeout,
            )
            _add_metrics(total, metrics)
            gated = apply_website_identity_gate(profile, record)
            candidate_record = gated["website"]
            assessment = gated.get("assessment")
            publishable, reason = _strong_parent_identity(profile, candidate_record, assessment)
            attempts.append({
                "organisation_number": str(profile.get("organisation_number") or ""),
                "company_name": profile.get("name"),
                "candidate_domain": candidate.get("domain"),
                "candidate_strategy": candidate.get("strategy"),
                "candidate_rank_score": candidate.get("rank_score"),
                "candidate_rank_reasons": candidate.get("rank_reasons"),
                "subunit_org": candidate.get("subunit_org"),
                "subunit_name": candidate.get("subunit_name"),
                "fetched_status": candidate_record.get("status"),
                "final_url": (candidate_record.get("value") or {}).get("final_url"),
                "content_sha256": candidate_record.get("content_sha256"),
                "identity_assessment": assessment,
                "publishable": publishable,
                "publication_reason": reason,
                "logical_requests": int(metrics.get("requests") or 0),
            })
            if publishable:
                value = candidate_record.get("value") or {}
                value["identity_assessment"] = {
                    **dict(assessment or {}),
                    "status": "exact",
                    "publishable": True,
                    "method": "brreg_subunit_hint_plus_independent_parent_identity_v1",
                    "reasons": [*list((assessment or {}).get("reasons") or []), reason],
                }
                candidate_record["value"] = value
                evidence_map = profile.setdefault("evidence", {})
                evidence_map["website_subunit_candidate"] = candidate_record
                evidence_map["website"] = candidate_record
                profile["website"] = value.get("final_url") or candidate_record.get("source_url") or ""
                verified += 1
                break
        if int(total["requests"]) >= max_logical_requests:
            break

    return {
        "schema": V6H_SCHEMA,
        "companies_with_candidates": companies_with_candidates,
        "attempts": len(attempts),
        "verified": verified,
        "logical_requests": int(total["requests"]),
        "conservative_request_charge": int(total["requests"]) * int(request_charge_multiplier),
        "bytes": int(total["bytes"]),
        "latencies_ms": list(total["latencies_ms"]),
        "runtime_seconds": round(time.monotonic() - start, 3),
        "third_party_api_cost_usd": 0.0,
        "attempt_audit": attempts,
    }
