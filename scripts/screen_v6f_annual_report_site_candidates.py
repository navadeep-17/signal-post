#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.annual_report_site_candidates import extract_annual_report_site_candidates  # noqa: E402
from norway_company_agent.annual_report_workforce import MAX_PDF_BYTES, UA, _ocr_pdf, latest_account_year  # noqa: E402
from norway_company_agent.official import BRREG_ACCOUNT_PDF  # noqa: E402


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def exact_site(profile: dict[str, Any]) -> bool:
    website = ((profile.get("evidence") or {}).get("website") or {})
    identity = ((website.get("value") or {}).get("identity_assessment") or {})
    return website.get("status") == "available" and bool(identity.get("publishable"))


def fetch_report_text(profile: dict[str, Any], *, timeout: float, ocr_pages: int, ocr_dpi: int) -> tuple[str | None, dict[str, Any]]:
    org = str(profile.get("organisation_number") or "")
    year = latest_account_year(profile)
    if not year:
        return None, {"organisation_number": org, "status": "no_latest_account_year", "request_count": 0}
    url = BRREG_ACCOUNT_PDF.format(org=org, year=year)
    started = time.monotonic()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/octet-stream"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_PDF_BYTES + 1)
            content_type = str(response.headers.get("content-type") or "")
        latency = int((time.monotonic() - started) * 1000)
        if len(raw) > MAX_PDF_BYTES or not raw.startswith(b"%PDF"):
            return None, {"organisation_number": org, "status": "unsupported_pdf", "request_count": 1, "bytes": len(raw), "content_type": content_type, "request_latency_ms": latency}
        reader = PdfReader(io.BytesIO(raw), strict=False)
        digital = "\n".join((page.extract_text() or "") for page in reader.pages[:120])
        ocr_used = len(digital.strip()) < 100 and ocr_pages > 0
        ocr = _ocr_pdf(raw, pages=min(ocr_pages, len(reader.pages)), dpi=ocr_dpi) if ocr_used else ""
        text = digital + ("\n" + ocr if ocr else "")
        if org not in re.sub(r"\D", "", text):
            return None, {"organisation_number": org, "status": "org_not_in_report_text", "request_count": 1, "bytes": len(raw), "request_latency_ms": latency, "ocr_used": ocr_used}
        return text, {
            "organisation_number": org,
            "status": "accepted_text",
            "year": year,
            "source_url": url,
            "request_count": 1,
            "bytes": len(raw),
            "request_latency_ms": latency,
            "content_sha256": hashlib.sha256(raw).hexdigest(),
            "digital_characters": len(digital.strip()),
            "ocr_used": ocr_used,
            "ocr_characters": len(ocr.strip()),
        }
    except Exception as exc:
        return None, {"organisation_number": org, "status": "error", "request_count": 1, "error": f"{type(exc).__name__}: {str(exc)[:180]}", "request_latency_ms": int((time.monotonic() - started) * 1000)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen exact-org BRREG annual reports for zero-cost website candidate hints")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--max-companies", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--min-start-interval", type=float, default=2.1)
    parser.add_argument("--ocr-pages", type=int, default=4)
    parser.add_argument("--ocr-dpi", type=int, default=110)
    args = parser.parse_args()

    profiles = read_jsonl(Path(args.profiles))
    unresolved = [row for row in profiles if not exact_site(row) and latest_account_year(row)]
    selected = unresolved[: max(0, args.max_companies)]
    rows: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    last_start = 0.0
    started = time.monotonic()

    for profile in selected:
        wait_for = args.min_start_interval - (time.monotonic() - last_start)
        if wait_for > 0:
            time.sleep(wait_for)
        last_start = time.monotonic()
        text, audit = fetch_report_text(profile, timeout=args.timeout, ocr_pages=args.ocr_pages, ocr_dpi=args.ocr_dpi)
        candidates = extract_annual_report_site_candidates(profile, text or "") if text else []
        audit["candidate_count"] = len(candidates)
        audit["high_candidate_count"] = sum(item["probe_recommendation"] == "high" for item in candidates)
        audit["medium_candidate_count"] = sum(item["probe_recommendation"] == "medium" for item in candidates)
        audits.append(audit)
        for item in candidates:
            rows.append({
                "organisation_number": str(profile.get("organisation_number") or ""),
                "company_name": profile.get("name"),
                "annual_report_year": audit.get("year"),
                "annual_report_source_url": audit.get("source_url"),
                "annual_report_sha256": audit.get("content_sha256"),
                **item,
            })

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    high_orgs = {row["organisation_number"] for row in rows if row["probe_recommendation"] == "high"}
    medium_orgs = {row["organisation_number"] for row in rows if row["probe_recommendation"] == "medium"}
    report = {
        "experiment": "V6f annual-report site candidate screen",
        "input_profiles": len(profiles),
        "unresolved_with_latest_accounts": len(unresolved),
        "selected": len(selected),
        "annual_report_requests": sum(int(item.get("request_count") or 0) for item in audits),
        "accepted_report_text": sum(item.get("status") == "accepted_text" for item in audits),
        "candidate_rows": len(rows),
        "companies_with_any_candidate": len({row["organisation_number"] for row in rows}),
        "companies_with_high_candidate": len(high_orgs),
        "companies_with_medium_candidate": len(medium_orgs),
        "high_candidate_rows": sum(row["probe_recommendation"] == "high" for row in rows),
        "medium_candidate_rows": sum(row["probe_recommendation"] == "medium" for row in rows),
        "candidate_source_kind_counts": dict(sorted(Counter(row["source_kind"] for row in rows).items())),
        "report_status_counts": dict(sorted(Counter(str(item.get("status") or "unknown") for item in audits).items())),
        "third_party_api_cost_usd": 0.0,
        "site_probe_requests": 0,
        "publication_count": 0,
        "wall_runtime_seconds": round(time.monotonic() - started, 3),
        "decision_rule": "Only high-confidence candidate reach is used to decide whether an independent exact-identity probe experiment is worth running; candidates themselves are never evidence.",
        "audit": audits,
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "audit"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
