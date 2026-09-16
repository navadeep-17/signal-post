#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from norway_company_agent.external_footprint import validate_observation  # noqa: E402
from norway_company_agent.official import BRREG_ACCOUNT_PDF  # noqa: E402
import run_annual_report_workforce_connector as workforce  # noqa: E402

UA = "signal-post/0.1 (+https://github.com/navadeep-17/signal-post)"
MAX_PDF_BYTES = 20_000_000


def registry_employee_count(profile: dict) -> int | None:
    live = ((profile.get("evidence") or {}).get("registry_live") or {}).get("value") or {}
    value = live.get("employees")
    if isinstance(value, bool):
        return None
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    return count if count >= 0 else None


def latest_account_year(profile: dict) -> str | None:
    live = ((profile.get("evidence") or {}).get("registry_live") or {}).get("value") or {}
    for value in (profile.get("latest_submitted_accounts"), live.get("latest_submitted_accounts")):
        text = str(value or "").strip()
        if len(text) == 4 and text.isdigit():
            return text
    return None


def _normalized_words(value: object) -> str:
    return " ".join(re.findall(r"[\wÆØÅæøå]+", str(value or "").casefold(), flags=re.UNICODE))


def collect(profile: dict, *, timeout: float) -> tuple[dict | None, dict]:
    org = str(profile.get("organisation_number") or "")
    year = latest_account_year(profile)
    if registry_employee_count(profile) is not None:
        return None, {"organisation_number": org, "status": "registry_count_already_available"}
    if not year:
        return None, {"organisation_number": org, "status": "no_latest_account_year"}

    url = BRREG_ACCOUNT_PDF.format(org=org, year=year)
    result = {"organisation_number": org, "name": profile.get("name"), "year": year, "url": url, "request_count": 1}
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                # BRREG's current annual-account OpenAPI contract advertises
                # application/octet-stream for this PDF-streaming response.
                "Accept": "application/octet-stream",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_PDF_BYTES + 1)
            content_type = str(response.headers.get("content-type") or "")
        if len(raw) > MAX_PDF_BYTES or not raw.startswith(b"%PDF"):
            return None, {**result, "status": "unsupported_pdf", "bytes": len(raw), "content_type": content_type}

        reader = PdfReader(io.BytesIO(raw), strict=False)
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:120])
        digits = re.sub(r"\D", "", text)
        org_in_pdf = org in digits
        normalized_name = _normalized_words(profile.get("name"))
        normalized_text = _normalized_words(text)
        name_in_pdf = bool(normalized_name and normalized_name in normalized_text)
        diagnostics = {
            "pages": len(reader.pages),
            "bytes": len(raw),
            "content_type": content_type,
            "text_characters": len(text.strip()),
            "organisation_number_in_extracted_text": org_in_pdf,
            "legal_name_in_extracted_text": name_in_pdf,
        }

        count, span, status, measure = workforce.extract_candidate(text)
        if count is None:
            return None, {
                **result,
                **diagnostics,
                "status": status,
                "needs_ocr": workforce.needs_ocr(text),
            }

        digest = hashlib.sha256(raw).hexdigest()
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
                {
                    "type": "official_brreg_annual_account_endpoint_organisation_number",
                    "value": org,
                },
                {
                    "type": "registry_latest_submitted_accounts_year",
                    "value": year,
                },
            ],
            "acquisition_mode": "official_api",
            "rights_status": "approved",
            "source_class": "official_annual_account_copy",
            "evidence_span": span,
            "effective_at": year,
            "metrics": {
                "workforce_value": count,
                "measure": measure,
                str(measure): count,
                "year": year,
                "scope": "company_phrase",
            },
            "strategy": "annual_report_workforce_snapshot_brreg_path_identity_v2",
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
        return None, {**result, "status": f"http_{exc.code}", "error": f"HTTPError: {exc}"}
    except Exception as exc:
        return None, {**result, "status": "error", "error": f"{type(exc).__name__}: {str(exc)[:180]}"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Corrected BRREG annual-report workforce yield screen.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--min-start-interval", type=float, default=2.1)
    args = parser.parse_args()

    profiles = [json.loads(line) for line in Path(args.profiles).read_text(encoding="utf-8").splitlines() if line.strip()]
    eligible = [profile for profile in profiles if registry_employee_count(profile) is None and latest_account_year(profile)]
    selected = eligible[: max(0, args.limit)]

    observations: list[dict] = []
    audit: list[dict] = []
    last_start = 0.0
    for profile in selected:
        remaining = args.min_start_interval - (time.monotonic() - last_start)
        if remaining > 0:
            time.sleep(remaining)
        last_start = time.monotonic()
        observation, result = collect(profile, timeout=args.timeout)
        audit.append(result)
        if observation:
            observations.append(observation)

    statuses = Counter(str(row.get("status") or "unknown") for row in audit)
    needs_ocr = sum(bool(row.get("needs_ocr")) for row in audit)
    total_bytes = sum(int(row.get("bytes") or 0) for row in audit)
    org_in_pdf = sum(bool(row.get("organisation_number_in_extracted_text")) for row in audit)
    name_in_pdf = sum(bool(row.get("legal_name_in_extracted_text")) for row in audit)
    report = {
        "experiment": "h2g_corrected_annual_report_workforce_screen_v2",
        "profiles": len(profiles),
        "eligible": len(eligible),
        "selected": len(selected),
        "requests": sum(int(row.get("request_count") or 0) for row in audit),
        "accepted": len(observations),
        "accepted_rate_over_selected": round(len(observations) / len(selected), 6) if selected else 0.0,
        "accepted_company_coverage_over_all_profiles": round(len(observations) / len(profiles), 6) if profiles else 0.0,
        "needs_ocr_without_digital_match": needs_ocr,
        "organisation_number_in_extracted_text": org_in_pdf,
        "legal_name_in_extracted_text": name_in_pdf,
        "status_counts": dict(statuses),
        "bytes": total_bytes,
        "third_party_cost_usd": 0.0,
        "observation_validation_errors": [
            {"id": row.get("id"), "errors": validate_observation(row)}
            for row in observations if validate_observation(row)
        ],
        "claim_boundary": (
            "Latest-year official BRREG annual-account copy addressed by exact organisation number and registry year; "
            "only unambiguous company-scope employee/FTE phrases publish; group/conflicting phrases abstain. "
            "Organisation-number/name presence in extracted PDF text is retained as a diagnostic, not required identity proof."
        ),
    }
    report["passed"] = len(audit) == len(selected) and not report["observation_validation_errors"]
    Path(args.output).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in observations), encoding="utf-8")
    Path(args.audit).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in audit), encoding="utf-8")
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
