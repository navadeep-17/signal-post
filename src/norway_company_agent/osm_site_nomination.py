from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from copy import deepcopy
from typing import Any, Callable

import tldextract

from .domain_discovery import (
    _page_contains_full_legal_name,
    _page_contains_org_number,
    _page_matches_registry_location,
    distinctive_legal_name_tokens,
)
from .final_site_discovery import (
    _has_conflicting_explicit_org_number,
    _publishable,
    fetch_bounded_homepage,
)
from .identity import apply_website_identity_gate
from .zero_cost_registry_guard import apply_registry_risk_guard


DEFAULT_NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
DEFAULT_USER_AGENT = "Signalpost-Hackathon-Research/1.0 (https://github.com/navadeep-17/signal-post)"
OSM_ATTRIBUTION = "Data © OpenStreetMap contributors, ODbL 1.0"
LEGAL_SUFFIXES = {
    "as", "asa", "enk", "da", "ans", "sa", "ba", "nuf", "hf", "stiftelse",
}
BLOCKED_WEBSITE_DOMAINS = {
    "facebook.com", "instagram.com", "linkedin.com", "youtube.com",
    "twitter.com", "x.com", "google.com", "goo.gl",
}


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _registry_address(profile: dict[str, Any]) -> dict[str, Any]:
    for key in ("business_address", "postal_address"):
        value = profile.get(key)
        if isinstance(value, dict) and value:
            return value

    raw = ((profile.get("evidence") or {}).get("registry") or {}).get("value")
    if isinstance(raw, dict):
        for key in ("forretningsadresse", "postadresse"):
            value = raw.get(key)
            if isinstance(value, dict) and value:
                return value

        # The frozen BRREG bulk CSV stores address columns as flattened keys.
        for prefix in ("forretningsadresse", "postadresse"):
            street = (
                raw.get(f"{prefix}.adresse")
                or raw.get(f"{prefix}.adresse.0")
                or raw.get(f"{prefix}.adresselinje")
            )
            postcode = raw.get(f"{prefix}.postnummer")
            municipality = raw.get(f"{prefix}.kommune")
            if street or postcode or municipality:
                if isinstance(street, str):
                    streets = [street]
                elif isinstance(street, list):
                    streets = street
                else:
                    streets = []
                return {
                    "adresse": streets,
                    "postnummer": postcode,
                    "kommune": municipality,
                }

    municipality = str(profile.get("municipality") or "").strip()
    return {"kommune": municipality} if municipality else {}


def _address_query(profile: dict[str, Any]) -> str:
    address = _registry_address(profile)
    street = " ".join(str(x) for x in (address.get("adresse") or []) if str(x).strip())
    postcode = str(address.get("postnummer") or "").strip()
    municipality = str(address.get("kommune") or profile.get("municipality") or "").strip()
    parts = [str(profile.get("name") or "").strip(), street, postcode, municipality, "Norway"]
    return ", ".join(part for part in parts if part)


def _result_names(result: dict[str, Any]) -> list[str]:
    values: list[str] = []
    namedetails = result.get("namedetails")
    if isinstance(namedetails, dict):
        values.extend(str(v) for v in namedetails.values() if str(v).strip())
    display = str(result.get("display_name") or "").strip()
    if display:
        values.append(display.split(",", 1)[0])
    return values


def _name_match(profile: dict[str, Any], result: dict[str, Any]) -> tuple[bool, list[str]]:
    tokens = [
        token for token in distinctive_legal_name_tokens(profile.get("name"))
        if token not in LEGAL_SUFFIXES and len(token) >= 3
    ]
    if not tokens:
        return False, []
    names = [_fold(value) for value in _result_names(result)]
    matched: list[str] = []
    for token in tokens:
        folded = _fold(token)
        if folded and any(folded in name.split() or folded in name for name in names):
            matched.append(token)
    if len(tokens) == 1:
        return len(matched) == 1 and len(_fold(matched[0])) >= 5, matched
    required = max(2, len(tokens) - 1)
    return len(matched) >= required, matched


def _location_match(profile: dict[str, Any], result: dict[str, Any]) -> tuple[bool, str | None]:
    registry = _registry_address(profile)
    address = result.get("address") if isinstance(result.get("address"), dict) else {}

    registry_postcode = re.sub(r"\D", "", str(registry.get("postnummer") or ""))
    result_postcode = re.sub(r"\D", "", str(address.get("postcode") or ""))
    if registry_postcode and result_postcode and registry_postcode == result_postcode:
        return True, "postcode"

    registry_municipality = _fold(registry.get("kommune") or profile.get("municipality"))
    result_places = [
        _fold(address.get(key))
        for key in ("municipality", "city", "town", "village", "county")
        if address.get(key)
    ]
    if registry_municipality and any(
        registry_municipality == place
        or registry_municipality in place
        or place in registry_municipality
        for place in result_places
        if place
    ):
        return True, "municipality"
    return False, None


def _candidate_url(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if not re.match(r"(?i)^https?://", text):
        text = "https://" + text.lstrip("/")
    try:
        parsed = urllib.parse.urlparse(text)
    except ValueError:
        return None
    host = (parsed.hostname or "").casefold().rstrip(".")
    if not host:
        return None
    registered = str(tldextract.extract(host).top_domain_under_public_suffix or "").casefold()
    if not registered or registered in BLOCKED_WEBSITE_DOMAINS:
        return None
    return f"https://{registered}/"


def nominate_osm_website(
    profile: dict[str, Any],
    *,
    base_url: str = DEFAULT_NOMINATIM_BASE_URL,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: float = 12.0,
    sleeper: Callable[[float], None] = time.sleep,
    min_interval_seconds: float = 1.05,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Query Nominatim once and nominate a website only from name+location matched OSM objects."""

    query = _address_query(profile)
    params = urllib.parse.urlencode(
        {
            "q": query,
            "format": "jsonv2",
            "addressdetails": "1",
            "extratags": "1",
            "namedetails": "1",
            "countrycodes": "no",
            "limit": "3",
        }
    )
    url = base_url.rstrip("/") + "/search?" + params
    started = time.monotonic()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )
    audit: dict[str, Any] = {
        "organisation_number": str(profile.get("organisation_number") or ""),
        "query": query,
        "request_url": url,
        "requests": 1,
        "candidate_count": 0,
        "selected": False,
        "attribution": OSM_ATTRIBUTION,
        "policy": {
            "single_threaded": True,
            "minimum_request_interval_seconds": min_interval_seconds,
            "cache_required_for_repeated_queries": True,
            "provider_switchable": True,
        },
    }
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(2_000_000)
        body = json.loads(raw.decode("utf-8", errors="replace"))
        rows = body if isinstance(body, list) else []
    except Exception as exc:
        audit.update(
            {
                "status": "source_error",
                "error": f"{type(exc).__name__}: {str(exc)[:240]}",
                "latency_ms": int((time.monotonic() - started) * 1000),
            }
        )
        sleeper(min_interval_seconds)
        return None, audit

    audit["latency_ms"] = int((time.monotonic() - started) * 1000)
    reviewed: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    for result in rows[:3]:
        if not isinstance(result, dict):
            continue
        name_ok, matched_tokens = _name_match(profile, result)
        location_ok, location_basis = _location_match(profile, result)
        tags = result.get("extratags") if isinstance(result.get("extratags"), dict) else {}
        website = (
            tags.get("website")
            or tags.get("contact:website")
            or tags.get("url")
            or tags.get("contact:url")
        )
        candidate_url = _candidate_url(website)
        review = {
            "osm_type": result.get("osm_type"),
            "osm_id": result.get("osm_id"),
            "display_name": result.get("display_name"),
            "name_match": name_ok,
            "matched_name_tokens": matched_tokens,
            "location_match": location_ok,
            "location_basis": location_basis,
            "website_tag_present": bool(website),
            "candidate_url": candidate_url,
        }
        reviewed.append(review)
        if selected is None and name_ok and location_ok and candidate_url:
            selected = {
                "url": candidate_url,
                "strategy": "osm_nominatim_name_location_website_nomination",
                "osm_type": result.get("osm_type"),
                "osm_id": result.get("osm_id"),
                "display_name": result.get("display_name"),
                "matched_name_tokens": matched_tokens,
                "location_basis": location_basis,
                "attribution": OSM_ATTRIBUTION,
                "claim_scope": (
                    "OSM/Nominatim name+registry-location match nominates the website tag only. "
                    "The OSM record is not publication evidence for website ownership."
                ),
            }
    audit["candidate_count"] = sum(1 for row in reviewed if row.get("candidate_url"))
    audit["reviewed_results"] = reviewed
    audit["selected"] = selected is not None
    audit["status"] = "available"
    sleeper(min_interval_seconds)
    return selected, audit


def _quarantine(assessment: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **assessment,
        "status": "review",
        "score": min(float(assessment.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [*list(assessment.get("reasons") or []), reason],
        "method": "osm_nomination_exact_page_identity_v1",
    }


def qualify_osm_candidate_identity(
    profile: dict[str, Any],
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not assessment or not assessment.get("publishable") or website.get("status") != "available":
        return assessment
    if _has_conflicting_explicit_org_number(profile, website):
        return _quarantine(
            assessment,
            "OSM-nominated candidate independently identifies a different organisation number",
        )
    if _page_contains_org_number(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "independently fetched OSM-nominated page contains exact target organisation number",
            ],
            "method": "osm_nomination_exact_page_identity_v1",
        }
    if _page_contains_full_legal_name(profile, website) and _page_matches_registry_location(profile, website):
        return {
            **assessment,
            "status": "exact",
            "score": max(float(assessment.get("score") or 0.95), 0.98),
            "publishable": True,
            "reasons": [
                *list(assessment.get("reasons") or []),
                "independently fetched OSM-nominated page has full legal name plus BRREG location",
            ],
            "method": "osm_nomination_exact_page_identity_v1",
        }
    return _quarantine(
        assessment,
        "OSM nomination alone is insufficient; independent page lacks exact org-number or legal-name-plus-location proof",
    )


def evaluate_osm_candidate(
    profile: dict[str, Any],
    candidate: dict[str, Any] | None,
    *,
    timeout: float = 6.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    row = deepcopy(profile)
    result: dict[str, Any] = {
        "organisation_number": str(row.get("organisation_number") or ""),
        "attempted": False,
        "verified": False,
        "requests": 0,
        "bytes": 0,
        "latencies_ms": [],
        "selected_url": None,
        "guard_reasons": [],
    }
    if not candidate:
        result["skipped_reason"] = "no_osm_website_candidate"
        return row, result
    current = ((row.get("evidence") or {}).get("website") or {})
    if _publishable(current):
        result["skipped_reason"] = "verified_website_already_present"
        return row, result

    result["attempted"] = True
    record, operations = fetch_bounded_homepage(
        str(candidate.get("url") or ""),
        source_type="osm_nominatim_website_candidate",
        timeout=timeout,
    )
    result["requests"] = int(operations.get("requests") or 0)
    result["bytes"] = int(operations.get("bytes") or 0)
    result["latencies_ms"] = [
        int(v) for v in (operations.get("latencies_ms") or []) if v is not None
    ]
    record["source_class"] = "company_owned_candidate"
    gated = apply_website_identity_gate(row, record)
    candidate_record = gated["website"]
    assessment = qualify_osm_candidate_identity(row, candidate_record, gated.get("assessment"))
    if assessment is not None:
        value = candidate_record.get("value") or {}
        value["identity_assessment"] = assessment
        candidate_record["value"] = value

    if not (
        assessment
        and assessment.get("publishable")
        and candidate_record.get("status") == "available"
    ):
        return row, result

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
        return row, result

    row["evidence"]["website"] = guarded
    row["website"] = trial.get("website") or ""
    result["verified"] = True
    result["selected_url"] = row["website"]
    result["website_content_sha256"] = guarded.get("content_sha256")
    result["identity_assessment"] = (guarded.get("value") or {}).get("identity_assessment")
    return row, result
