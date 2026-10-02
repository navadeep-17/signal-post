from __future__ import annotations

import re
import time
import urllib.parse
from typing import Any

from .company_site_contact import EMAIL_RE
from .domain_discovery import _page_contains_org_number, _page_matches_registry_location
from .final_site_discovery import (
    _add_metrics,
    _has_conflicting_explicit_org_number,
    fetch_bounded_homepage,
)
from .identity import _tokens, apply_website_identity_gate
from .website import _registered_domain

V6E_SCHEMA = "signalpost.annual_report_domain_discovery.v1"

URL_RE = re.compile(
    r"(?i)(?<![@\w])((?:https?://|www\.)[a-z0-9æøå][a-z0-9æøå.-]{1,180}(?::\d{2,5})?(?:/[^^\s<>()\[\]{}\"']*)?)"
)

FREE_OR_PERSONAL_DOMAINS = {
    "gmail.com", "googlemail.com", "hotmail.com", "hotmail.no", "outlook.com", "live.com",
    "icloud.com", "me.com", "yahoo.com", "yahoo.no", "proton.me", "protonmail.com",
    "online.no", "start.no", "telenor.no", "broadpark.no", "mail.com",
}

# High-frequency report/audit infrastructure domains that are not the filing company's site.
KNOWN_REPORT_VENDOR_DOMAINS = {
    "brreg.no", "altinn.no", "signant.no", "penneo.com", "bankid.no", "digipost.no",
    "pwc.no", "pwc.com", "ey.com", "deloitte.no", "deloitte.com", "kpmg.no", "kpmg.com",
    "bdo.no", "bdo.global", "rsmnorge.no", "rsm.global",
}

NEGATIVE_CONTEXT_TERMS = (
    "revisor", "revisjon", "auditor", "audit firm", "regnskapsfører", "regnskapsforer",
    "accountant", "accounting firm", "bankforbindelse", "bank connection",
)
WEB_CONTEXT_TERMS = (
    "nettside", "hjemmeside", "website", "webside", "www", "internet", "internett",
)
CONTACT_CONTEXT_TERMS = (
    "kontakt", "contact", "e-post", "epost", "email", "e-mail",
)
GENERIC_LOCAL_PARTS = {
    "info", "post", "kontakt", "contact", "office", "firmapost", "mail", "hei", "hello",
    "admin", "kundeservice", "support",
}


def _clean_candidate_url(value: str) -> str:
    text = str(value or "").strip().rstrip(".,;:!?)]}>'\"")
    if text.casefold().startswith("www."):
        text = "https://" + text
    try:
        parsed = urllib.parse.urlparse(text)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname.strip(".").casefold()
    if not host or host.startswith("www.") and host.count(".") < 2:
        return ""
    return urllib.parse.urlunparse(("https", host, "/", "", "", ""))


def _domain_from_email(email: str) -> str:
    value = str(email or "").strip().casefold().rstrip(".,;:!?)]}>'\"")
    if "@" not in value:
        return ""
    return value.rsplit("@", 1)[1].strip(".")


def _context(text: str, start: int, end: int, radius: int = 180) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return " ".join(text[left:right].replace("\n", " ").split())[:500]


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return any(term in folded for term in terms)


def _company_tokens(profile: dict[str, Any]) -> set[str]:
    return set(_tokens(profile.get("name")))


def _context_has_company_name(profile: dict[str, Any], context: str) -> bool:
    core = _company_tokens(profile)
    if not core:
        return False
    observed = set(_tokens(context))
    if len(core) == 1:
        return next(iter(core)) in observed
    return core.issubset(observed)


def _rank_candidate(
    profile: dict[str, Any],
    *,
    domain: str,
    strategy: str,
    context: str,
    local_part: str | None = None,
) -> tuple[int, list[str]]:
    reasons: list[str] = []
    registered = _registered_domain("https://" + domain)
    if not registered or registered in FREE_OR_PERSONAL_DOMAINS or registered in KNOWN_REPORT_VENDOR_DOMAINS:
        return -999, ["blocked generic/report-vendor domain"]
    if _contains_any(context, NEGATIVE_CONTEXT_TERMS):
        return -200, ["auditor/accounting context"]

    score = 0
    if strategy == "explicit_url":
        score += 70
        reasons.append("explicit URL in exact-org official annual report")
        if _contains_any(context, WEB_CONTEXT_TERMS):
            score += 30
            reasons.append("website-labelled context")
        if _context_has_company_name(profile, context):
            score += 20
            reasons.append("legal company name in local context")
        if _contains_any(context, CONTACT_CONTEXT_TERMS):
            score += 10
            reasons.append("contact context")
    elif strategy == "email_domain":
        score += 45
        reasons.append("email domain in exact-org official annual report")
        if str(local_part or "").casefold() in GENERIC_LOCAL_PARTS:
            score += 20
            reasons.append("company-style generic mailbox")
        if _context_has_company_name(profile, context):
            score += 25
            reasons.append("legal company name in local context")
        if _contains_any(context, CONTACT_CONTEXT_TERMS):
            score += 15
            reasons.append("contact context")

    tld = registered.rsplit(".", 1)[-1] if "." in registered else ""
    if tld == "no":
        score += 10
        reasons.append("Norwegian .no domain")
    elif tld == "com":
        score += 3
        reasons.append("commercial .com domain")
    return score, reasons


def extract_annual_report_domain_candidates(
    profile: dict[str, Any],
    text: str,
    *,
    max_candidates: int = 3,
) -> list[dict[str, Any]]:
    """Nominate bounded website candidates from an exact-org annual report.

    Candidate rows are discovery hints only. They are never evidence and never publish a
    website without a separately fetched page passing the strict identity gate.
    """
    candidates: dict[str, dict[str, Any]] = {}

    for match in URL_RE.finditer(text):
        url = _clean_candidate_url(match.group(1))
        if not url:
            continue
        domain = _registered_domain(url)
        if not domain:
            continue
        context = _context(text, match.start(), match.end())
        score, reasons = _rank_candidate(profile, domain=domain, strategy="explicit_url", context=context)
        if score < 60:
            continue
        row = {
            "domain": domain,
            "url": "https://" + domain + "/",
            "strategy": "explicit_url",
            "rank_score": score,
            "rank_reasons": reasons,
            "context": context,
        }
        prior = candidates.get(domain)
        if prior is None or int(row["rank_score"]) > int(prior["rank_score"]):
            candidates[domain] = row

    for match in EMAIL_RE.finditer(text):
        email = match.group(1).strip().casefold()
        domain = _domain_from_email(email)
        if not domain:
            continue
        registered = _registered_domain("https://" + domain)
        if not registered:
            continue
        context = _context(text, match.start(), match.end())
        local_part = email.rsplit("@", 1)[0]
        score, reasons = _rank_candidate(
            profile,
            domain=registered,
            strategy="email_domain",
            context=context,
            local_part=local_part,
        )
        if score < 60:
            continue
        row = {
            "domain": registered,
            "url": "https://" + registered + "/",
            "strategy": "email_domain",
            "rank_score": score,
            "rank_reasons": reasons,
            "context": context,
            "email_local_part": local_part,
        }
        prior = candidates.get(registered)
        if prior is None or int(row["rank_score"]) > int(prior["rank_score"]):
            candidates[registered] = row

    ordered = sorted(
        candidates.values(),
        key=lambda row: (-int(row["rank_score"]), 0 if row["strategy"] == "explicit_url" else 1, row["domain"]),
    )
    return ordered[: max(0, int(max_candidates))]


def _already_verified(profile: dict[str, Any]) -> bool:
    website = ((profile.get("evidence") or {}).get("website") or {})
    identity = ((website.get("value") or {}).get("identity_assessment") or {})
    return website.get("status") == "available" and bool(identity.get("publishable"))


def _strong_independent_identity(profile: dict[str, Any], website: dict[str, Any], assessment: dict[str, Any] | None) -> tuple[bool, str]:
    if website.get("status") != "available" or not assessment or not assessment.get("publishable"):
        return False, "base exact-company identity gate did not publish"
    if _has_conflicting_explicit_org_number(profile, website):
        return False, "page explicitly identifies a conflicting organisation number"
    if _page_contains_org_number(profile, website):
        return True, "exact target organisation number independently appears on fetched company page"

    core = _tokens(profile.get("name"))
    # Single-token legal names are too collision-prone for the name+location route.
    if len(core) < 2:
        return False, "single-token legal name requires exact organisation number on fetched page"
    if float(assessment.get("score") or 0.0) < 0.95:
        return False, "legal-name evidence below exact threshold"
    if not _page_matches_registry_location(profile, website):
        return False, "fetched page lacks BRREG location corroboration"
    return True, "exact legal company name plus independently corroborated BRREG location"


def probe_annual_report_candidates(
    profiles: list[dict[str, Any]],
    *,
    max_logical_requests: int,
    timeout: float = 6.0,
    max_candidates_per_company: int = 1,
    request_charge_multiplier: int = 2,
) -> dict[str, Any]:
    """Probe annual-report-nominated domains under one global bounded request allowance."""
    start = time.monotonic()
    max_logical_requests = max(0, int(max_logical_requests))
    total = {"requests": 0, "bytes": 0, "latencies_ms": []}
    attempts: list[dict[str, Any]] = []
    verified = 0
    companies_with_candidates = 0

    for profile in profiles:
        if _already_verified(profile):
            continue
        candidates = list(profile.get("annual_report_website_candidates") or [])[: max(0, int(max_candidates_per_company))]
        if not candidates:
            continue
        companies_with_candidates += 1
        for candidate in candidates:
            # fetch_bounded_homepage uses robots + homepage = up to two logical requests.
            if int(total["requests"]) + 2 > max_logical_requests:
                break
            record, metrics = fetch_bounded_homepage(
                candidate.get("url"),
                source_type="official_annual_report_domain_candidate",
                timeout=timeout,
            )
            _add_metrics(total, metrics)
            gated = apply_website_identity_gate(profile, record)
            candidate_record = gated["website"]
            assessment = gated.get("assessment")
            publishable, reason = _strong_independent_identity(profile, candidate_record, assessment)
            attempt = {
                "organisation_number": str(profile.get("organisation_number") or ""),
                "company_name": profile.get("name"),
                "candidate_domain": candidate.get("domain"),
                "candidate_strategy": candidate.get("strategy"),
                "candidate_rank_score": candidate.get("rank_score"),
                "candidate_rank_reasons": candidate.get("rank_reasons"),
                "candidate_context": candidate.get("context"),
                "fetched_status": candidate_record.get("status"),
                "final_url": (candidate_record.get("value") or {}).get("final_url"),
                "content_sha256": candidate_record.get("content_sha256"),
                "base_identity_assessment": assessment,
                "publishable": publishable,
                "publication_reason": reason,
                "logical_requests": int(metrics.get("requests") or 0),
            }
            attempts.append(attempt)
            if publishable:
                value = candidate_record.get("value") or {}
                value["identity_assessment"] = {
                    **dict(assessment or {}),
                    "publishable": True,
                    "status": "exact",
                    "method": "annual_report_candidate_plus_independent_page_identity_v1",
                    "reasons": [*list((assessment or {}).get("reasons") or []), reason],
                }
                candidate_record["value"] = value
                evidence_map = profile.setdefault("evidence", {})
                evidence_map["website_annual_report_candidate"] = candidate_record
                evidence_map["website"] = candidate_record
                profile["website"] = value.get("final_url") or candidate_record.get("source_url") or ""
                profile["website_discovery_strategy"] = "annual_report_candidate_independent_exact_identity"
                verified += 1
                break
        if int(total["requests"]) >= max_logical_requests:
            break

    return {
        "schema": V6E_SCHEMA,
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
