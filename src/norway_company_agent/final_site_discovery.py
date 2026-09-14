from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.request
import urllib.robotparser
from copy import deepcopy
from typing import Any

from bs4 import BeautifulSoup
import extruct
import trafilatura

from .domain_discovery import qualify_registry_email_domain_identity, registry_email_domain_candidates
from .evidence import evidence
from .identity import apply_website_identity_gate
from .website import (
    USER_AGENT,
    _extraction_state,
    _jsonld_organisations,
    _registered_domain,
    _social_links,
    assert_public_url,
    normalize_homepage,
)
from .zero_cost_discovery import deterministic_domain_candidates, qualify_deterministic_domain_identity
from .zero_cost_registry_guard import apply_registry_risk_guard

BRREG_BULK_URL = "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv"
MAX_REDIRECTS_PER_REQUEST = 1
MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE = 4


class BoundedSafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """SSRF-safe redirect handler with a single-hop ceiling."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        assert_public_url(newurl)
        redirect_count = int(getattr(req, "_signalpost_redirect_count", 0))
        if redirect_count >= MAX_REDIRECTS_PER_REQUEST:
            raise urllib.error.HTTPError(newurl, code, "Signalpost redirect limit exceeded", headers, fp)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            setattr(redirected, "_signalpost_redirect_count", redirect_count + 1)
        return redirected


BOUNDED_SAFE_OPENER = urllib.request.build_opener(BoundedSafeRedirectHandler())


def _robots_allowed(url: str, timeout: float) -> tuple[bool, int]:
    """Return robots decision plus one logical request charge.

    An unavailable robots file follows the starter policy: one ordinary homepage GET is
    allowed, but no deeper crawl occurs in this final evaluator path.
    """
    assert_public_url(url)
    parsed = urllib.request.urlparse(url) if hasattr(urllib.request, "urlparse") else None
    if parsed is None:
        import urllib.parse

        parsed = urllib.parse.urlparse(url)
        robots_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    else:
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        request = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            parser.parse(response.read().decode("utf-8", errors="replace").splitlines())
        return parser.can_fetch(USER_AGENT, url), 1
    except Exception:
        return True, 1


def fetch_bounded_homepage(
    url: str | None,
    *,
    source_type: str,
    timeout: float = 6.0,
    max_bytes: int = 750_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch robots + homepage only, with at most one redirect per logical request."""
    normalized = normalize_homepage(url)
    metrics: dict[str, Any] = {"requests": 0, "bytes": 0, "latencies_ms": []}
    if not normalized:
        return evidence("website", "not_found", source_type, str(url or BRREG_BULK_URL), note="No valid homepage URL"), metrics
    try:
        assert_public_url(normalized)
    except ValueError as exc:
        return evidence("website", "blocked", source_type, normalized, note=str(exc)), metrics

    allowed, robots_requests = _robots_allowed(normalized, timeout)
    metrics["requests"] += robots_requests
    if not allowed:
        return evidence("website", "blocked", source_type, normalized, note="robots.txt disallows this user agent"), metrics

    started = time.monotonic()
    request = urllib.request.Request(
        normalized,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    metrics["requests"] += 1
    try:
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            elapsed = int((time.monotonic() - started) * 1000)
            final_url = response.geturl()
            assert_public_url(final_url)
            content_type = response.headers.get("content-type", "")
        metrics["bytes"] += len(raw)
        metrics["latencies_ms"].append(elapsed)
        if len(raw) > max_bytes:
            return evidence("website", "blocked", source_type, normalized, note="Homepage exceeds byte limit"), metrics
        if "html" not in content_type.casefold():
            return evidence("website", "source_error", source_type, normalized, note=f"Unsupported content type: {content_type}"), metrics

        html = raw.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        structured = extruct.extract(html, base_url=final_url, syntaxes=["json-ld", "microdata", "opengraph"])
        text = trafilatura.extract(html, url=final_url, include_links=False, include_tables=False, favor_precision=True) or ""
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description_tag = soup.select_one('meta[name="description"], meta[property="og:description"]')
        description = str(description_tag.get("content") or "").strip() if description_tag else ""
        digest = hashlib.sha256(raw).hexdigest()
        value = {
            "requested_url": normalized,
            "final_url": final_url,
            "registered_domain": _registered_domain(final_url),
            "title": title[:500],
            "description": description[:2000],
            "main_text_excerpt": text[:5000],
            "social_links": _social_links(final_url, soup),
            "structured_organisations": _jsonld_organisations(structured),
            "content_sha256": digest,
            "extraction_state": _extraction_state(text, soup),
            "pages": [{
                "url": final_url,
                "title": title[:500],
                "main_text_excerpt": text[:5000],
                "content_sha256": digest,
            }],
            "crawl_errors": [],
        }
        return evidence(
            "website",
            "available",
            source_type,
            final_url,
            value=value,
            note="Bounded homepage-only final evaluator evidence",
            content_sha256=digest,
        ), metrics
    except urllib.error.HTTPError as exc:
        elapsed = int((time.monotonic() - started) * 1000)
        metrics["latencies_ms"].append(elapsed)
        status = "not_found" if exc.code in {404, 410} else "source_error"
        return evidence("website", status, source_type, normalized, note=f"HTTP {exc.code}"), metrics
    except Exception as exc:
        elapsed = int((time.monotonic() - started) * 1000)
        metrics["latencies_ms"].append(elapsed)
        return evidence("website", "source_error", source_type, normalized, note=f"{type(exc).__name__}: {str(exc)[:180]}"), metrics


def _add_metrics(total: dict[str, Any], item: dict[str, Any]) -> None:
    total["requests"] += int(item.get("requests") or 0)
    total["bytes"] += int(item.get("bytes") or 0)
    total["latencies_ms"].extend(int(value) for value in item.get("latencies_ms") or [] if value is not None)


def _publishable(record: dict[str, Any]) -> bool:
    identity = (record.get("value") or {}).get("identity_assessment") or {}
    return record.get("status") == "available" and bool(identity.get("publishable"))


def discover_final_website(profile: dict[str, Any], *, timeout: float = 6.0) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve a canonical company website with at most two homepage probes.

    Order:
    1. registry website, when present; otherwise one registry-email-domain candidate;
    2. one deterministic legal-name .no candidate if still unresolved.
    Every publication requires the existing exact-identity gates. H1c additionally passes
    the registry-risk guard. Failed guesses never replace a registry-linked terminal record.
    """
    row = deepcopy(profile)
    total: dict[str, Any] = {
        "requests": 0,
        "bytes": 0,
        "latencies_ms": [],
        "registry_attempted": False,
        "email_attempted": False,
        "h1c_attempted": False,
        "selected_source": None,
        "promoted": False,
    }
    evidence_map = row.setdefault("evidence", {})
    registry_terminal: dict[str, Any] | None = None
    registry_url = str(row.get("website") or "").strip()

    if registry_url:
        total["registry_attempted"] = True
        record, ops = fetch_bounded_homepage(
            registry_url,
            source_type="registry_linked_company_website",
            timeout=timeout,
        )
        _add_metrics(total, ops)
        gated = apply_website_identity_gate(row, record)
        registry_terminal = gated["website"]
        evidence_map["website"] = registry_terminal
        if _publishable(registry_terminal):
            total["selected_source"] = "registry_website"
            total["promoted"] = True
            return row, total
    else:
        plan = registry_email_domain_candidates(row)
        candidates = plan.get("candidates") or []
        if plan.get("eligible") and candidates:
            candidate = candidates[0]
            total["email_attempted"] = True
            record, ops = fetch_bounded_homepage(
                candidate["url"],
                source_type="registry_email_domain_candidate_website",
                timeout=timeout,
            )
            _add_metrics(total, ops)
            record["source_class"] = "company_owned_candidate"
            gated = apply_website_identity_gate(row, record)
            candidate_record = gated["website"]
            assessment = qualify_registry_email_domain_identity(
                row,
                candidate["domain"],
                candidate_record,
                gated.get("assessment"),
            )
            if assessment is not None:
                value = candidate_record.get("value") or {}
                value["identity_assessment"] = assessment
                candidate_record["value"] = value
            selected = bool(assessment and assessment.get("publishable") and candidate_record.get("status") == "available")
            evidence_map["website_email_discovery"] = evidence(
                "website_email_discovery",
                "available" if selected else "not_found",
                "official_registry_email_domain_discovery",
                BRREG_BULK_URL,
                value={
                    "candidate_domain": candidate["domain"],
                    "selected_url": (candidate_record.get("value") or {}).get("final_url") if selected else None,
                    "publishable": selected,
                    "third_party_cost_usd": 0.0,
                },
                source_row_key=row.get("organisation_number"),
                note="One public BRREG email-domain candidate independently fetched; no search provider used.",
            )
            if selected:
                evidence_map["website_email_candidate"] = candidate_record
                evidence_map["website"] = candidate_record
                row["website"] = (candidate_record.get("value") or {}).get("final_url") or candidate_record.get("source_url") or ""
                total["selected_source"] = "registry_email_domain"
                total["promoted"] = True
                return row, total

    h1c_plan = deterministic_domain_candidates(row, max_candidates=1)
    h1c_candidates = h1c_plan.get("candidates") or []
    if h1c_plan.get("eligible") and h1c_candidates:
        candidate = h1c_candidates[0]
        total["h1c_attempted"] = True
        record, ops = fetch_bounded_homepage(
            candidate["url"],
            source_type="deterministic_legal_name_domain_guess",
            timeout=timeout,
        )
        _add_metrics(total, ops)
        gated = apply_website_identity_gate(row, record)
        candidate_record = gated["website"]
        assessment = qualify_deterministic_domain_identity(
            row,
            candidate["domain"],
            candidate_record,
            gated.get("assessment"),
        )
        if assessment is not None:
            value = candidate_record.get("value") or {}
            value["identity_assessment"] = assessment
            candidate_record["value"] = value
        selected = bool(assessment and assessment.get("publishable") and candidate_record.get("status") == "available")
        evidence_map["website_discovery_zero_cost"] = evidence(
            "website_discovery_zero_cost",
            "available" if selected else "not_found",
            "deterministic_legal_name_domain_guess",
            candidate_record.get("source_url") or candidate["url"],
            value={
                "candidate_strategy": candidate["strategy"],
                "candidate_domain": candidate["domain"],
                "independent_page_url": (candidate_record.get("value") or {}).get("final_url") if selected else None,
                "third_party_cost_usd": 0.0,
            },
            note="One deterministic .no candidate independently fetched; no search API used.",
            content_sha256=candidate_record.get("content_sha256"),
        )
        evidence_map["website_discovered_zero_cost"] = candidate_record
        if selected:
            evidence_map["website"] = candidate_record
            row["website"] = (candidate_record.get("value") or {}).get("final_url") or candidate_record.get("source_url") or ""
            row, reasons = apply_registry_risk_guard(row)
            if _publishable((row.get("evidence") or {}).get("website") or {}):
                total["selected_source"] = "h1c_deterministic_domain"
                total["promoted"] = True
                return row, total
            total["h1c_guard_reasons"] = reasons

    if registry_terminal is not None:
        evidence_map["website"] = registry_terminal
    elif "website" not in evidence_map:
        evidence_map["website"] = evidence(
            "website",
            "not_found",
            "bounded_final_website_discovery",
            BRREG_BULK_URL,
            note="No bounded company website candidate passed exact-entity verification.",
        )
    row["evidence"] = evidence_map
    if total["requests"] > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        raise RuntimeError(f"Final site discovery exceeded logical request ceiling: {total['requests']}")
    return row, total
