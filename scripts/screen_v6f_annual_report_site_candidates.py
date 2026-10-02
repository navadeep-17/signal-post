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
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.annual_report_site_candidate import (  # noqa: E402
    extract_annual_report_site_candidates,
    verify_annual_report_site_candidate,
)
from norway_company_agent.annual_report_workforce import (  # noqa: E402
    MAX_PDF_BYTES,
    UA,
    _ocr_pdf,
    latest_account_year,
    needs_ocr,
)
from norway_company_agent.official import BRREG_ACCOUNT_PDF  # noqa: E402

OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE = 5
MAX_SITE_LOGICAL_REQUESTS_PER_PROFILE = 4


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def verified_site(profile: dict[str, Any]) -> bool:
    website = ((profile.get("evidence") or {}).get("website") or {})
    identity = ((website.get("value") or {}).get("identity_assessment") or {})
    return website.get("status") == "available" and bool(identity.get("publishable"))


def infer_site_and_annual_requests(profile: dict[str, Any]) -> tuple[int | None, int | None]:
    """Recover V5 per-profile request decomposition from invariant request parity.

    Official modules use exactly five logical requests. Every site probe costs two
    logical requests (robots + page). The annual-account stage adds either zero or one.
    Therefore the remainder after the five official requests has parity equal to the
    annual-account request flag.
    """
    total = int((profile.get("run_metrics") or {}).get("logical_requests") or 0)
    remainder = total - OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE
    if remainder < 0:
        return None, None
    annual = remainder % 2
    site = remainder - annual
    if site not in {0, 2, 4}:
        return None, None
    return site, annual


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
        return None, {"status": "no_latest_account_year", "request_count": 0}
    url = BRREG_ACCOUNT_PDF.format(org=org, year=year)
    started = time.monotonic()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/octet-stream"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_PDF_BYTES + 1)
            content_type = str(response.headers.get("content-type") or "")
        latency = int((time.monotonic() - started) * 1000)
        if len(raw) > MAX_PDF_BYTES or not raw.startswith(b"%PDF"):
            return None, {"status": "unsupported_pdf", "request_count": 1, "bytes": len(raw), "request_latency_ms": latency}
        reader = PdfReader(io.BytesIO(raw), strict=False)
        digital = "\n".join((page.extract_text() or "") for page in reader.pages[:120])
        ocr_text = ""
        ocr_used = needs_ocr(digital) and ocr_pages > 0
        if ocr_used:
            ocr_text = _ocr_pdf(raw, pages=min(ocr_pages, len(reader.pages)), dpi=ocr_dpi)
        text = digital + ("\n" + ocr_text if ocr_text else "")
        if org not in re.sub(r"\D", "", text):
            return None, {
                "status": "organisation_number_not_in_text", "request_count": 1, "bytes": len(raw),
                "request_latency_ms": latency, "ocr_used": ocr_used,
            }
        return text, {
            "status": "accepted", "request_count": 1, "bytes": len(raw), "request_latency_ms": latency,
            "ocr_used": ocr_used, "content_sha256": hashlib.sha256(raw).hexdigest(), "source_url": url,
            "year": year,
        }
    except urllib.error.HTTPError as exc:
        return None, {"status": f"http_{exc.code}", "request_count": 1, "request_latency_ms": int((time.monotonic() - started) * 1000)}
    except Exception as exc:
        return None, {
            "status": "error", "request_count": 1, "request_latency_ms": int((time.monotonic() - started) * 1000),
            "error": f"{type(exc).__name__}: {str(exc)[:180]}",
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="V6f non-publishing annual-report website candidate screen")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--baseline-report", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--site-timeout", type=float, default=6.0)
    parser.add_argument("--ocr-pages", type=int, default=8)
    parser.add_argument("--ocr-dpi", type=int, default=110)
    parser.add_argument("--max-report-refetches", type=int, default=100)
    parser.add_argument("--max-candidate-probes", type=int, default=30)
    args = parser.parse_args()

    profiles = read_jsonl(Path(args.profiles))
    baseline_report = json.loads(Path(args.baseline_report).read_text(encoding="utf-8"))
    baseline_charge = int((baseline_report.get("request_budget") or {}).get("observed_conservative_challenge_request_charge") or 0)
    started = time.monotonic()

    unresolved = 0
    production_report_reuse_eligible = 0
    report_refetches = 0
    reports_with_candidates = 0
    candidate_probes = 0
    verified = 0
    audit: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}

    for profile in profiles:
        if verified_site(profile):
            continue
        unresolved += 1
        site_requests, annual_request = infer_site_and_annual_requests(profile)
        if site_requests is None or annual_request != 1:
            continue
        # A production implementation would reuse this already-charged annual report.
        production_report_reuse_eligible += 1
        if report_refetches >= args.max_report_refetches:
            break
        report_refetches += 1
        text, report_meta = fetch_report_text(
            profile, timeout=args.timeout, ocr_pages=args.ocr_pages, ocr_dpi=args.ocr_dpi
        )
        status = str(report_meta.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        row: dict[str, Any] = {
            "organisation_number": str(profile.get("organisation_number") or ""),
            "name": profile.get("name"),
            "existing_site_logical_requests": site_requests,
            "annual_request_already_present_in_v5": True,
            "experiment_report_refetch_only": True,
            "report": report_meta,
            "candidates": [],
            "probe": None,
        }
        if text is None:
            audit.append(row)
            continue
        candidates = extract_annual_report_site_candidates(
            profile,
            text=text,
            source_url=str(report_meta["source_url"]),
            content_sha256=str(report_meta["content_sha256"]),
            max_candidates=3,
        )
        row["candidates"] = candidates
        if candidates:
            reports_with_candidates += 1
        # Preserve the existing four-logical-request site ceiling in the modeled production path.
        if not candidates or site_requests + 2 > MAX_SITE_LOGICAL_REQUESTS_PER_PROFILE or candidate_probes >= args.max_candidate_probes:
            audit.append(row)
            continue
        candidate_probes += 1
        record, probe = verify_annual_report_site_candidate(profile, candidates[0], timeout=args.site_timeout)
        row["probe"] = probe
        if record is not None:
            verified += 1
            row["verified_website"] = {
                "source_url": record.get("source_url"),
                "final_url": (record.get("value") or {}).get("final_url"),
                "registered_domain": (record.get("value") or {}).get("registered_domain"),
                "content_sha256": record.get("content_sha256") or (record.get("value") or {}).get("content_sha256"),
                "identity_assessment": (record.get("value") or {}).get("identity_assessment"),
                "annual_report_candidate_proof": (record.get("value") or {}).get("annual_report_candidate_proof"),
            }
        audit.append(row)

    modeled_added_logical = candidate_probes * 2
    modeled_added_charge = modeled_added_logical * 2
    report = {
        "experiment": "V6f annual-report site candidates",
        "publication_enabled": False,
        "profiles": len(profiles),
        "unresolved_websites": unresolved,
        "production_report_reuse_eligible": production_report_reuse_eligible,
        "experiment_report_refetches": report_refetches,
        "experiment_report_refetches_counted_as_production_increment": False,
        "reports_with_candidates": reports_with_candidates,
        "candidate_probes": candidate_probes,
        "verified_sites": verified,
        "verified_sites_per_candidate_probe": (verified / candidate_probes) if candidate_probes else 0.0,
        "modeled_incremental_logical_requests": modeled_added_logical,
        "modeled_incremental_conservative_charge": modeled_added_charge,
        "baseline_observed_conservative_charge": baseline_charge,
        "modeled_combined_observed_conservative_charge": baseline_charge + modeled_added_charge,
        "wrong_company_publications": 0,
        "third_party_api_cost_usd": 0.0,
        "search_api_requests": 0,
        "report_status_counts": status_counts,
        "runtime_seconds": round(time.monotonic() - started, 3),
        "decision_metric": "new exact verified websites / added charged network request",
        "candidate_boundary": "official exact-org annual report only nominates; independent fetched site plus strong exact-company corroboration decides verification",
    }
    write_jsonl(Path(args.audit), audit)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
