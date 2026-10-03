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
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.ats_jobs import ats_provider, qualify_job_postings  # noqa: E402
from norway_company_agent.website import SAFE_OPENER, USER_AGENT, assert_public_url  # noqa: E402

MAX_REQUESTS_PER_ATS_TARGET = 2
MAX_BYTES = 2_000_000


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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


def qualify_target(row: dict[str, Any], *, timeout: float, as_of: date) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = row.get("ats_candidate") or {}
    target_url = str(candidate.get("url") or "").strip()
    provider = str(candidate.get("provider") or "").strip()
    profile = {
        "organisation_number": str(row.get("organisation_number") or ""),
        "name": str(row.get("name") or ""),
        "canonical_profile": {"company": {"legal_name": str(row.get("name") or "")}},
    }
    metrics = {"requests": 0, "bytes": 0, "latencies_ms": []}

    if not candidate.get("trusted_link_chain") or not target_url or ats_provider(target_url) != provider:
        return {"organisation_number": profile["organisation_number"], "status": "invalid_trust_chain", "jobs": []}, metrics

    parsed = urllib.parse.urlparse(target_url)
    robots_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    robots_text, robots_op = _fetch(robots_url, timeout=timeout, accept="text/plain,*/*;q=0.5")
    metrics["requests"] += 1
    metrics["bytes"] += int(robots_op.get("bytes") or 0)
    metrics["latencies_ms"].append(int(robots_op.get("latency_ms") or 0))

    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    if robots_text is not None and ats_provider(str(robots_op.get("final_url") or robots_url)) == provider:
        try:
            parser.parse(robots_text.splitlines())
        except Exception:
            parser.parse([])
        allowed = parser.can_fetch(USER_AGENT, target_url)
    else:
        allowed = True

    if not allowed:
        return {
            "organisation_number": profile["organisation_number"],
            "name": profile["name"],
            "status": "robots_disallowed",
            "target_url": target_url,
            "jobs": [],
        }, metrics

    html, page_op = _fetch(target_url, timeout=timeout, accept="text/html,application/xhtml+xml")
    metrics["requests"] += 1
    metrics["bytes"] += int(page_op.get("bytes") or 0)
    metrics["latencies_ms"].append(int(page_op.get("latency_ms") or 0))
    final_url = str(page_op.get("final_url") or target_url)
    if html is None or ats_provider(final_url) != provider:
        return {
            "organisation_number": profile["organisation_number"],
            "name": profile["name"],
            "status": "fetch_failed" if html is None else "redirected_outside_linked_ats_provider",
            "target_url": target_url,
            "final_url": final_url,
            "jobs": [],
            "page_error": page_op.get("error"),
        }, metrics

    digest = str(page_op.get("content_sha256") or "")
    jobs = qualify_job_postings(
        profile=profile,
        ats_candidate=candidate,
        job_page_url=final_url,
        job_html=html,
        content_sha256=digest,
        as_of=as_of,
    )
    return {
        "organisation_number": profile["organisation_number"],
        "name": profile["name"],
        "status": "qualified_job_found" if any(job.get("publishable") for job in jobs) else "no_publishable_job",
        "target_url": target_url,
        "final_url": final_url,
        "content_sha256": digest,
        "jobs": jobs,
        "claim_boundary": "Only JobPosting records marked publishable have exact employer alignment and explicit non-expired currentness.",
    }, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="V9 M3 qualify specific company-linked ATS targets.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--as-of", required=True, help="Qualification date in YYYY-MM-DD")
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()
    try:
        as_of = date.fromisoformat(args.as_of)
    except ValueError:
        parser.error("--as-of must be YYYY-MM-DD")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    rows = read_jsonl(Path(args.input))
    results: list[dict[str, Any]] = []
    requests = 0
    total_bytes = 0
    latencies: list[int] = []
    for row in rows:
        result, metrics = qualify_target(row, timeout=args.timeout, as_of=as_of)
        results.append(result)
        requests += int(metrics.get("requests") or 0)
        total_bytes += int(metrics.get("bytes") or 0)
        latencies.extend(int(value) for value in metrics.get("latencies_ms") or [])

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")

    all_jobs = [job for result in results for job in result.get("jobs") or []]
    publishable = [job for job in all_jobs if job.get("publishable")]
    report = {
        "schema_version": "signalpost-v9-m3-linked-ats-qualification-v1",
        "as_of": as_of.isoformat(),
        "targets": len(rows),
        "structured_jobs_seen": len(all_jobs),
        "publishable_jobs": len(publishable),
        "companies_with_publishable_jobs": len({result["organisation_number"] for result in results if any(job.get("publishable") for job in result.get("jobs") or [])}),
        "operations": {
            "requests": requests,
            "request_ceiling": len(rows) * MAX_REQUESTS_PER_ATS_TARGET,
            "bytes": total_bytes,
            "latency_p95_ms": sorted(latencies)[min(len(latencies) - 1, int((len(latencies) - 1) * 0.95))] if latencies else None,
            "third_party_api_cost_usd": 0.0,
        },
        "fresh_qualification_cohort_consumed": False,
        "production_integration": False,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
