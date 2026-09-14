from __future__ import annotations

import hashlib
import re
import time
import urllib.error
import urllib.request
from typing import Any

from bs4 import BeautifulSoup
import extruct
import trafilatura

from .domain_discovery import (
    _domain_identity_strength,
    _page_contains_full_legal_name,
    _page_contains_org_number,
    _page_matches_registry_location,
    distinctive_legal_name_tokens,
)
from .evidence import evidence
from .website import (
    SAFE_OPENER,
    USER_AGENT,
    _extraction_state,
    _jsonld_organisations,
    _registered_domain,
    _robots_allowed,
    _social_links,
    assert_public_url,
    normalize_homepage,
)


def _verified_website_present(profile: dict[str, Any]) -> bool:
    website = (profile.get("evidence") or {}).get("website") or {}
    identity = (website.get("value") or {}).get("identity_assessment") or {}
    return website.get("status") == "available" and bool(identity.get("publishable"))


def deterministic_domain_candidates(profile: dict[str, Any], *, max_candidates: int = 2) -> dict[str, Any]:
    """Generate a tiny deterministic .no candidate set from the legal name."""
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    if _verified_website_present(profile):
        return {"eligible": False, "reason": "verified_website_present", "candidates": []}

    tokens = distinctive_legal_name_tokens(profile.get("name"))
    if not tokens:
        return {"eligible": False, "reason": "legal_name_has_no_distinctive_tokens", "candidates": []}

    labels = ["".join(tokens), "-".join(tokens)]
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for strategy, label in zip(("legal_name_compact", "legal_name_hyphenated"), labels):
        label = label.strip("-")
        if not (3 <= len(label) <= 63) or label in seen:
            continue
        if not all(ch.isalnum() or ch == "-" for ch in label) or label[0] == "-" or label[-1] == "-":
            continue
        seen.add(label)
        domain = f"{label}.no"
        candidates.append({
            "domain": domain,
            "url": f"https://{domain}/",
            "source": "deterministic_legal_name_domain_guess",
            "strategy": strategy,
        })
        if len(candidates) >= max_candidates:
            break

    return {
        "eligible": bool(candidates),
        "reason": "deterministic_legal_name_candidates" if candidates else "no_safe_candidate_labels",
        "candidates": candidates,
    }


def fetch_candidate_homepage(
    url: str,
    *,
    timeout: float = 6.0,
    max_bytes: int = 750_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch only the candidate homepage using the starter's SSRF/robots protections."""
    normalized = normalize_homepage(url)
    empty_ops = {"requests": 0, "bytes": 0, "latencies_ms": []}
    if not normalized:
        return evidence("website", "not_found", "deterministic_legal_name_domain_guess", str(url), note="Invalid candidate URL"), empty_ops
    try:
        assert_public_url(normalized)
    except ValueError as exc:
        return evidence("website", "not_found", "deterministic_legal_name_domain_guess", normalized, note=str(exc)), empty_ops

    if not _robots_allowed(normalized, timeout):
        return evidence("website", "blocked", "deterministic_legal_name_domain_guess", normalized, note="robots.txt disallows this user agent"), {"requests": 1, "bytes": 0, "latencies_ms": []}

    started = time.monotonic()
    request = urllib.request.Request(normalized, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    try:
        with SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            elapsed = int((time.monotonic() - started) * 1000)
            final_url = response.geturl()
            assert_public_url(final_url)
            content_type = response.headers.get("content-type", "")
        if len(raw) > max_bytes:
            return evidence("website", "blocked", "deterministic_legal_name_domain_guess", normalized, note="Candidate homepage exceeds byte limit"), {"requests": 2, "bytes": len(raw), "latencies_ms": [elapsed]}
        if "html" not in content_type.casefold():
            return evidence("website", "source_error", "deterministic_legal_name_domain_guess", normalized, note=f"Unsupported content type: {content_type}"), {"requests": 2, "bytes": len(raw), "latencies_ms": [elapsed]}

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
            "deterministic_legal_name_domain_guess",
            final_url,
            value=value,
            note="Zero-cost discovery candidate; publication still requires exact page identity",
            content_sha256=digest,
        ), {"requests": 2, "bytes": len(raw), "latencies_ms": [elapsed]}
    except urllib.error.HTTPError as exc:
        elapsed = int((time.monotonic() - started) * 1000)
        status = "not_found" if exc.code in {404, 410} else "source_error"
        return evidence("website", status, "deterministic_legal_name_domain_guess", normalized, note=f"HTTP {exc.code}"), {"requests": 2, "bytes": 0, "latencies_ms": [elapsed]}
    except Exception as exc:
        elapsed = int((time.monotonic() - started) * 1000)
        return evidence("website", "source_error", "deterministic_legal_name_domain_guess", normalized, note=f"{type(exc).__name__}: {str(exc)[:180]}"), {"requests": 2, "bytes": 0, "latencies_ms": [elapsed]}


def _normalised_tokens(value: Any) -> set[str]:
    text = str(value or "").translate(str.maketrans({"ø": "o", "Ø": "O", "å": "a", "Å": "A", "æ": "ae", "Æ": "AE"})).casefold()
    return set(re.findall(r"[a-z0-9]+", text))


def _title_contains_full_legal_name(profile: dict[str, Any], website: dict[str, Any]) -> bool:
    legal = set(distinctive_legal_name_tokens(profile.get("name")))
    title = (website.get("value") or {}).get("title") or ""
    return bool(legal and legal.issubset(_normalised_tokens(title)))


def qualify_deterministic_domain_identity(
    profile: dict[str, Any],
    candidate_domain: str,
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Require independent page proof before a guessed domain can be published."""
    if not assessment or not assessment.get("publishable") or website.get("status") != "available":
        return assessment

    if _page_contains_org_number(profile, website):
        return {
            **assessment,
            "score": 1.0,
            "reasons": [*list(assessment.get("reasons") or []), "H1c independently fetched page contains exact organisation number"],
            "method": "deterministic_domain_page_identity_guard_v2",
        }

    if not _page_contains_full_legal_name(profile, website):
        return {
            **assessment,
            "status": "review",
            "score": min(float(assessment.get("score") or 0.85), 0.85),
            "publishable": False,
            "reasons": [*list(assessment.get("reasons") or []), "H1c page lacks complete legal name"],
            "method": "deterministic_domain_page_identity_guard_v2",
        }

    final_url = (website.get("value") or {}).get("final_url") or website.get("source_url") or ""
    final_domain = str(final_url).split("//", 1)[-1].split("/", 1)[0].split(":", 1)[0]
    final_strength = _domain_identity_strength(profile, final_domain)
    location_match = _page_matches_registry_location(profile, website)
    title_match = _title_contains_full_legal_name(profile, website)
    if location_match or (title_match and final_strength in {"exact", "multi"}):
        return {
            **assessment,
            "score": min(0.99, max(float(assessment.get("score") or 0.95), 0.95)),
            "reasons": [*list(assessment.get("reasons") or []), "H1c full legal name has registry-location or title-plus-final-domain corroboration"],
            "method": "deterministic_domain_page_identity_guard_v2",
        }

    return {
        **assessment,
        "status": "review",
        "score": min(float(assessment.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [*list(assessment.get("reasons") or []), "H1c legal-name mention lacks registry-location or title-plus-final-domain corroboration"],
        "method": "deterministic_domain_page_identity_guard_v2",
    }
