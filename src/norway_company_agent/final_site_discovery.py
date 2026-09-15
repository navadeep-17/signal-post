from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from copy import deepcopy
from typing import Any

from bs4 import BeautifulSoup
import extruct
import trafilatura

from .domain_discovery import (
    _page_contains_org_number,
    _page_matches_registry_location,
    qualify_registry_email_domain_identity,
    registry_email_domain_candidates,
)
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
SECONDARY_IDENTITY_TERMS = (
    "kontakt",
    "contact",
    "kontaktinformasjon",
    "personvern",
    "privacy",
    "privacy-policy",
    "om-oss",
    "om_oss",
    "about",
    "legal",
    "impressum",
    "vilkar",
    "terms",
    "company",
    "company-info",
    "firma",
    "selskapsinfo",
    "organisasjonsnummer",
    "orgnr",
    "org-nr",
)
IDENTITY_CONTAINER_TERMS = (
    "footer",
    "kontakt",
    "contact",
    "personvern",
    "privacy",
    "legal",
    "impressum",
    "company-info",
    "companyinfo",
    "selskapsinfo",
    "organisasjonsnummer",
    "orgnr",
    "org-nr",
    "address",
    "adresse",
)


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
    parsed = urllib.parse.urlparse(url)
    robots_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        request = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            parser.parse(response.read().decode("utf-8", errors="replace").splitlines())
        return parser.can_fetch(USER_AGENT, url), 1
    except Exception:
        return True, 1


def _identity_text_excerpt(soup: BeautifulSoup, limit: int = 5000) -> str:
    """Retain bounded legal/contact/footer text that precision extraction may omit.

    This is extraction only, not a weaker identity rule. The existing exact organisation-
    number / BRREG-location checks remain authoritative for H1c publication.
    """
    nodes: list[Any] = list(
        soup.select(
            'footer, address, [itemprop="address"], [itemprop="legalName"], '
            '[itemprop="taxID"], [itemprop="vatID"]'
        )
    )
    for node in soup.select("[id], [class]"):
        marker_parts = [str(node.get("id") or "")]
        classes = node.get("class") or []
        if isinstance(classes, str):
            marker_parts.append(classes)
        else:
            marker_parts.extend(str(value) for value in classes)
        marker = " ".join(marker_parts).casefold()
        if any(term in marker for term in IDENTITY_CONTAINER_TERMS):
            nodes.append(node)

    chunks: list[str] = []
    seen: set[str] = set()
    used = 0
    for node in nodes:
        text = " ".join(str(node.get_text(" ", strip=True) or "").split())
        if not text or text in seen:
            continue
        seen.add(text)
        remaining = limit - used
        if remaining <= 0:
            break
        chunk = text[:remaining]
        chunks.append(chunk)
        used += len(chunk) + 1
    return "\n".join(chunks)[:limit]


def _secondary_identity_links(base_url: str, soup: BeautifulSoup) -> list[str]:
    """Return deterministic same-domain identity/contact links, strongest first."""
    base_domain = _registered_domain(base_url)
    if not base_domain:
        return []
    ranked: list[tuple[int, str]] = []
    seen: set[str] = set()
    for node in soup.select("a[href]"):
        href = str(node.get("href") or "").strip()
        if not href:
            continue
        absolute = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(absolute)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        if _registered_domain(absolute) != base_domain:
            continue
        normalized = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))
        if normalized.rstrip("/") == base_url.rstrip("/") or normalized in seen:
            continue
        path_text = urllib.parse.unquote(parsed.path).casefold()
        anchor_text = node.get_text(" ", strip=True).casefold()
        haystack = f"{path_text} {anchor_text}"
        matched_index = next((index for index, term in enumerate(SECONDARY_IDENTITY_TERMS) if term in haystack), None)
        if matched_index is None:
            continue
        seen.add(normalized)
        ranked.append((matched_index, normalized))
    ranked.sort(key=lambda item: (item[0], len(urllib.parse.urlparse(item[1]).path), item[1]))
    return [url for _, url in ranked[:8]]


def fetch_bounded_homepage(
    url: str | None,
    *,
    source_type: str,
    timeout: float = 6.0,
    max_bytes: int = 750_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch robots + one HTML page, with at most one redirect per logical request."""
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
        identity_text = _identity_text_excerpt(soup)
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
            "identity_text_excerpt": identity_text,
            "main_text_excerpt": text[:5000],
            "social_links": _social_links(final_url, soup),
            "structured_organisations": _jsonld_organisations(structured),
            "content_sha256": digest,
            "extraction_state": _extraction_state(text, soup),
            "identity_links": _secondary_identity_links(final_url, soup),
            "pages": [{
                "url": final_url,
                "title": title[:500],
                "identity_text_excerpt": identity_text,
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
            note="Bounded single-page final evaluator evidence",
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


def _secondary_required(assessment: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **assessment,
        "status": "review",
        "score": min(float(assessment.get("score") or 0.88), 0.88),
        "publishable": False,
        "secondary_identity_required": True,
        "reasons": [*list(assessment.get("reasons") or []), reason],
        "method": "final_h1c_secondary_identity_guard_v1",
    }


def _secondary_verified(assessment: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **assessment,
        "status": "exact",
        "score": max(float(assessment.get("score") or 0.95), 0.98),
        "publishable": True,
        "secondary_identity_required": False,
        "reasons": [*list(assessment.get("reasons") or []), reason],
        "method": "final_h1c_secondary_identity_guard_v1",
    }


def _merge_secondary_page(primary: dict[str, Any], secondary: dict[str, Any]) -> bool:
    """Merge same-domain secondary identity evidence into the primary record."""
    if primary.get("status") != "available" or secondary.get("status") != "available":
        return False
    primary_value = primary.get("value") or {}
    secondary_value = secondary.get("value") or {}
    primary_domain = str(primary_value.get("registered_domain") or "")
    secondary_domain = str(secondary_value.get("registered_domain") or "")
    if not primary_domain or primary_domain != secondary_domain:
        return False
    pages = list(primary_value.get("pages") or [])
    secondary_pages = list(secondary_value.get("pages") or [])
    if secondary_pages:
        pages.append(secondary_pages[0])
    primary_value["pages"] = pages
    primary_value["secondary_identity_page"] = {
        "url": secondary_value.get("final_url") or secondary.get("source_url"),
        "content_sha256": secondary.get("content_sha256") or secondary_value.get("content_sha256"),
    }
    primary["value"] = primary_value
    return True


def discover_final_website(profile: dict[str, Any], *, timeout: float = 6.0) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve a canonical company website with a four-logical-request site ceiling.

    Order:
    1. registry website, when present; otherwise one registry-email-domain candidate;
    2. one deterministic legal-name .no candidate if still unresolved;
    3. for H1c title+domain-only matches, one same-domain identity page only when two
       logical requests remain. Without that budget, the weak candidate abstains.

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
        "h1c_secondary_attempted": False,
        "h1c_secondary_verified": False,
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

        initially_selected = bool(assessment and assessment.get("publishable") and candidate_record.get("status") == "available")
        homepage_strong = bool(
            initially_selected
            and (
                _page_contains_org_number(row, candidate_record)
                or _page_matches_registry_location(row, candidate_record)
            )
        )
        if initially_selected and not homepage_strong and assessment is not None:
            assessment = _secondary_required(
                assessment,
                "H1c title/domain match requires a same-domain identity page with organisation-number or registry-location corroboration",
            )
            value = candidate_record.get("value") or {}
            value["identity_assessment"] = assessment
            candidate_record["value"] = value
            links = list(value.get("identity_links") or [])
            if links and total["requests"] + 2 <= MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
                secondary_url = links[0]
                total["h1c_secondary_attempted"] = True
                secondary_record, secondary_ops = fetch_bounded_homepage(
                    secondary_url,
                    source_type="deterministic_legal_name_secondary_identity_page",
                    timeout=timeout,
                )
                _add_metrics(total, secondary_ops)
                evidence_map["website_h1c_secondary_identity"] = secondary_record
                merged = _merge_secondary_page(candidate_record, secondary_record)
                if merged and (
                    _page_contains_org_number(row, candidate_record)
                    or _page_matches_registry_location(row, candidate_record)
                ):
                    assessment = _secondary_verified(
                        assessment,
                        "same-domain secondary identity page corroborates the exact organisation number or BRREG location",
                    )
                    total["h1c_secondary_verified"] = True
                else:
                    assessment = _secondary_required(
                        assessment,
                        "same-domain secondary identity page did not corroborate the exact organisation number or BRREG location",
                    )
                value = candidate_record.get("value") or {}
                value["identity_assessment"] = assessment
                candidate_record["value"] = value
            elif not links:
                assessment = _secondary_required(
                    assessment,
                    "H1c homepage exposed no bounded same-domain identity page for corroboration",
                )
                value = candidate_record.get("value") or {}
                value["identity_assessment"] = assessment
                candidate_record["value"] = value
            else:
                assessment = _secondary_required(
                    assessment,
                    "H1c secondary corroboration skipped because the per-company site request budget was already consumed",
                )
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
                "secondary_identity_attempted": total["h1c_secondary_attempted"],
                "secondary_identity_verified": total["h1c_secondary_verified"],
                "third_party_cost_usd": 0.0,
            },
            note="One deterministic .no candidate independently fetched; weak title/domain matches require bounded secondary identity corroboration.",
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
