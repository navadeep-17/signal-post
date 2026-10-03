#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.ats_jobs import extract_linked_ats_candidates  # noqa: E402
from norway_company_agent.website import SAFE_OPENER, USER_AGENT, _registered_domain, assert_public_url  # noqa: E402

MAX_REQUESTS_PER_CAREERS_SURFACE = 2
MAX_BYTES = 1_000_000


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _same_registered_domain(left: str, right: str) -> bool:
    try:
        a = _registered_domain(left)
        b = _registered_domain(right)
        return bool(a and b and a.casefold() == b.casefold())
    except Exception:
        return False


def _fetch(url: str, *, timeout: float, accept: str) -> tuple[str | None, dict[str, Any]]:
    started = time.monotonic()
    try:
        assert_public_url(url)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
        with SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(MAX_BYTES + 1)
            final_url = response.geturl()
            assert_public_url(final_url)
            status = int(response.status)
        elapsed = int((time.monotonic() - started) * 1000)
        if len(raw) > MAX_BYTES:
            return None, {"status": status, "bytes": len(raw), "latency_ms": elapsed, "final_url": final_url, "error": "document_too_large"}
        return raw.decode("utf-8", errors="replace"), {
            "status": status,
            "bytes": len(raw),
            "latency_ms": elapsed,
            "final_url": final_url,
            "content_sha256": hashlib.sha256(raw).hexdigest(),
        }
    except Exception as exc:
        return None, {
            "status": int(getattr(exc, "code", 0) or 0),
            "bytes": 0,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "final_url": url,
            "error": type(exc).__name__,
        }


def screen_row(row: dict[str, Any], *, timeout: float = 6.0) -> tuple[dict[str, Any], dict[str, Any]]:
    verified_url = str(row.get("verified_company_url") or "").strip()
    careers_url = str(row.get("careers_url") or "").strip()
    if not verified_url or not careers_url or not _same_registered_domain(verified_url, careers_url):
        return {
            "organisation_number": row.get("organisation_number"),
            "name": row.get("name"),
            "status": "invalid_reused_input",
            "ats_candidates": [],
        }, {"requests": 0, "bytes": 0, "latencies_ms": []}

    metrics = {"requests": 0, "bytes": 0, "latencies_ms": []}
    parsed = urllib.parse.urlparse(careers_url)
    robots_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    robots_text, robots_op = _fetch(robots_url, timeout=timeout, accept="text/plain,*/*;q=0.5")
    metrics["requests"] += 1
    metrics["bytes"] += int(robots_op.get("bytes") or 0)
    metrics["latencies_ms"].append(int(robots_op.get("latency_ms") or 0))

    robots_parser = urllib.robotparser.RobotFileParser()
    robots_parser.set_url(robots_url)
    if robots_text is not None and _same_registered_domain(str(robots_op.get("final_url") or robots_url), verified_url):
        try:
            robots_parser.parse(robots_text.splitlines())
        except Exception:
            robots_parser.parse([])
        allowed = robots_parser.can_fetch(USER_AGENT, careers_url)
    else:
        # Same conservative starter policy used elsewhere: unavailable robots permits
        # the one requested first-party page, but no deeper crawl follows in this screen.
        allowed = True

    if not allowed:
        return {
            "organisation_number": row.get("organisation_number"),
            "name": row.get("name"),
            "status": "robots_disallowed",
            "careers_url": careers_url,
            "ats_candidates": [],
        }, metrics

    html, page_op = _fetch(careers_url, timeout=timeout, accept="text/html,application/xhtml+xml")
    metrics["requests"] += 1
    metrics["bytes"] += int(page_op.get("bytes") or 0)
    metrics["latencies_ms"].append(int(page_op.get("latency_ms") or 0))
    final_url = str(page_op.get("final_url") or careers_url)
    same_domain = _same_registered_domain(final_url, verified_url)
    if html is None or not same_domain:
        return {
            "organisation_number": row.get("organisation_number"),
            "name": row.get("name"),
            "status": "fetch_failed" if html is None else "redirected_outside_verified_domain",
            "careers_url": careers_url,
            "final_url": final_url,
            "ats_candidates": [],
            "page_error": page_op.get("error"),
        }, metrics

    digest = str(page_op.get("content_sha256") or "")
    candidates = extract_linked_ats_candidates(
        verified_company_url=verified_url,
        careers_url=final_url,
        careers_html=html,
        careers_content_sha256=digest,
    )
    return {
        "organisation_number": row.get("organisation_number"),
        "name": row.get("name"),
        "status": "ats_link_found" if candidates else "no_supported_ats_link",
        "careers_url": careers_url,
        "final_url": final_url,
        "careers_content_sha256": digest,
        "ats_candidates": candidates,
        "claim_boundary": "Direct ATS links only. No ATS link or careers page is an active-vacancy claim.",
    }, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="V9 M3 reused-careers ATS link screen.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--timeout", type=float, default=6.0)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    rows = read_jsonl(Path(args.input))
    results: list[dict[str, Any]] = []
    requests = 0
    total_bytes = 0
    latencies: list[int] = []
    for row in rows:
        result, metrics = screen_row(row, timeout=args.timeout)
        results.append(result)
        requests += int(metrics.get("requests") or 0)
        total_bytes += int(metrics.get("bytes") or 0)
        latencies.extend(int(value) for value in metrics.get("latencies_ms") or [])

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")

    companies_with_ats = sum(bool(row.get("ats_candidates")) for row in results)
    ats_links = sum(len(row.get("ats_candidates") or []) for row in results)
    report = {
        "schema_version": "signalpost-v9-m3-reused-careers-screen-v1",
        "reused_careers_surfaces": len(rows),
        "companies_with_supported_ats_links": companies_with_ats,
        "supported_ats_links": ats_links,
        "operations": {
            "requests": requests,
            "request_ceiling": len(rows) * MAX_REQUESTS_PER_CAREERS_SURFACE,
            "bytes": total_bytes,
            "latency_p95_ms": sorted(latencies)[min(len(latencies) - 1, int((len(latencies) - 1) * 0.95))] if latencies else None,
            "third_party_api_cost_usd": 0.0,
        },
        "fresh_qualification_cohort_consumed": False,
        "production_integration": False,
        "claim_boundary": "ATS provenance measurement only; no active vacancy is published by this screen.",
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
