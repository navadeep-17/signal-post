from __future__ import annotations

import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

ENDPOINT = "https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter"
ACCEPT = "application/vnd.brreg.enhetsregisteret.oppdatering.enhet.v1+json"
USER_AGENT = "signal-post/0.1 (+https://github.com/navadeep-17/signal-post)"
BATCH_SIZE = 100
MAX_RESPONSE_BYTES = 25_000_000
DEFAULT_LOOKBACK_DAYS = 365
DEFAULT_MAX_EVENTS_PER_COMPANY = 3
MANAGED_FIELD = "official_registry_change"

# Only paths with a stable, decision-useful interpretation are promoted. Unknown paths remain
# in the official source response but are not turned into evaluator-facing facts.
EXACT_PATH_LABELS = {
    "/sisteInnsendteAarsregnskap": "latest submitted annual accounts",
    "/antallAnsatte": "registered employee count",
    "/naeringskode1": "registered industry",
    "/vedtektsdato": "articles date",
    "/registrertIMvaregisteret": "VAT registration status",
    "/registreringsdatoMerverdiavgiftsregisteret": "VAT registration date",
    "/registreringsdatoFrivilligMerverdiavgiftsregisteret": "voluntary VAT registration date",
    "/kapital/antallAksjer": "registered share count",
    "/kapital/innfortDato": "registered capital effective date",
}
PREFIX_PATH_LABELS = {
    "/forretningsadresse/": "registered business address",
    "/postadresse/": "registered postal address",
    "/kapital/": "registered capital",
}


def _normalise_org(value: Any) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) != 9:
        raise ValueError(f"Invalid Norwegian organisation number: {value!r}")
    return digits


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def theoretical_change_feed_requests(company_count: int, *, batch_size: int = BATCH_SIZE) -> int:
    if company_count < 0:
        raise ValueError("company_count cannot be negative")
    if batch_size < 1 or batch_size > BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {BATCH_SIZE}")
    return math.ceil(company_count / batch_size) if company_count else 0


def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def build_change_feed_url(organisation_numbers: Iterable[Any], *, size: int = 10_000) -> str:
    orgs = [_normalise_org(value) for value in organisation_numbers]
    if not orgs:
        raise ValueError("organisation_numbers cannot be empty")
    if len(orgs) != len(set(orgs)):
        raise ValueError("organisation_numbers contains duplicates")
    if size < 1 or size > 10_000:
        raise ValueError("size must be between 1 and 10000")
    query = urllib.parse.urlencode(
        {
            "organisasjonsnummer": ",".join(orgs),
            "includeChanges": "true",
            "size": str(size),
            "sort": "id,DESC",
        }
    )
    return f"{ENDPOINT}?{query}"


def target_source_url(organisation_number: Any) -> str:
    return build_change_feed_url([_normalise_org(organisation_number)])


def _path_label(path: Any) -> str | None:
    text = str(path or "").strip()
    if text in EXACT_PATH_LABELS:
        return EXACT_PATH_LABELS[text]
    for prefix, label in PREFIX_PATH_LABELS.items():
        if text.startswith(prefix):
            return label
    return None


def _json_value(value: Any) -> Any:
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    return str(value)


def _normalise_change(change: dict[str, Any]) -> dict[str, Any] | None:
    path = str(change.get("path") or "").strip()
    label = _path_label(path)
    operation = str(change.get("op") or "").strip().casefold()
    if not label or operation not in {"add", "replace", "remove"}:
        return None
    return {
        "path": path,
        "label": label,
        "operation": operation,
        "value": _json_value(change.get("value")) if operation != "remove" else None,
    }


def _render_value(value: Any) -> str:
    if isinstance(value, dict):
        description = str(value.get("beskrivelse") or value.get("description") or "").strip()
        code = str(value.get("kode") or value.get("code") or "").strip()
        if description and code:
            return f"{description} ({code})"
        return description or code or json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value[:4]) + (" …" if len(value) > 4 else "")
    if value is None:
        return "removed"
    return str(value)


def _summary(changes: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    seen_labels: set[str] = set()
    for change in changes:
        label = str(change.get("label") or "registry field")
        if label in seen_labels:
            continue
        seen_labels.add(label)
        operation = str(change.get("operation") or "updated")
        value = _render_value(change.get("value"))
        if operation == "remove":
            parts.append(f"{label} removed")
        elif operation == "add":
            parts.append(f"{label} added: {value}")
        else:
            parts.append(f"{label} updated: {value}")
    return "; ".join(parts[:5])


def _event_digest(event: dict[str, Any]) -> str:
    canonical = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def fetch_registry_change_events(
    organisation_numbers: Iterable[Any],
    *,
    timeout: float = 20.0,
    batch_size: int = BATCH_SIZE,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    max_events_per_company: int = DEFAULT_MAX_EVENTS_PER_COMPANY,
    as_of: str | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Fetch recent exact-org BRREG registry changes in bounded batches.

    The connector is supplementary and fail-soft on transport errors. It fails closed on
    attribution/schema integrity errors: an event for an unrequested organisation is never
    returned to the caller.
    """
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if batch_size < 1 or batch_size > BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {BATCH_SIZE}")
    if lookback_days < 1:
        raise ValueError("lookback_days must be positive")
    if max_events_per_company < 1 or max_events_per_company > 10:
        raise ValueError("max_events_per_company must be between 1 and 10")

    orgs = [_normalise_org(value) for value in organisation_numbers]
    if len(orgs) != len(set(orgs)):
        raise ValueError("organisation_numbers contains duplicates")

    now = _parse_datetime(as_of) or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback_days)
    grouped: dict[str, list[dict[str, Any]]] = {org: [] for org in orgs}
    metrics: dict[str, Any] = {
        "requests": 0,
        "bytes": 0,
        "latencies_ms": [],
        "batches": 0,
        "requested_organisations": len(orgs),
        "events_received": 0,
        "events_published": 0,
        "companies_with_published_events": 0,
        "errors": [],
        "integrity_errors": [],
        "response_sha256": [],
        "lookback_days": lookback_days,
        "max_events_per_company": max_events_per_company,
    }

    for chunk in _chunks(orgs, batch_size):
        requested = set(chunk)
        retrieval_url = build_change_feed_url(chunk)
        request = urllib.request.Request(
            retrieval_url,
            headers={"User-Agent": USER_AGENT, "Accept": ACCEPT},
        )
        metrics["requests"] += 1
        metrics["batches"] += 1
        started = time.monotonic()
        retrieved_at = _utc_now()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            elapsed = int((time.monotonic() - started) * 1000)
            metrics["latencies_ms"].append(elapsed)
            metrics["bytes"] += len(raw)
            if len(raw) > MAX_RESPONSE_BYTES:
                metrics["errors"].append("BRREG change-feed response exceeded byte limit")
                continue
            metrics["response_sha256"].append(hashlib.sha256(raw).hexdigest())
            payload = json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
            metrics["errors"].append(f"HTTP {exc.code}")
            continue
        except Exception as exc:
            metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
            metrics["errors"].append(f"{type(exc).__name__}: {str(exc)[:180]}")
            continue

        embedded = payload.get("_embedded") if isinstance(payload, dict) else None
        events = embedded.get("oppdaterteEnheter") if isinstance(embedded, dict) else None
        if not isinstance(events, list):
            metrics["integrity_errors"].append("BRREG change-feed payload lacks _embedded.oppdaterteEnheter[]")
            continue
        page = payload.get("page") if isinstance(payload, dict) else None
        if isinstance(page, dict):
            total_elements = int(page.get("totalElements") or len(events))
            if total_elements > len(events):
                metrics["errors"].append(
                    f"BRREG change-feed batch truncated ({len(events)}/{total_elements}); newest page retained"
                )

        metrics["events_received"] += len(events)
        for raw_event in events:
            if not isinstance(raw_event, dict):
                metrics["integrity_errors"].append("BRREG change-feed returned a non-object event")
                continue
            org = str(raw_event.get("organisasjonsnummer") or "").strip()
            if org not in requested:
                metrics["integrity_errors"].append(f"Unexpected organisation number in BRREG change feed: {org}")
                continue
            effective = _parse_datetime(raw_event.get("dato"))
            if effective is None or effective < cutoff or effective > now + timedelta(days=1):
                continue
            event_id = raw_event.get("oppdateringsid")
            if event_id is None:
                metrics["integrity_errors"].append(f"BRREG change event for {org} lacks oppdateringsid")
                continue
            raw_changes = raw_event.get("endringer")
            if not isinstance(raw_changes, list) or not raw_changes:
                continue
            changes = [item for item in (_normalise_change(change) for change in raw_changes if isinstance(change, dict)) if item]
            if not changes:
                continue
            event_for_hash = {
                "organisasjonsnummer": org,
                "oppdateringsid": event_id,
                "dato": raw_event.get("dato"),
                "endringstype": raw_event.get("endringstype"),
                "endringer": raw_changes,
            }
            summary = _summary(changes)
            if not summary:
                continue
            grouped[org].append(
                {
                    "organisation_number": org,
                    "event_id": str(event_id),
                    "event_type": str(raw_event.get("endringstype") or "Ukjent"),
                    "effective_at": effective.isoformat().replace("+00:00", "Z"),
                    "retrieved_at": retrieved_at,
                    "source_url": target_source_url(org),
                    "retrieval_url": retrieval_url,
                    "content_sha256": _event_digest(event_for_hash),
                    "changes": changes,
                    "summary": summary,
                }
            )

    for org in grouped:
        deduplicated: dict[str, dict[str, Any]] = {}
        for event in grouped[org]:
            deduplicated[str(event["event_id"])] = event
        grouped[org] = sorted(
            deduplicated.values(),
            key=lambda item: (str(item.get("effective_at") or ""), str(item.get("event_id") or "")),
            reverse=True,
        )[:max_events_per_company]

    metrics["events_published"] = sum(len(events) for events in grouped.values())
    metrics["companies_with_published_events"] = sum(bool(events) for events in grouped.values())
    return grouped, metrics


def _evidence_id(org: str, event: dict[str, Any]) -> str:
    material = "|".join(
        [
            org,
            "brreg-change",
            str(event.get("event_id") or ""),
            str(event.get("content_sha256") or ""),
        ]
    )
    return "ev-brreg-change-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def project_registry_change_claims(
    contract: dict[str, Any],
    events: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Project qualified BRREG events as explicit official-registry-change claims."""
    org = _normalise_org(contract.get("organisation_number"))
    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]

    removed_ids = {
        evidence_id
        for claim in claims
        if claim.get("field") == MANAGED_FIELD
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    claims = [claim for claim in claims if claim.get("field") != MANAGED_FIELD]
    still_referenced = {
        evidence_id
        for claim in claims
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    evidence_by_id = {
        str(item.get("id")): item
        for item in evidence
        if item.get("id") and item.get("id") not in (removed_ids - still_referenced)
    }

    normalized_events: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if _normalise_org(event.get("organisation_number")) != org:
            raise ValueError("BRREG change event organisation number mismatch")
        event_id = str(event.get("event_id") or "").strip()
        summary = str(event.get("summary") or "").strip()
        source_url = str(event.get("source_url") or "").strip()
        retrieved_at = str(event.get("retrieved_at") or "").strip()
        effective_at = str(event.get("effective_at") or "").strip()
        digest = str(event.get("content_sha256") or "").strip()
        changes = event.get("changes") or []
        if not event_id or not summary or not source_url or not retrieved_at or not effective_at:
            continue
        if len(digest) != 64 or not isinstance(changes, list) or not changes:
            continue
        normalized_events.append(event)

    normalized_events.sort(
        key=lambda item: (str(item.get("effective_at") or ""), str(item.get("event_id") or "")),
        reverse=True,
    )
    for event in normalized_events:
        evidence_id = _evidence_id(org, event)
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": event["source_url"],
            "source_class": "official",
            "retrieved_at": event["retrieved_at"],
            "effective_at": event["effective_at"],
            "content_sha256": event["content_sha256"],
            "source_row_key": str(event["event_id"]),
            "claim_span": str(event["summary"])[:1000],
            **({"retrieval_url": event.get("retrieval_url")} if event.get("retrieval_url") else {}),
        }
        value = {
            "event_id": str(event["event_id"]),
            "event_type": str(event.get("event_type") or "Ukjent"),
            "effective_at": event["effective_at"],
            "summary": event["summary"],
            "changes": list(event["changes"]),
        }
        claims.append(
            {
                "field": MANAGED_FIELD,
                "value": value,
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": [evidence_id],
                "signal_type": "official_registry_change",
                "claim_scope": (
                    "Dated exact-organisation-number BRREG Enhetsregister update. This is an official registry change, "
                    "not company-authored news, hiring activity, or a social post."
                ),
            }
        )

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
