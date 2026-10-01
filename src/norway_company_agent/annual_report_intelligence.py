from __future__ import annotations

import hashlib
import io
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from typing import Any

from pypdf import PdfReader

from .annual_report_description import build_annual_report_description_observation
from .annual_report_workforce import (
    MAX_PDF_BYTES,
    UA,
    _ocr_pdf,
    existing_workforce_observation,
    extract_candidate,
    latest_account_year,
    needs_ocr,
    ocr_runtime_available,
    registry_employee_count,
)
from .external_footprint import validate_observation
from .official import BRREG_ACCOUNT_PDF


def _build_workforce_observation(
    *,
    org: str,
    year: str,
    url: str,
    digest: str,
    retrieved_at: str,
    text: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    count, span, status, measure = extract_candidate(text)
    if count is None:
        return None, {"status": status}

    metrics = {
        "workforce_value": count,
        "measure": measure,
        str(measure): count,
        "year": year,
        "scope": "company_phrase",
        "claim_scope": (
            "Official latest-year BRREG annual-account company-scope workforce phrase; "
            "not a group total or inferred trend."
        ),
    }
    observation = {
        "id": "annual-workforce-" + hashlib.sha256(
            f"{org}|{year}|{count}|{digest}".encode("utf-8")
        ).hexdigest()[:24],
        "organisation_number": org,
        "platform": "brreg",
        "signal_type": "workforce_snapshot",
        "source_url": url,
        "retrieved_at": retrieved_at,
        "content_sha256": digest,
        "exact_entity": True,
        "identity_proof": [
            {"type": "official_brreg_annual_account_endpoint_organisation_number", "value": org},
            {"type": "organisation_number_in_ocr_text", "value": org},
            {"type": "registry_latest_submitted_accounts_year", "value": year},
        ],
        "acquisition_mode": "official_api",
        "rights_status": "approved",
        "source_class": "official_annual_account_copy",
        "evidence_span": span,
        "effective_at": year,
        "metrics": metrics,
        "strategy": "annual_report_workforce_snapshot_brreg_ocr_exact_org_v5",
    }
    errors = validate_observation(observation)
    if errors:
        return None, {"status": "validation_error", "validation_errors": errors}
    return observation, {
        "status": "accepted",
        "workforce_value": count,
        "measure": measure,
        "evidence_span": span,
    }


def collect_annual_report_intelligence(
    profile: dict[str, Any],
    *,
    timeout: float = 60.0,
    ocr_pages: int = 8,
    ocr_dpi: int = 110,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch one BRREG annual report and derive multiple exact-entity observations.

    V3 deliberately keeps the same network eligibility as H2g: this collector runs only
    for companies for which the production pipeline would already spend the annual-report
    request to recover workforce. Business-description extraction therefore reuses the
    same PDF bytes and OCR text instead of creating a second outbound request.
    """

    org = str(profile.get("organisation_number") or "")
    year = latest_account_year(profile)
    if existing_workforce_observation(profile) or registry_employee_count(profile) is not None:
        return [], {
            "organisation_number": org,
            "status": "workforce_already_available",
            "request_count": 0,
            "workforce_status": "not_attempted",
            "description_status": "not_attempted",
        }
    if not year:
        return [], {
            "organisation_number": org,
            "status": "no_latest_account_year",
            "request_count": 0,
            "workforce_status": "not_attempted",
            "description_status": "not_attempted",
        }

    url = BRREG_ACCOUNT_PDF.format(org=org, year=year)
    base: dict[str, Any] = {
        "organisation_number": org,
        "name": profile.get("name"),
        "year": year,
        "url": url,
        "request_count": 1,
    }
    started = time.monotonic()
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": UA, "Accept": "application/octet-stream"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_PDF_BYTES + 1)
            content_type = str(response.headers.get("content-type") or "")
        request_latency_ms = int((time.monotonic() - started) * 1000)
        if len(raw) > MAX_PDF_BYTES or not raw.startswith(b"%PDF"):
            return [], {
                **base,
                "status": "unsupported_pdf",
                "bytes": len(raw),
                "content_type": content_type,
                "request_latency_ms": request_latency_ms,
                "workforce_status": "not_attempted",
                "description_status": "not_attempted",
            }

        reader = PdfReader(io.BytesIO(raw), strict=False)
        digital_text = "\n".join((page.extract_text() or "") for page in reader.pages[:120])
        ocr_used = needs_ocr(digital_text) and ocr_pages > 0
        ocr_text = ""
        if ocr_used:
            ocr_text = _ocr_pdf(raw, pages=min(ocr_pages, len(reader.pages)), dpi=ocr_dpi)
        text = digital_text + ("\n" + ocr_text if ocr_text else "")

        org_in_text = org in re.sub(r"\D", "", text)
        diagnostics = {
            "pages": len(reader.pages),
            "bytes": len(raw),
            "content_type": content_type,
            "request_latency_ms": request_latency_ms,
            "digital_text_characters": len(digital_text.strip()),
            "ocr_used": ocr_used,
            "ocr_pages": min(ocr_pages, len(reader.pages)) if ocr_used else 0,
            "ocr_characters": len(ocr_text.strip()),
            "organisation_number_in_combined_text": org_in_text,
        }
        if not org_in_text:
            return [], {
                **base,
                **diagnostics,
                "status": "organisation_number_not_in_ocr_text",
                "workforce_status": "not_attempted",
                "description_status": "not_attempted",
            }

        digest = hashlib.sha256(raw).hexdigest()
        retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        workforce_observation, workforce_audit = _build_workforce_observation(
            org=org,
            year=year,
            url=url,
            digest=digest,
            retrieved_at=retrieved_at,
            text=text,
        )
        description_observation, description_audit = build_annual_report_description_observation(
            profile,
            text=text,
            source_url=url,
            content_sha256=digest,
            retrieved_at=retrieved_at,
            effective_at=year,
        )

        observations = [
            row
            for row in (workforce_observation, description_observation)
            if row is not None
        ]
        status = "accepted" if observations else "no_publishable_observation"
        return observations, {
            **base,
            **diagnostics,
            "status": status,
            "workforce_status": workforce_audit.get("status"),
            "description_status": description_audit.get("status"),
            "workforce_value": workforce_audit.get("workforce_value"),
            "workforce_measure": workforce_audit.get("measure"),
            "description_characters": len(
                str(description_audit.get("description") or "")
            ),
            "observations": len(observations),
        }
    except urllib.error.HTTPError as exc:
        return [], {
            **base,
            "status": f"http_{exc.code}",
            "error": f"HTTPError: {exc}",
            "request_latency_ms": int((time.monotonic() - started) * 1000),
            "workforce_status": "not_attempted",
            "description_status": "not_attempted",
        }
    except Exception as exc:
        return [], {
            **base,
            "status": "error",
            "error": f"{type(exc).__name__}: {str(exc)[:180]}",
            "request_latency_ms": int((time.monotonic() - started) * 1000),
            "workforce_status": "not_attempted",
            "description_status": "not_attempted",
        }


def attach_annual_report_intelligence_batch(
    profiles: list[dict[str, Any]],
    *,
    max_requests: int,
    workers: int = 4,
    min_start_interval: float = 2.1,
    timeout: float = 60.0,
    ocr_pages: int = 8,
    ocr_dpi: int = 110,
    request_charge_multiplier: int = 2,
) -> dict[str, Any]:
    """Batch V3 annual-report intelligence under the existing H2g request budget."""

    max_requests = max(0, int(max_requests))
    eligible = [
        profile
        for profile in profiles
        if not existing_workforce_observation(profile)
        and registry_employee_count(profile) is None
        and latest_account_year(profile)
    ]
    selected = eligible[:max_requests]
    runtime_available = ocr_runtime_available()
    if not runtime_available or not selected:
        return {
            "runtime_available": runtime_available,
            "eligible": len(eligible),
            "selected": 0 if not runtime_available else len(selected),
            "requests": 0,
            "accepted": 0,
            "descriptions_accepted": 0,
            "observations_accepted": 0,
            "added_conservative_challenge_request_charge": 0,
            "status_counts": {
                "ocr_runtime_unavailable": len(selected)
            } if not runtime_available and selected else {},
            "workforce_status_counts": {},
            "description_status_counts": {},
            "runtime_seconds": 0.0,
            "execution_errors": [],
            "audit": [],
        }

    started = time.monotonic()
    results: dict[int, tuple[list[dict[str, Any]], dict[str, Any]]] = {}
    active: dict[Any, int] = {}
    next_index = 0
    last_submit = 0.0
    worker_count = max(1, int(workers))

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        while next_index < len(selected) or active:
            while next_index < len(selected) and len(active) < worker_count:
                remaining = min_start_interval - (time.monotonic() - last_submit)
                if remaining > 0:
                    time.sleep(remaining)
                future = pool.submit(
                    collect_annual_report_intelligence,
                    selected[next_index],
                    timeout=timeout,
                    ocr_pages=ocr_pages,
                    ocr_dpi=ocr_dpi,
                )
                active[future] = next_index
                next_index += 1
                last_submit = time.monotonic()
            if active:
                done, _ = wait(tuple(active), return_when=FIRST_COMPLETED)
                for future in done:
                    index = active.pop(future)
                    try:
                        results[index] = future.result()
                    except Exception as exc:
                        profile = selected[index]
                        results[index] = (
                            [],
                            {
                                "organisation_number": str(
                                    profile.get("organisation_number") or ""
                                ),
                                "status": "worker_error",
                                "error": f"{type(exc).__name__}: {str(exc)[:180]}",
                                "request_count": 0,
                                "workforce_status": "not_attempted",
                                "description_status": "not_attempted",
                            },
                        )

    ordered = [results[index] for index in range(len(selected))]
    audit = [result for _, result in ordered]
    workforce_accepted = 0
    description_accepted = 0
    observations_accepted = 0

    for index, (observations, result) in enumerate(ordered):
        profile = selected[index]
        requests = int(result.get("request_count") or 0)
        metrics = profile.setdefault("run_metrics", {})
        metrics["logical_requests"] = int(metrics.get("logical_requests") or 0) + requests
        metrics["requests"] = int(metrics.get("requests") or 0) + requests * request_charge_multiplier
        metrics["bytes"] = int(metrics.get("bytes") or 0) + int(result.get("bytes") or 0)
        if result.get("request_latency_ms") is not None:
            metrics.setdefault("latencies_ms", []).append(int(result["request_latency_ms"]))

        rows = profile.setdefault("external_observations", [])
        known_ids = {
            str(row.get("id"))
            for row in rows
            if isinstance(row, dict) and row.get("id")
        }
        for observation in observations:
            observation_id = str(observation.get("id") or "")
            if observation_id and observation_id not in known_ids:
                rows.append(observation)
                known_ids.add(observation_id)
                observations_accepted += 1
            if observation.get("signal_type") == "workforce_snapshot":
                workforce_accepted += 1
            elif observation.get("signal_type") == "company_profile" and observation.get("company_description"):
                description_accepted += 1

    statuses = Counter(str(row.get("status") or "unknown") for row in audit)
    workforce_statuses = Counter(
        str(row.get("workforce_status") or "unknown") for row in audit
    )
    description_statuses = Counter(
        str(row.get("description_status") or "unknown") for row in audit
    )
    requests = sum(int(row.get("request_count") or 0) for row in audit)
    execution_errors = [
        {
            "organisation_number": row.get("organisation_number"),
            "status": row.get("status"),
            "error": row.get("error"),
        }
        for row in audit
        if row.get("status") in {"error", "worker_error"}
    ]
    return {
        "runtime_available": True,
        "eligible": len(eligible),
        "selected": len(selected),
        "requests": requests,
        # Compatibility: existing H2g callers interpret accepted as workforce accepted.
        "accepted": workforce_accepted,
        "descriptions_accepted": description_accepted,
        "observations_accepted": observations_accepted,
        "added_conservative_challenge_request_charge": requests * request_charge_multiplier,
        "status_counts": dict(statuses),
        "workforce_status_counts": dict(workforce_statuses),
        "description_status_counts": dict(description_statuses),
        "runtime_seconds": round(time.monotonic() - started, 3),
        "execution_errors": execution_errors,
        "audit": audit,
    }
