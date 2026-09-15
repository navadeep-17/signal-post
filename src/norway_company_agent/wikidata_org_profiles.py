from __future__ import annotations

import gzip
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from typing import Any, Iterable

from .evidence import utc_now

"""Exact Norwegian organisation-number to Wikidata organisation-profile candidates."""

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIDATA_BATCH_SIZE = 100
WIKIDATA_MAX_RESPONSE_BYTES = 1_000_000
WIKIDATA_USER_AGENT = "signal-post/0.1 (+https://github.com/navadeep-17/signal-post)"
LINKEDIN_ORGANISATION_PROPERTY = "P4264"


def _normalise_org(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 9:
        raise ValueError(f"Invalid Norwegian organisation number: {value!r}")
    return digits


def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _sparql_query(orgs: list[str]) -> str:
    values = " ".join(json.dumps(org) for org in orgs)
    return (
        "SELECT ?org ?item ?linkedin WHERE { "
        f"VALUES ?org {{ {values} }} "
        "?item wdt:P2333 ?org . "
        "?item wdt:P4264 ?linkedin . "
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


def linkedin_company_url(identifier: str) -> str | None:
    value = str(identifier or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*[A-Za-z0-9]", value):
        return None
    encoded = urllib.parse.quote(value, safe="-")
    return f"https://www.linkedin.com/company/{encoded}/"


def fetch_wikidata_linkedin_candidates(
    organisation_numbers: Iterable[Any],
    *,
    timeout: float = 8.0,
    batch_size: int = WIKIDATA_BATCH_SIZE,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Collect exact P2333 -> P4264 organisation-profile candidates from WDQS.

    H2d is deliberately candidate-only at this stage. An organisation is emitted only when
    its Norwegian organisation number maps to exactly one Wikidata item and that item has
    exactly one safe truthy P4264 value. The LinkedIn page itself is not fetched here.
    """
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if batch_size < 1 or batch_size > WIKIDATA_BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {WIKIDATA_BATCH_SIZE}")

    orgs = [_normalise_org(value) for value in organisation_numbers]
    if len(orgs) != len(set(orgs)):
        raise ValueError("organisation_numbers contains duplicates")

    collected: dict[str, dict[str, Any]] = {
        org: {
            "items": set(),
            "identifiers": set(),
            "query_url": None,
            "response_sha256": None,
            "retrieved_at": None,
        }
        for org in orgs
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
            metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
            metrics["bytes"] += len(raw)
            if len(raw) > WIKIDATA_MAX_RESPONSE_BYTES:
                metrics["errors"].append("Wikidata LinkedIn response exceeded byte limit")
                continue
            response_sha256 = hashlib.sha256(raw).hexdigest()
            retrieved_at = utc_now()
            payload = json.loads(_decode_response(raw, str(encoding)).decode("utf-8"))
        except urllib.error.HTTPError as exc:
            metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
            metrics["errors"].append(f"HTTP {exc.code}")
            continue
        except Exception as exc:
            metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
            metrics["errors"].append(f"{type(exc).__name__}: {str(exc)[:180]}")
            continue

        for org in chunk:
            collected[org]["query_url"] = url
            collected[org]["response_sha256"] = response_sha256
            collected[org]["retrieved_at"] = retrieved_at

        bindings = ((payload.get("results") or {}).get("bindings") or []) if isinstance(payload, dict) else []
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            org = str(((binding.get("org") or {}).get("value") or "")).strip()
            if org not in collected:
                continue
            item = str(((binding.get("item") or {}).get("value") or "")).strip()
            identifier = str(((binding.get("linkedin") or {}).get("value") or "")).strip()
            if not item or not linkedin_company_url(identifier):
                continue
            collected[org]["items"].add(item)
            collected[org]["identifiers"].add(identifier)

    candidates: dict[str, dict[str, Any]] = {}
    ambiguous_items = 0
    ambiguous_identifiers = 0
    for org, values in collected.items():
        items = sorted(values["items"])
        identifiers = sorted(values["identifiers"])
        if len(items) > 1:
            ambiguous_items += 1
            continue
        if len(identifiers) > 1:
            ambiguous_identifiers += 1
            continue
        if len(items) != 1 or len(identifiers) != 1:
            continue
        identifier = identifiers[0]
        candidates[org] = {
            "organisation_number": org,
            "wikidata_item": items[0],
            "property_id": LINKEDIN_ORGANISATION_PROPERTY,
            "linkedin_identifier": identifier,
            "profile_url": linkedin_company_url(identifier),
            "source_url": values["query_url"],
            "content_sha256": values["response_sha256"],
            "retrieved_at": values["retrieved_at"],
            "source": "wikidata_exact_org_linkedin_organisation_candidate",
        }

    metrics.update(
        {
            "candidate_companies": len(candidates),
            "ambiguous_item_organisations": ambiguous_items,
            "ambiguous_linkedin_identifiers": ambiguous_identifiers,
            "missing_organisations": len(orgs) - len(candidates) - ambiguous_items - ambiguous_identifiers,
        }
    )
    return candidates, metrics


def candidate_observation(profile: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any] | None:
    """Build the prospective H2d claim for validation/audit without social-page access."""
    org = str(profile.get("organisation_number") or "")
    if str(candidate.get("organisation_number") or "") != org:
        return None
    profile_url = str(candidate.get("profile_url") or "")
    source_url = str(candidate.get("source_url") or "")
    digest = str(candidate.get("content_sha256") or "")
    retrieved_at = str(candidate.get("retrieved_at") or "")
    item = str(candidate.get("wikidata_item") or "")
    if not profile_url.startswith("https://www.linkedin.com/company/"):
        return None
    if not source_url.startswith("https://query.wikidata.org/") or len(digest) != 64 or not retrieved_at or not item:
        return None

    observation_id = "wikidata-linkedin-" + hashlib.sha256(
        f"{org}|{item}|{profile_url}".encode("utf-8")
    ).hexdigest()[:24]
    return {
        "id": observation_id,
        "organisation_number": org,
        "platform": "linkedin",
        "signal_type": "profile_handle",
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "content_sha256": digest,
        "exact_entity": True,
        "identity_proof": [
            {
                "type": "wikidata_exact_norwegian_org_number",
                "property": "P2333",
                "wikidata_item": item,
                "organisation_number": org,
                "unique_item": True,
            },
            {
                "type": "wikidata_linkedin_organisation_identifier",
                "property": LINKEDIN_ORGANISATION_PROPERTY,
                "profile_url": profile_url,
                "unique_value": True,
            },
        ],
        "acquisition_mode": "official_api",
        "rights_status": "approved",
        "source_class": "wikidata",
        "evidence_span": (
            f"Unique Wikidata item exact-matched by P2333 declares P4264 LinkedIn organisation profile {profile_url}"
        ),
        "profile_url": profile_url,
        "metrics": {
            "identity_score": 0.98,
            "claim_scope": (
                "LinkedIn company/organisation identifier declared on the unique Wikidata item exact-matched by "
                "Norwegian organisation number; the LinkedIn page itself was not fetched."
            ),
        },
        "strategy": "wikidata_exact_org_linkedin_candidate_v1",
    }
