from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .external_footprint import validate_observation
from .official import BRREG_ACCOUNT_PDF

UA = "signal-post/0.1 (+https://github.com/navadeep-17/signal-post)"
MAX_PDF_BYTES = 20_000_000
OCR_NUMBER = r"(?-i:\b[0-9O][0-9O .,-]{0,8})"
PATTERNS = (
    (0, "full_time_equivalents", re.compile(rf"(?i)(?:antall|tal\s+p[aå])\s+(?:aarsverk|arsverk|årsverk)\s+i\s+(?:regnskapsaret|rekneskapsaret)\s*(?:er|:|=)?\s*({OCR_NUMBER})")),
    (0, "full_time_equivalents", re.compile(rf"(?i)antall\s+(?:aarsverk|arsverk|årsverk)(?:\s+sysselsatt\s+i\s+regnskapsaret)?\s*(?:er|:|=)?\s*({OCR_NUMBER})")),
    (0, "full_time_equivalents", re.compile(rf"(?i)selskapet\s+har(?:\s+[i1]\s+\d{{4}})?\s+sysselsatt\s+({OCR_NUMBER})\s+(?:aarsverk|arsverk|årsverk)")),
    (0, "full_time_equivalents", re.compile(rf"(?i)selskapet\s+har\s+({OCR_NUMBER})\s+(?:aarsverk|arsverk|årsverk)")),
    (0, "full_time_equivalents", re.compile(rf"(?i)antall\s+(?:aarsverk|arsverk|årsverk)\s+(?:sysselsatt|syssetsatt)\s+i\s+regnskapsaret\s*(?:er|:|=)?\s*({OCR_NUMBER})")),
    (1, "employees", re.compile(rf"(?i)gjennomsnittlig(?:e)?\s+antall\s+ansatte(?:\s+i\s+regnskapsaret)?\s*(?:er|:|=)?\s*({OCR_NUMBER})")),
    (1, "employees", re.compile(rf"(?i)antall\s+ansatte\s*(?:er|:|=)?\s*({OCR_NUMBER})")),
    (2, "employees", re.compile(rf"(?i)({OCR_NUMBER})\s+(?:heltids)?ansatte\b")),
)
WORD_COUNTS = {"ingen": 0, "en": 1, "ett": 1, "to": 2, "tre": 3, "fire": 4, "fem": 5}
WORD_EMPLOYEE_PATTERN = re.compile(r"(?i)\b(?:det\s+er|selskapet\s+har)\s+(ingen|en|ett|to|tre|fire|fem)\s+ansatte\b")
ZERO_WORKFORCE_PATTERN = re.compile(
    r"(?i)\b(?:selskapet|stiftelsen|legatet|sameiet|det)\s+"
    r"(?:har\s+ingen\s+(ansatte|(?:aarsverk|arsverk|årsverk))|"
    r"har\s+ikke\s+hatt\s+(?:noen\s+)?ansatte|"
    r"hadde\s+ingen\s+ansatte|"
    r"ikke\s+har\s+ansatte)\b"
)
WORKFORCE_TERMS = re.compile(r"(?i)ansatt|aarsverk|arsverk|årsverk|sysselsatt")


def registry_employee_count(profile: dict[str, Any]) -> int | None:
    live = ((profile.get("evidence") or {}).get("registry_live") or {}).get("value") or {}
    value = live.get("employees")
    if isinstance(value, bool):
        return None
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    return count if count >= 0 else None


def latest_account_year(profile: dict[str, Any]) -> str | None:
    live = ((profile.get("evidence") or {}).get("registry_live") or {}).get("value") or {}
    for value in (profile.get("latest_submitted_accounts"), live.get("latest_submitted_accounts")):
        text = str(value or "").strip()
        if len(text) == 4 and text.isdigit():
            return text
    return None


def existing_workforce_observation(profile: dict[str, Any]) -> bool:
    return any(
        isinstance(row, dict) and row.get("signal_type") == "workforce_snapshot"
        for row in (profile.get("external_observations") or [])
    )


def ocr_runtime_available() -> bool:
    return bool(shutil.which("pdftoppm") and shutil.which("tesseract"))


def needs_ocr(text: str) -> bool:
    return len(text.strip()) < 100 or not WORKFORCE_TERMS.search(text)


def number_value(value: str) -> int | float | None:
    cleaned = value.replace(" ", "").replace("O", "0").strip(".,-")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif re.search(r"\.\d{1,2}$", cleaned):
        pass
    else:
        cleaned = cleaned.replace(".", "")
    try:
        number = float(cleaned)
    except ValueError:
        return None
    if not 0 <= number <= 100_000:
        return None
    return int(number) if number.is_integer() else round(number, 2)


def extract_candidate(text: str) -> tuple[int | float | None, str | None, str, str | None]:
    compact = re.sub(r"[\t\r ]+", " ", text)
    matches: list[tuple[int, int | float, str, str]] = []
    for priority, measure, pattern in PATTERNS:
        for match in pattern.finditer(compact):
            start = max(0, compact.rfind("\n", 0, match.start()) + 1)
            end_pos = compact.find("\n", match.end())
            end = len(compact) if end_pos < 0 else end_pos
            span = compact[start:end].strip()[:500]
            if re.search(r"(?i)konsern|group", span):
                continue
            count = number_value(match.group(1))
            if count is not None:
                matches.append((priority, count, span, measure))
    for match in WORD_EMPLOYEE_PATTERN.finditer(compact):
        start = max(0, compact.rfind("\n", 0, match.start()) + 1)
        end_pos = compact.find("\n", match.end())
        end = len(compact) if end_pos < 0 else end_pos
        span = compact[start:end].strip()[:500]
        if not re.search(r"(?i)konsern|group", span):
            matches.append((2, WORD_COUNTS[match.group(1).casefold()], span, "employees"))
    for match in ZERO_WORKFORCE_PATTERN.finditer(compact):
        start = max(0, compact.rfind("\n", 0, match.start()) + 1)
        end_pos = compact.find("\n", match.end())
        end = len(compact) if end_pos < 0 else end_pos
        span = compact[start:end].strip()[:500]
        if not re.search(r"(?i)konsern|group", span):
            measure = "full_time_equivalents" if match.group(1) and re.search(r"(?i)verk", match.group(1)) else "employees"
            matches.append((0, 0, span, measure))
    if not matches:
        return None, None, "no_employee_phrase", None
    best_priority = min(item[0] for item in matches)
    best = [item for item in matches if item[0] == best_priority]
    values = {item[1] for item in best}
    if len(values) != 1:
        return None, None, "conflicting_employee_counts", None
    chosen = sorted(best, key=lambda item: item[3] != "full_time_equivalents")[0]
    return chosen[1], chosen[2], "accepted", chosen[3]


def _ocr_pdf(raw: bytes, *, pages: int, dpi: int) -> str:
    if pages <= 0:
        return ""
    with tempfile.TemporaryDirectory(prefix="signalpost-annual-workforce-") as temporary:
        root = Path(temporary)
        pdf_path = root / "report.pdf"
        prefix = root / "page"
        pdf_path.write_bytes(raw)
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", str(pages), "-jpeg", "-r", str(dpi), str(pdf_path), str(prefix)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=180,
        )
        env = os.environ.copy()
        env["OMP_THREAD_LIMIT"] = "1"
        chunks: list[str] = []
        for image_path in sorted(root.glob("page-*.jpg")):
            completed = subprocess.run(
                ["tesseract", str(image_path), "stdout", "-l", "eng", "--psm", "6"],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )
            chunks.append(completed.stdout)
        return "\n".join(chunks)


def collect_annual_report_workforce(
    profile: dict[str, Any],
    *,
    timeout: float = 60.0,
    ocr_pages: int = 8,
    ocr_dpi: int = 110,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    org = str(profile.get("organisation_number") or "")
    year = latest_account_year(profile)
    if existing_workforce_observation(profile) or registry_employee_count(profile) is not None:
        return None, {"organisation_number": org, "status": "workforce_already_available", "request_count": 0}
    if not year:
        return None, {"organisation_number": org, "status": "no_latest_account_year", "request_count": 0}

    url = BRREG_ACCOUNT_PDF.format(org=org, year=year)
    result: dict[str, Any] = {
        "organisation_number": org,
        "name": profile.get("name"),
        "year": year,
        "url": url,
        "request_count": 1,
    }
    started = time.monotonic()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/octet-stream"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_PDF_BYTES + 1)
            content_type = str(response.headers.get("content-type") or "")
        request_latency_ms = int((time.monotonic() - started) * 1000)
        if len(raw) > MAX_PDF_BYTES or not raw.startswith(b"%PDF"):
            return None, {
                **result,
                "status": "unsupported_pdf",
                "bytes": len(raw),
                "content_type": content_type,
                "request_latency_ms": request_latency_ms,
            }

        reader = PdfReader(io.BytesIO(raw), strict=False)
        digital_text = "\n".join((page.extract_text() or "") for page in reader.pages[:120])
        ocr_used = needs_ocr(digital_text) and ocr_pages > 0
        ocr_text = ""
        if ocr_used:
            ocr_text = _ocr_pdf(raw, pages=min(ocr_pages, len(reader.pages)), dpi=ocr_dpi)
        text = digital_text + ("\n" + ocr_text if ocr_text else "")

        digits = re.sub(r"\D", "", text)
        org_in_text = org in digits
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
            return None, {**result, **diagnostics, "status": "organisation_number_not_in_ocr_text"}

        count, span, status, measure = extract_candidate(text)
        if count is None:
            return None, {**result, **diagnostics, "status": status}

        digest = hashlib.sha256(raw).hexdigest()
        metrics = {
            "workforce_value": count,
            "measure": measure,
            str(measure): count,
            "year": year,
            "scope": "company_phrase",
            "claim_scope": "Official latest-year BRREG annual-account company-scope workforce phrase; not a group total or inferred trend.",
        }
        observation = {
            "id": "annual-workforce-" + hashlib.sha256(f"{org}|{year}|{count}|{digest}".encode()).hexdigest()[:24],
            "organisation_number": org,
            "platform": "brreg",
            "signal_type": "workforce_snapshot",
            "source_url": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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
            return None, {**result, **diagnostics, "status": "validation_error", "validation_errors": errors}
        return observation, {
            **result,
            **diagnostics,
            "status": "accepted",
            "workforce_value": count,
            "measure": measure,
            "evidence_span": span,
        }
    except urllib.error.HTTPError as exc:
        return None, {
            **result,
            "status": f"http_{exc.code}",
            "error": f"HTTPError: {exc}",
            "request_latency_ms": int((time.monotonic() - started) * 1000),
        }
    except Exception as exc:
        return None, {
            **result,
            "status": "error",
            "error": f"{type(exc).__name__}: {str(exc)[:180]}",
            "request_latency_ms": int((time.monotonic() - started) * 1000),
        }


def attach_annual_report_workforce_batch(
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
            "added_conservative_challenge_request_charge": 0,
            "status_counts": {"ocr_runtime_unavailable": len(selected)} if not runtime_available and selected else {},
            "runtime_seconds": 0.0,
            "execution_errors": [],
            "audit": [],
        }

    started = time.monotonic()
    results: dict[int, tuple[dict[str, Any] | None, dict[str, Any]]] = {}
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
                    collect_annual_report_workforce,
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
                            None,
                            {
                                "organisation_number": str(profile.get("organisation_number") or ""),
                                "status": "worker_error",
                                "error": f"{type(exc).__name__}: {str(exc)[:180]}",
                                "request_count": 0,
                            },
                        )

    ordered = [results[index] for index in range(len(selected))]
    audit = [result for _, result in ordered]
    accepted = 0
    for index, (observation, result) in enumerate(ordered):
        profile = selected[index]
        requests = int(result.get("request_count") or 0)
        metrics = profile.setdefault("run_metrics", {})
        metrics["logical_requests"] = int(metrics.get("logical_requests") or 0) + requests
        metrics["requests"] = int(metrics.get("requests") or 0) + requests * request_charge_multiplier
        metrics["bytes"] = int(metrics.get("bytes") or 0) + int(result.get("bytes") or 0)
        if result.get("request_latency_ms") is not None:
            metrics.setdefault("latencies_ms", []).append(int(result["request_latency_ms"]))
        if observation:
            rows = profile.setdefault("external_observations", [])
            if not any(isinstance(row, dict) and row.get("id") == observation.get("id") for row in rows):
                rows.append(observation)
            accepted += 1

    statuses = Counter(str(row.get("status") or "unknown") for row in audit)
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
        "accepted": accepted,
        "added_conservative_challenge_request_charge": requests * request_charge_multiplier,
        "status_counts": dict(statuses),
        "runtime_seconds": round(time.monotonic() - started, 3),
        "execution_errors": execution_errors,
        "audit": audit,
    }
