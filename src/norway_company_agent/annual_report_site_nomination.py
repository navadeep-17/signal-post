from __future__ import annotations

import re
import urllib.parse
from copy import deepcopy
from typing import Any

import tldextract

from .domain_discovery import (
    GENERIC_EMAIL_DOMAINS,
    _domain_identity_strength,
    _page_contains_full_legal_name,
    _page_contains_org_number,
    _page_matches_registry_location,
    distinctive_legal_name_tokens,
    registry_email_domain_candidates,
)
from .final_site_discovery import (
    _has_conflicting_explicit_org_number,
    _publishable,
    fetch_bounded_homepage,
)
from .identity import apply_website_identity_gate
from .zero_cost_discovery import deterministic_domain_candidates
from .zero_cost_registry_guard import apply_registry_risk_guard


URL_RE = re.compile(
    r"(?i)\bhttps?://(?:www\.)?[a-z0-9](?:[a-z0-9._-]{0,251}[a-z0-9])?"
    r"\.[a-z]{2,63}(?:/[^\s<>\[\]{}()]*)?"
)
WWW_RE = re.compile(
    r"(?i)\bwww\.[a-z0-9](?:[a-z0-9._-]{0,251}[a-z0-9])?\.[a-z]{2,63}\b"
)

BARE_NO_RE = re.compile(
    r"(?i)(?<![a-z0-9.-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+no\b"
)

EXCLUDED_REGISTERED_DOMAINS = {
    "altinn.no",
    "brreg.no",
    "skatteetaten.no",
    "regjeringen.no",
    "lovdata.no",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "youtu.be",
    "vimeo.com",
}


def _registered_domain(host: str) -> str:
    ext = tldextract.extract(host)
    return str(ext.top_domain_under_public_suffix or "").casefold().rstrip(".")


def _normalise_candidate(raw: str) -> tuple[str, str] | None:
    text = str(raw or "").strip().strip(".,;:!?)]}'\"")
    if text.casefold().startswith("www."):
        text = "https://" + text
    try:
        parsed = urllib.parse.urlparse(text)
    except ValueError:
        return None
    host = (parsed.hostname or "").casefold().rstrip(".")
    if parsed.scheme not in {"http", "https"} or not host:
        return None
    registered = _registered_domain(host)
    if not registered or registered in EXCLUDED_REGISTERED_DOMAINS:
        return None
    if any(
        registered == blocked or registered.endswith("." + blocked)
        for blocked in EXCLUDED_REGISTERED_DOMAINS
    ):
        return None
    return registered, f"https://{registered}/"


def extract_annual_report_site_candidates(
    profile: dict[str, Any],
    text: str,
    *,
    max_candidates: int = 3,
) -> list[dict[str, Any]]:
    """Nominate website domains from exact-org annual-report text.

    These are discovery hints only. They are never publication evidence for the website.
    Publication still requires an independent company-page fetch and exact-entity gate.
    """

    if max_candidates < 1:
        return []
    org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    digits = re.sub(r"\D", "", str(text or ""))
    if len(org) != 9 or org not in digits:
        return []

    raw_text = str(text or "")
    matches: list[tuple[int, int, str, str]] = []
    seen_spans: set[tuple[int, int]] = set()
    for method, pattern, base_score in (
        ("explicit_http_url", URL_RE, 3),
        ("explicit_www_domain", WWW_RE, 2),
    ):
        for match in pattern.finditer(raw_text):
            span_key = (match.start(), match.end())
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)
            normalised = _normalise_candidate(match.group(0))
            if normalised is None:
                continue
            domain, url = normalised
            start = max(0, match.start() - 180)
            end = min(len(raw_text), match.end() + 180)
            context = " ".join(raw_text[start:end].split())
            score = base_score
            if "www." in match.group(0).casefold():
                score += 1
            if org and org in re.sub(r"\D", "", context):
                score += 2
            matches.append((score, match.start(), domain, url + "\t" + method + "\t" + context[:500]))

    by_domain: dict[str, dict[str, Any]] = {}
    for score, position, domain, packed in sorted(matches, key=lambda x: (-x[0], x[1], x[2])):
        url, method, context = packed.split("\t", 2)
        existing = by_domain.get(domain)
        if existing is not None:
            continue
        by_domain[domain] = {
            "domain": domain,
            "url": url,
            "method": method,
            "score": score,
            "position": position,
            "evidence_span": context,
            "claim_scope": (
                "Exact-org official annual report contains this URL/domain. "
                "This nominates a candidate only; it does not establish website ownership."
            ),
        }
        if len(by_domain) >= max_candidates:
            break
    return list(by_domain.values())


def extract_annual_report_bare_no_candidates(
    profile: dict[str, Any],
    text: str,
    *,
    max_candidates: int = 3,
) -> list[dict[str, Any]]:
    """Nominate only genuinely new bare .no domains from an exact-org annual report.

    Explicit http(s)/www candidates belong to M15. Registry-email and deterministic
    compact/hyphenated legal-name domains belong to existing V8/H1 discovery. M16 keeps
    only report-specific bare .no domains whose registered-domain label is compatible
    with the legal name. As with M15, nomination never establishes website ownership.
    """

    if max_candidates < 1:
        return []

    org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    raw_text = str(text or "")
    if len(org) != 9 or org not in re.sub(r"\D", "", raw_text):
        return []

    already_tried: set[str] = set()
    for item in deterministic_domain_candidates(profile, max_candidates=2).get("candidates") or []:
        domain = str(item.get("domain") or "").casefold().rstrip(".")
        if domain:
            already_tried.add(domain)
    for item in registry_email_domain_candidates(profile).get("candidates") or []:
        domain = str(item.get("domain") or "").casefold().rstrip(".")
        if domain:
            already_tried.add(domain)
    for item in extract_annual_report_site_candidates(profile, raw_text, max_candidates=20):
        domain = str(item.get("domain") or "").casefold().rstrip(".")
        if domain:
            already_tried.add(domain)

    legal_tokens = distinctive_legal_name_tokens(profile.get("name"))
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    for match in BARE_NO_RE.finditer(raw_text):
        token = match.group(0).casefold().rstrip(".")
        if token.startswith("www."):
            continue
        prefix = raw_text[max(0, match.start() - 10):match.start()].casefold()
        if prefix.endswith("http://") or prefix.endswith("https://"):
            continue

        registered = _registered_domain(token)
        if (
            not registered
            or not registered.endswith(".no")
            or registered in seen
            or registered in already_tried
            or registered in EXCLUDED_REGISTERED_DOMAINS
            or registered in GENERIC_EMAIL_DOMAINS
        ):
            continue

        strength = _domain_identity_strength(profile, registered)
        if strength not in {"exact", "multi", "acronym"}:
            continue

        start = max(0, match.start() - 180)
        end = min(len(raw_text), match.end() + 180)
        context = " ".join(raw_text[start:end].split())
        is_email_domain = match.start() > 0 and raw_text[match.start() - 1] == "@"

        score = {"exact": 6, "multi": 5, "acronym": 4}[strength]
        if is_email_domain:
            score += 1
        if org in re.sub(r"\D", "", context):
            score += 2
        context_folded = context.casefold()
        if legal_tokens and all(token in context_folded for token in legal_tokens):
            score += 1

        seen.add(registered)
        candidates.append(
            {
                "domain": registered,
                "url": f"https://{registered}/",
                "method": (
                    "annual_report_email_domain"
                    if is_email_domain
                    else "annual_report_bare_no_domain"
                ),
                "identity_strength": strength,
                "score": score,
                "position": match.start(),
                "evidence_span": context[:500],
                "claim_scope": (
                    "Exact-org official annual report contains this bare .no domain. "
                    "The domain is only a discovery candidate; publication requires an "
                    "independent first-party fetch and exact-company identity verification."
                ),
            }
        )

    candidates.sort(
        key=lambda row: (
            -int(row.get("score") or 0),
            int(row.get("position") or 0),
            str(row.get("domain") or ""),
        )
    )
    return candidates[:max_candidates]


def _quarantine(assessment: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **assessment,
        "status": "review",
        "score": min(float(assessment.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [*list(assessment.get("reasons") or []), reason],
        "method": "annual_report_site_nomination_exact_page_v1",
    }


def qualify_annual_report_candidate_identity(
    profile: dict[str, Any],
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Apply a strict page-local identity rule to a filing-nominated candidate."""

    if not assessment or not assessment.get("publishable") or website.get("status") != "available":
        return assessment

    if _has_conflicting_explicit_org_number(profile, website):
        return _quarantine(
            assessment,
            "filing-nominated candidate independently identifies a different organisation number",
        )

    if _page_contains_org_number(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "independently fetched filing-nominated page contains exact target organisation number",
            ],
            "method": "annual_report_site_nomination_exact_page_v1",
        }

    if _page_contains_full_legal_name(profile, website) and _page_matches_registry_location(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": max(float(assessment.get("score") or 0.95), 0.98),
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "independently fetched filing-nominated page has full legal name plus BRREG location",
            ],
            "method": "annual_report_site_nomination_exact_page_v1",
        }

    return _quarantine(
        assessment,
        "filing nomination alone is insufficient; independent page lacks exact org-number or legal-name-plus-location proof",
    )


def evaluate_annual_report_site_candidates(
    profile: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    timeout: float = 6.0,
    max_candidates: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Independently fetch and exact-verify bounded annual-report site nominations."""

    row = deepcopy(profile)
    result: dict[str, Any] = {
        "organisation_number": str(row.get("organisation_number") or ""),
        "candidate_count": len(candidates),
        "attempted": 0,
        "verified": False,
        "selected_domain": None,
        "selected_url": None,
        "requests": 0,
        "bytes": 0,
        "latencies_ms": [],
        "candidate_results": [],
        "guard_reasons": [],
    }

    current = ((row.get("evidence") or {}).get("website") or {})
    if _publishable(current):
        result["skipped_reason"] = "verified_website_already_present"
        return row, result

    for candidate in candidates[: max(0, int(max_candidates))]:
        result["attempted"] += 1
        record, operations = fetch_bounded_homepage(
            str(candidate.get("url") or ""),
            source_type="official_annual_report_domain_candidate",
            timeout=timeout,
        )
        result["requests"] += int(operations.get("requests") or 0)
        result["bytes"] += int(operations.get("bytes") or 0)
        result["latencies_ms"].extend(
            int(v) for v in (operations.get("latencies_ms") or []) if v is not None
        )

        record["source_class"] = "company_owned_candidate"
        gated = apply_website_identity_gate(row, record)
        candidate_record = gated["website"]
        assessment = qualify_annual_report_candidate_identity(
            row,
            candidate_record,
            gated.get("assessment"),
        )
        if assessment is not None:
            value = candidate_record.get("value") or {}
            value["identity_assessment"] = assessment
            candidate_record["value"] = value

        candidate_result = {
            "domain": candidate.get("domain"),
            "nomination_method": candidate.get("method"),
            "annual_report_evidence_span": candidate.get("evidence_span"),
            "website_status": candidate_record.get("status"),
            "identity_status": (assessment or {}).get("status"),
            "identity_score": (assessment or {}).get("score"),
            "identity_publishable": bool((assessment or {}).get("publishable")),
            "identity_reasons": list((assessment or {}).get("reasons") or []),
            "website_source_url": candidate_record.get("source_url"),
            "website_content_sha256": candidate_record.get("content_sha256"),
            "final_url": (candidate_record.get("value") or {}).get("final_url"),
        }
        result["candidate_results"].append(candidate_result)

        if not (
            assessment
            and assessment.get("publishable")
            and candidate_record.get("status") == "available"
        ):
            continue

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
        if not _publishable(guarded):
            continue

        row["evidence"]["website"] = guarded
        row["website"] = trial.get("website") or ""
        result["verified"] = True
        result["selected_domain"] = candidate.get("domain")
        result["selected_url"] = row["website"]
        break

    if not result["attempted"]:
        result["skipped_reason"] = "no_candidate"
    return row, result
