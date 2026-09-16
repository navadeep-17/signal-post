#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.external_footprint import validate_observation  # noqa: E402
from norway_company_agent.official import BRREG_ACCOUNT_PDF  # noqa: E402

# Reuse the already-audited conservative phrase extractor rather than inventing a second parser.
import run_annual_report_workforce_connector as workforce  # noqa: E402

UA = "signal-post/0.1 (+https://github.com/navadeep-17/signal-post)"
MAX_PDF_BYTES = 20_000_000


def registry_employee_count(profile: dict) -> int | None:
    registry = ((profile.get("evidence") or {}).get("registry") or {}).get("value") or {}
    live = ((profile.get("evidence") or {}).get("registry_live") or {}).get("value") or {}
    for value in (registry.get("antallAnsatte"), registry.get("employees"), live.get("employees")):
        text = str(value or "").strip()
        if text.isdigit():
            return int(text)
    return None


def latest_account_year(profile: dict) -> str | None:
    live = ((profile.get("evidence") or {}).get("registry_live") or {}).get("value") or {}
    candidates = [profile.get("latest_submitted_accounts"), live.get("latest_submitted_accounts")]
    for value in candidates:
        text = str(value or "").strip()
        if len(text) == 4 and text.isdigit():
            return text
    return None


def collect(profile: dict, *, timeout: float) -> tuple[dict | None, dict]:
    org = str(profile.get("organisation_number") or "")
    year = latest_account_year(profile)
    if registry_employee_count(profile) is not None:
        return None, {"organisation_number": org, "status": "registry_count_already_available"}
    if not year:
        return None, {"organisation_number": org, "status": "no_latest_account_year"}

    url = BRREG_ACCOUNT_PDF.format(org=org, year=year)
    result = {"organisation_number": org, "year": year, "url": url, "request_count": 1}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_PDF_BYTES + 1)
        if len(raw) > MAX_PDF_BYTES or not raw.startswith(b"%PDF"):
            return None, {**result, "status": "unsupported_pdf", "bytes": len(raw)}

        reader = PdfReader(io.BytesIO(raw), strict=False)
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:120])
        digits = re.sub(r"\D", "", text)
        if org not in digits:
            return None, {**result, "status": "organisation_number_not_in_pdf", "pages": len(reader.pages)}

        count, span, status, measure = workforce.extract_candidate(text)
        if count is None:
            return None, {**result, "status": status, "pages": len(reader.pages)}

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
                {"type": "official_report_url_organisation_number", "value": org},
                {"type": "organisation_number_in_pdf", "value": org},
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
            "strategy": "annual_report_workforce_snapshot_direct_latest_year_v2",
        }
        errors = validate_observation(observation)
        if errors:
            return None, {**result, "status": "validation_error", "validation_errors": errors}
        return observation, {
            **result,
            "status": "accepted",
            "workforce_value": count,
            "measure": measure,
            "evidence_span": span,
            "pages": len(reader.pages),
        }
    except Exception as exc:
        return None, {**result, "status": "error", "error": f"{type(exc).__name__}: {str(exc)[:180]}"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen official BRREG annual-report PDFs for exact-entity workforce snapshots.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--limit", type=int, default=90)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    profiles = [json.loads(line) for line in Path(args.profiles).read_text(encoding="utf-8").splitlines() if line.strip()]
    eligible = [
        profile for profile in profiles
        if registry_employee_count(profile) is None and latest_account_year(profile)
    ]
    selected = eligible[: max(0, args.limit)]

    observations = []
    audit = []
    for profile in selected:
        observation, result = collect(profile, timeout=args.timeout)
        audit.append(result)
        if observation:
            observations.append(observation)

    Path(args.output).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in observations), encoding="utf-8")
    Path(args.audit).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in audit), encoding="utf-8")
    status_counts = {}
    for row in audit:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    report = {
        "experiment": "h2e_official_workforce_screen_v1",
        "profiles": len(profiles),
        "eligible": len(eligible),
        "selected": len(selected),
        "requests": sum(int(row.get("request_count") or 0) for row in audit),
        "accepted": len(observations),
        "accepted_company_coverage_over_all_profiles": round(len(observations) / len(profiles), 6) if profiles else 0.0,
        "accepted_rate_over_selected": round(len(observations) / len(selected), 6) if selected else 0.0,
        "status_counts": status_counts,
        "third_party_cost_usd": 0.0,
        "claim_boundary": "One official latest-year BRREG annual-account PDF request; exact organisation number must occur in the PDF and only unambiguous company-scope workforce phrases publish.",
        "passed": len(audit) == len(selected) and all(not validate_observation(row) for row in observations),
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
