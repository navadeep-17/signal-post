from __future__ import annotations

import gzip
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from typing import Any, Iterable

from .domain_discovery import (
    _page_contains_full_legal_name,
    _page_contains_org_number,
    _page_matches_registry_location,
)
from .evidence import evidence
from .final_site_discovery import (
    MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
    _add_metrics,
    _has_conflicting_explicit_org_number,
    _publishable,
    discover_final_website,
    fetch_bounded_homepage,
)
from .identity import apply_website_identity_gate
from .website import _registered_domain, normalize_homepage
from .zero_cost_registry_guard import apply_registry_risk_guard

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIDATA_BATCH_SIZE = 100
WIKIDATA_MAX_RESPONSE_BYTES = 1_000_000
WIKIDATA_USER_AGENT = "signal-post/0.1 (+https://github.com/navadeep-17/signal-post)"
CONTACT_SURFACE_TERMS = ("kontakt", "contact")


def _normalise_org(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 9:
        raise ValueError(f"Invalid Norwegian organisation number: {value!r}")
    return digits


def theoretical_wikidata_lookup_requests(company_count: int, *, batch_size: int = WIKIDATA_BATCH_SIZE) -> int:
    if company_count < 0:
        raise ValueError("company_count cannot be negative")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    return math.ceil(company_count / batch_size) if company_count else 0


def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _sparql_query(orgs: list[str]) -> str:
    values = " ".join(json.dumps(org) for org in orgs)
    return (
        "SELECT ?org ?item ?website WHERE { "
        f"VALUES ?org {{ {values} }} "
        "?item wdt:P2333 ?org . "
        "?item wdt:P856 ?website . "
        "}"
    )


def _decode_response(raw: bytes, encoding: str) -> bytes:
    value = str(encoding or "").casefold()
    if "gzip" in value:
        return gzip.decompress(raw)
    if "deflate" in value:
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw


def fetch_wikidata_website_candidates(
    organisation_numbers: Iterable[Any],
    *,
    timeout: float = 8.0,
    batch_size: int = WIKIDATA_BATCH_SIZE,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Resolve exact P2333 -> P856 candidates in bounded batches.

    Wikidata is candidate discovery only. We require exactly one Wikidata item and one
    normalized website URL for an organisation number; ambiguous mappings abstain. The
    returned URL must still be independently fetched and pass Signalpost identity gates.
    """
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if batch_size < 1 or batch_size > WIKIDATA_BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {WIKIDATA_BATCH_SIZE}")

    orgs = [_normalise_org(value) for value in organisation_numbers]
    if len(orgs) != len(set(orgs)):
        raise ValueError("organisation_numbers contains duplicates")

    collected: dict[str, dict[str, set[str]]] = {
        org: {"items": set(), "urls": set()} for org in orgs
    }
    metrics: dict[str, Any] = {
        "requests": 0,
        "bytes": 0,
        "latencies_ms": [],
        "errors": [],
        "batches": 0,
        "requested_organisations": len(orgs),
    }

    for chunk in _chunks(orgs, batch_size):
        query = _sparql_query(chunk)
        url = WIKIDATA_SPARQL_URL + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": WIKIDATA_USER_AGENT,
                "Accept": "application/sparql-results+json",
                "Accept-Encoding": "gzip,deflate",
            },
        )
        metrics["requests"] += 1
        metrics["batches"] += 1
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read(WIKIDATA_MAX_RESPONSE_BYTES + 1)
                headers = getattr(response, "headers", {})
                encoding = headers.get("content-encoding", "") if hasattr(headers, "get") else ""
            elapsed = int((time.monotonic() - started) * 1000)
            metrics["latencies_ms"].append(elapsed)
            metrics["bytes"] += len(raw)
            if len(raw) > WIKIDATA_MAX_RESPONSE_BYTES:
                metrics["errors"].append("Wikidata response exceeded byte limit")
                continue
            raw = _decode_response(raw, str(encoding))
            payload = json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            elapsed = int((time.monotonic() - started) * 1000)
            metrics["latencies_ms"].append(elapsed)
            metrics["errors"].append(f"HTTP {exc.code}")
            continue
        except Exception as exc:
            elapsed = int((time.monotonic() - started) * 1000)
            metrics["latencies_ms"].append(elapsed)
            metrics["errors"].append(f"{type(exc).__name__}: {str(exc)[:180]}")
            continue

        bindings = ((payload.get("results") or {}).get("bindings") or []) if isinstance(payload, dict) else []
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            org = str(((binding.get("org") or {}).get("value") or "")).strip()
            if org not in collected:
                continue
            item = str(((binding.get("item") or {}).get("value") or "")).strip()
            website = str(((binding.get("website") or {}).get("value") or "")).strip()
            normalized = normalize_homepage(website)
            if not item or not normalized:
                continue
            collected[org]["items"].add(item)
            collected[org]["urls"].add(normalized)

    candidates: dict[str, dict[str, Any]] = {}
    ambiguous = 0
    for org, values in collected.items():
        items = sorted(values["items"])
        urls = sorted(values["urls"])
        if len(items) == 1 and len(urls) == 1:
            candidates[org] = {
                "organisation_number": org,
                "wikidata_item": items[0],
                "url": urls[0],
                "source": "wikidata_exact_org_official_website_candidate",
                "properties": ["P2333", "P856"],
            }
        elif items or urls:
            ambiguous += 1

    metrics["candidate_count"] = len(candidates)
    metrics["ambiguous_count"] = ambiguous
    metrics["missing_count"] = len(orgs) - len(candidates) - ambiguous
    return candidates, metrics


def _quarantine(assessment: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **assessment,
        "status": "review",
        "score": min(float(assessment.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [*list(assessment.get("reasons") or []), reason],
        "method": "wikidata_candidate_independent_identity_v1",
    }


def qualify_wikidata_candidate_identity(
    profile: dict[str, Any],
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Require independent company-page proof; Wikidata itself is never identity proof."""
    if not assessment or not assessment.get("publishable") or website.get("status") != "available":
        return assessment

    if _has_conflicting_explicit_org_number(profile, website):
        return _quarantine(assessment, "independently fetched Wikidata candidate identifies a different organisation number")

    if _page_contains_org_number(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "reasons": [*list(assessment.get("reasons") or []), "independently fetched candidate contains exact target organisation number"],
            "method": "wikidata_candidate_independent_identity_v1",
        }

    if _page_contains_full_legal_name(profile, website) and _page_matches_registry_location(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": max(float(assessment.get("score") or 0.95), 0.98),
            "publishable": True,
            "reasons": [*list(assessment.get("reasons") or []), "independently fetched candidate has full legal name plus BRREG location corroboration"],
            "method": "wikidata_candidate_independent_identity_v1",
        }

    return _quarantine(
        assessment,
        "Wikidata candidate lacks independent exact organisation-number or legal-name-plus-BRREG-location proof",
    )


def _contact_surface_candidates(primary: dict[str, Any]) -> list[str]:
    """Return explicit same-domain contact links retained from the verified homepage."""
    value = primary.get("value") or {}
    base_url = str(value.get("final_url") or primary.get("source_url") or "")
    base_domain = _registered_domain(base_url)
    ranked: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for raw in value.get("identity_links") or []:
        url = str(raw or "").strip()
        if not url or url in seen or _registered_domain(url) != base_domain:
            continue
        path = urllib.parse.unquote(urllib.parse.urlparse(url).path).casefold()
        marker = next((index for index, term in enumerate(CONTACT_SURFACE_TERMS) if term in path), None)
        if marker is None:
            continue
        seen.add(url)
        ranked.append((marker, len(path), url))
    ranked.sort()
    return [url for _, _, url in ranked]


def _attach_idle_contact_surface(
    profile: dict[str, Any],
    primary: dict[str, Any],
    *,
    total: dict[str, Any],
    timeout: float,
) -> bool:
    """Use the final two site requests only when careers/news left them completely idle.

    The contact page is not identity discovery. It is a secondary enrichment page nominated
    by an already-verified exact homepage. Publication requires independent page-local exact
    organisation proof, or full legal name plus BRREG location, and rejects conflicting
    explicit organisation numbers. No existing careers/news request is displaced.
    """
    total.setdefault("contact_surface_attempted", False)
    total.setdefault("contact_surface_retained", False)
    if not _publishable(primary):
        return False
    if int(total.get("requests") or 0) + 2 > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        return False
    candidates = _contact_surface_candidates(primary)
    if not candidates:
        return False

    candidate_url = candidates[0]
    total["contact_surface_attempted"] = True
    total["contact_surface_candidate_url"] = candidate_url
    surface, ops = fetch_bounded_homepage(
        candidate_url,
        source_type="verified_company_contact_surface_candidate",
        timeout=timeout,
    )
    _add_metrics(total, ops)

    primary_value = primary.get("value") or {}
    surface_value = surface.get("value") or {}
    primary_domain = str(primary_value.get("registered_domain") or _registered_domain(str(primary_value.get("final_url") or primary.get("source_url") or "")))
    surface_domain = str(surface_value.get("registered_domain") or "")
    final_url = str(surface_value.get("final_url") or surface.get("source_url") or "")
    same_domain = bool(primary_domain and surface_domain == primary_domain)
    exact_candidate_url = final_url.rstrip("/") == candidate_url.rstrip("/")
    conflict = _has_conflicting_explicit_org_number(profile, surface)
    org_match = _page_contains_org_number(profile, surface)
    name_match = _page_contains_full_legal_name(profile, surface)
    location_match = _page_matches_registry_location(profile, surface)
    strong_identity = bool(org_match or (name_match and location_match))
    accepted = bool(
        surface.get("status") == "available"
        and same_domain
        and exact_candidate_url
        and not conflict
        and strong_identity
    )

    total["contact_surface_identity"] = {
        "same_registered_domain": same_domain,
        "exact_candidate_url": exact_candidate_url,
        "conflicting_explicit_org_number": conflict,
        "target_org_number_on_page": org_match,
        "full_legal_name_on_page": name_match,
        "registry_location_on_page": location_match,
        "publishable": accepted,
    }
    if not accepted:
        return False

    surface_value["contact_surface_identity"] = {
        "status": "exact",
        "publishable": True,
        "method": "verified_homepage_contact_surface_exact_page_v1",
        "target_org_number_on_page": org_match,
        "full_legal_name_on_page": name_match,
        "registry_location_on_page": location_match,
    }
    surface["value"] = surface_value
    profile.setdefault("evidence", {})["website_contact_surface"] = surface
    total["contact_surface_retained"] = True
    return True


def _maybe_attach_idle_contact_surface(
    row: dict[str, Any],
    total: dict[str, Any],
    *,
    timeout: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Attach contact enrichment only for an already-promoted site with two unused requests."""
    total.setdefault("contact_surface_attempted", False)
    total.setdefault("contact_surface_retained", False)
    if not total.get("promoted"):
        return row, total
    if total.get("careers_surface_attempted") or total.get("news_detail_attempted"):
        return row, total
    if int(total.get("requests") or 0) + 2 > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        return row, total
    primary = ((row.get("evidence") or {}).get("website") or {})
    _attach_idle_contact_surface(row, primary, total=total, timeout=timeout)
    return row, total


def discover_final_website_with_wikidata(
    profile: dict[str, Any],
    *,
    wikidata_candidate: dict[str, Any] | None,
    timeout: float = 6.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run existing discovery, then Wikidata fallback and idle exact-site contact enrichment."""
    row, total = discover_final_website(profile, timeout=timeout)
    total["wikidata_candidate_available"] = bool(wikidata_candidate)
    total["wikidata_attempted"] = False
    total["wikidata_verified"] = False

    if total.get("promoted"):
        return _maybe_attach_idle_contact_surface(row, total, timeout=timeout)
    if not wikidata_candidate:
        return row, total
    if int(total.get("requests") or 0) + 2 > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        total["wikidata_skipped_reason"] = "site_request_budget_consumed"
        return row, total

    candidate_url = str(wikidata_candidate.get("url") or "")
    if not candidate_url:
        total["wikidata_skipped_reason"] = "candidate_url_missing"
        return row, total

    total["wikidata_attempted"] = True
    record, ops = fetch_bounded_homepage(
        candidate_url,
        source_type="wikidata_official_website_candidate",
        timeout=timeout,
    )
    _add_metrics(total, ops)
    record["source_class"] = "open_knowledge_graph_candidate"
    gated = apply_website_identity_gate(row, record)
    candidate_record = gated["website"]
    assessment = qualify_wikidata_candidate_identity(
        row,
        candidate_record,
        gated.get("assessment"),
    )
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
    item_url = str(wikidata_candidate.get("wikidata_item") or WIKIDATA_SPARQL_URL)
    evidence_map["website_wikidata_discovery"] = evidence(
        "website_wikidata_discovery",
        "available" if selected else "not_found",
        "wikidata_exact_org_candidate_discovery",
        item_url,
        value={
            "organisation_number_property": "P2333",
            "official_website_property": "P856",
            "candidate_url": candidate_url,
            "independent_page_url": (candidate_record.get("value") or {}).get("final_url") if selected else None,
            "publishable": selected,
            "third_party_cost_usd": 0.0,
        },
        source_row_key=row.get("organisation_number"),
        note="Exact Wikidata P2333/P856 mapping nominates a candidate only; publication requires an independent company-page identity check.",
    )
    evidence_map["website_wikidata_candidate"] = candidate_record

    if selected:
        evidence_map["website"] = candidate_record
        row["website"] = (candidate_record.get("value") or {}).get("final_url") or candidate_record.get("source_url") or ""
        row, reasons = apply_registry_risk_guard(row)
        if _publishable((row.get("evidence") or {}).get("website") or {}):
            total["selected_source"] = "wikidata_candidate"
            total["promoted"] = True
            total["wikidata_verified"] = True
        else:
            total["wikidata_guard_reasons"] = reasons

    if int(total.get("requests") or 0) > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        raise RuntimeError(f"H1e final site discovery exceeded logical request ceiling: {total['requests']}")
    return _maybe_attach_idle_contact_surface(row, total, timeout=timeout)
