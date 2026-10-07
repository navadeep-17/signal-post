#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
import sys
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.annual_report_site_nomination import (
    evaluate_annual_report_site_candidates,
    extract_annual_report_bare_no_candidates,
)
from norway_company_agent.annual_report_workforce import (
    MAX_PDF_BYTES,
    UA,
    _ocr_pdf,
    latest_account_year,
    needs_ocr,
)
from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs
from norway_company_agent.official import BRREG_ACCOUNT_PDF


MIN_NET_NEW_VERIFIED_WEBSITES = 2


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{lineno}: expected object")
        rows.append(item)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def baseline_has_verified_website(row: dict[str, Any]) -> bool:
    return any(
        isinstance(claim, dict)
        and claim.get("field") == "official_website"
        and claim.get("availability") == "available"
        and claim.get("value")
        for claim in (row.get("claims") or [])
    )


def fetch_report_text(
    profile: dict[str, Any],
    *,
    timeout: float,
    ocr_pages: int,
    ocr_dpi: int,
) -> tuple[str | None, dict[str, Any]]:
    org = str(profile.get("organisation_number") or "")
    year = latest_account_year(profile)
    if not year:
        return None, {
            "organisation_number": org,
            "status": "no_latest_account_year",
            "request_count": 0,
        }

    url = BRREG_ACCOUNT_PDF.format(org=org, year=year)
    started = time.monotonic()
    result: dict[str, Any] = {
        "organisation_number": org,
        "year": year,
        "source_url": url,
        "request_count": 1,
    }
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": UA, "Accept": "application/octet-stream"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(MAX_PDF_BYTES + 1)
            content_type = str(response.headers.get("content-type") or "")
        elapsed = int((time.monotonic() - started) * 1000)
        if len(raw) > MAX_PDF_BYTES or not raw.startswith(b"%PDF"):
            return None, {
                **result,
                "status": "unsupported_pdf",
                "bytes": len(raw),
                "content_type": content_type,
                "request_latency_ms": elapsed,
            }

        reader = PdfReader(io.BytesIO(raw), strict=False)
        digital = "\n".join((page.extract_text() or "") for page in reader.pages[:120])
        ocr_used = needs_ocr(digital) and ocr_pages > 0
        ocr = ""
        if ocr_used:
            ocr = _ocr_pdf(raw, pages=min(ocr_pages, len(reader.pages)), dpi=ocr_dpi)
        text = digital + ("\n" + ocr if ocr else "")
        org_in_text = org in re.sub(r"\D", "", text)
        digest = hashlib.sha256(raw).hexdigest()
        if not org_in_text:
            return None, {
                **result,
                "status": "organisation_number_not_in_report_text",
                "bytes": len(raw),
                "request_latency_ms": elapsed,
                "content_sha256": digest,
                "ocr_used": ocr_used,
                "ocr_pages": min(ocr_pages, len(reader.pages)) if ocr_used else 0,
            }
        return text, {
            **result,
            "status": "available",
            "bytes": len(raw),
            "request_latency_ms": elapsed,
            "content_sha256": digest,
            "ocr_used": ocr_used,
            "ocr_pages": min(ocr_pages, len(reader.pages)) if ocr_used else 0,
            "digital_text_characters": len(digital.strip()),
            "ocr_characters": len(ocr.strip()),
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
            "error": f"{type(exc).__name__}: {str(exc)[:200]}",
            "request_latency_ms": int((time.monotonic() - started) * 1000),
        }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--bulk", type=Path, required=True)
    p.add_argument("--baseline-output", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--manual-audit", type=Path, required=True)
    p.add_argument("--annual-timeout", type=float, default=60.0)
    p.add_argument("--ocr-pages", type=int, default=8)
    p.add_argument("--ocr-dpi", type=int, default=110)
    p.add_argument("--site-timeout", type=float, default=6.0)
    p.add_argument("--max-site-candidates", type=int, default=1)
    args = p.parse_args()

    manifest = read_organisation_inputs(args.manifest)
    orgs = [str(row["organisation_number"]) for row in manifest]
    if len(orgs) != 20 or len(set(orgs)) != 20:
        raise ValueError(f"M16 requires exactly 20 unique companies, got {len(orgs)}")

    baseline_rows = read_jsonl(args.baseline_output)
    baseline = {
        str(row.get("organisation_number") or ""): row
        for row in baseline_rows
    }
    if set(baseline) != set(orgs):
        raise ValueError("baseline output company set differs from frozen M16 manifest")

    profiles, snapshot = profiles_from_bulk(args.bulk, orgs)
    profile_by_org = {
        str(profile.get("organisation_number") or ""): profile
        for profile in profiles
    }

    rows: list[dict[str, Any]] = []
    manual: list[dict[str, Any]] = []
    report_requests = 0
    site_requests = 0
    report_bytes = 0
    site_bytes = 0
    candidate_companies = 0
    candidate_domains = 0
    verified = 0
    baseline_verified = 0
    evidence_defects: list[dict[str, Any]] = []
    execution_errors: list[dict[str, Any]] = []

    for org in orgs:
        profile = profile_by_org[org]
        baseline_site = baseline_has_verified_website(baseline[org])
        baseline_verified += int(baseline_site)
        item: dict[str, Any] = {
            "organisation_number": org,
            "baseline_verified_website": baseline_site,
            "annual_report": None,
            "candidates": [],
            "site_evaluation": None,
            "net_new_verified_website": False,
        }
        if baseline_site:
            item["screen_status"] = "baseline_already_verified"
            rows.append(item)
            continue

        text, report_result = fetch_report_text(
            profile,
            timeout=args.annual_timeout,
            ocr_pages=args.ocr_pages,
            ocr_dpi=args.ocr_dpi,
        )
        item["annual_report"] = report_result
        report_requests += int(report_result.get("request_count") or 0)
        report_bytes += int(report_result.get("bytes") or 0)

        if report_result.get("status") == "error":
            execution_errors.append(
                {
                    "organisation_number": org,
                    "stage": "annual_report",
                    "error": report_result.get("error"),
                }
            )
        if text is None:
            item["screen_status"] = str(report_result.get("status") or "annual_report_unavailable")
            rows.append(item)
            continue

        candidates = extract_annual_report_bare_no_candidates(
            profile,
            text,
            max_candidates=max(1, args.max_site_candidates),
        )
        item["candidates"] = candidates
        if candidates:
            candidate_companies += 1
            candidate_domains += len(candidates)
        if not candidates:
            item["screen_status"] = "no_site_candidate_in_report"
            rows.append(item)
            continue

        enriched, site_result = evaluate_annual_report_site_candidates(
            profile,
            candidates,
            timeout=args.site_timeout,
            max_candidates=args.max_site_candidates,
        )
        item["site_evaluation"] = site_result
        site_requests += int(site_result.get("requests") or 0)
        site_bytes += int(site_result.get("bytes") or 0)

        if site_result.get("verified"):
            verified += 1
            item["net_new_verified_website"] = True
            item["screen_status"] = "verified"
            selected_url = str(site_result.get("selected_url") or "")
            candidate_result = next(
                (
                    row
                    for row in (site_result.get("candidate_results") or [])
                    if row.get("domain") == site_result.get("selected_domain")
                ),
                None,
            ) or {}
            defects: list[str] = []
            if not selected_url.startswith(("http://", "https://")):
                defects.append("selected_url_missing")
            if len(str(report_result.get("content_sha256") or "")) != 64:
                defects.append("annual_report_hash_missing")
            if len(str(candidate_result.get("website_content_sha256") or "")) != 64:
                defects.append("website_hash_missing")
            if not str(candidate_result.get("annual_report_evidence_span") or "").strip():
                defects.append("annual_report_candidate_span_missing")
            if not bool(candidate_result.get("identity_publishable")):
                defects.append("independent_identity_not_publishable")
            if defects:
                evidence_defects.append(
                    {
                        "organisation_number": org,
                        "defects": defects,
                    }
                )
            manual.append(
                {
                    "organisation_number": org,
                    "selected_domain": site_result.get("selected_domain"),
                    "selected_url": selected_url,
                    "annual_report_source_url": report_result.get("source_url"),
                    "annual_report_content_sha256": report_result.get("content_sha256"),
                    "annual_report_candidate_span": candidate_result.get("annual_report_evidence_span"),
                    "website_content_sha256": candidate_result.get("website_content_sha256"),
                    "identity_status": candidate_result.get("identity_status"),
                    "identity_score": candidate_result.get("identity_score"),
                    "identity_reasons": candidate_result.get("identity_reasons"),
                    "registry_guard_reasons": site_result.get("guard_reasons"),
                    "manual_review_finalized": False,
                }
            )
        else:
            item["screen_status"] = "candidate_failed_exact_identity_gate"
        rows.append(item)

    if len(rows) != 20:
        raise AssertionError("M16 output lost companies")

    if evidence_defects or execution_errors:
        decision = "BLOCKED"
    elif verified >= MIN_NET_NEW_VERIFIED_WEBSITES:
        decision = "MANUAL_AUDIT_REQUIRED"
    else:
        decision = "SHELVE_LOW_YIELD"

    report = {
        "milestone": "M16",
        "screen": "consumed_official_annual_report_bare_domain",
        "machine_decision": decision,
        "companies": len(rows),
        "fresh_companies_used": 0,
        "baseline_verified_website_companies": baseline_verified,
        "annual_report_requests": report_requests,
        "candidate_site_requests": site_requests,
        "total_screen_logical_requests": report_requests + site_requests,
        "annual_report_bytes": report_bytes,
        "candidate_site_bytes": site_bytes,
        "companies_with_report_site_candidate": candidate_companies,
        "report_site_candidate_domains": candidate_domains,
        "net_new_verified_website_companies": verified,
        "minimum_net_new_verified_website_companies": MIN_NET_NEW_VERIFIED_WEBSITES,
        "manual_review_rows": len(manual),
        "manual_review_finalized": False,
        "evidence_defects": evidence_defects,
        "execution_errors": execution_errors,
        "third_party_api_cost_usd": 0.0,
        "search_api_requests": 0,
        "publication_authorized": False,
        "production_promotion_authorized": False,
        "fresh_qualification_authorized": False,
        "candidate_boundary": (
            "Official exact-org annual report bare .no text nominates candidates only, after excluding "
            "registry-email and deterministic H1c/H1g domains already tried by the baseline. Only an "
            "independently fetched page passing the exact-company identity and registry-risk guards counts."
        ),
        "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
    }

    write_jsonl(args.output, rows)
    write_jsonl(args.manual_audit, manual)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if decision != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
