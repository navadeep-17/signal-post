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
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.structured_first_party import (  # noqa: E402
    discover_feed_links,
    extract_structured_surfaces,
    parse_feed_xml,
    parse_sitemap_xml,
    verified_site_url,
)
from norway_company_agent.website import (  # noqa: E402
    SAFE_OPENER,
    USER_AGENT,
    _registered_domain,
    assert_public_url,
)

MAX_REQUESTS_PER_VERIFIED_SITE = 5
MAX_DOCUMENT_BYTES = 1_000_000


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _same_registered_domain(url: str, verified_url: str) -> bool:
    try:
        return bool(_registered_domain(url)) and _registered_domain(url) == _registered_domain(verified_url)
    except Exception:
        return False


def _robots_url(verified_url: str) -> str:
    parsed = urllib.parse.urlparse(verified_url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))


def _clean_candidate(raw: str, *, base_url: str, verified_url: str) -> str | None:
    absolute = urllib.parse.urljoin(base_url, str(raw or "").strip())
    parsed = urllib.parse.urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    clean = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))
    if not _same_registered_domain(clean, verified_url):
        return None
    return clean


def fetch_document(url: str, *, timeout: float, accept: str) -> tuple[str | None, dict[str, Any]]:
    """Fetch one public document with same redirect safety as the existing website path."""
    started = time.monotonic()
    try:
        assert_public_url(url)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
        with SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(MAX_DOCUMENT_BYTES + 1)
            final_url = response.geturl()
            assert_public_url(final_url)
            content_type = str(response.headers.get("content-type") or "")
            status = int(response.status)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        if len(raw) > MAX_DOCUMENT_BYTES:
            return None, {"status": status, "bytes": len(raw), "latency_ms": elapsed_ms, "final_url": final_url, "error": "document_too_large"}
        return raw.decode("utf-8", errors="replace"), {
            "status": status,
            "bytes": len(raw),
            "latency_ms": elapsed_ms,
            "final_url": final_url,
            "content_type": content_type,
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


def parse_robots(text: str | None, *, robots_url: str, verified_url: str) -> tuple[urllib.robotparser.RobotFileParser, list[str]]:
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    lines = str(text or "").splitlines()
    try:
        parser.parse(lines)
    except Exception:
        parser.parse([])
    sitemaps: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().casefold() != "sitemap":
            continue
        clean = _clean_candidate(value.strip(), base_url=verified_url, verified_url=verified_url)
        if not clean or clean in seen:
            continue
        seen.add(clean)
        sitemaps.append(clean)
        if len(sitemaps) >= 2:
            break
    return parser, sitemaps


def _dedupe_records(records: list[dict[str, Any]], *, limit: int = 80) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    output: list[dict[str, Any]] = []
    for row in records:
        key = (str(row.get("surface_kind") or ""), str(row.get("url") or ""))
        if not key[1] or key in seen:
            continue
        seen.add(key)
        output.append(row)
        if len(output) >= limit:
            break
    return output


def discover_profile(profile: dict[str, Any], *, timeout: float = 6.0) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Discover structured first-party surfaces with at most five network requests.

    Requests: robots, homepage, up to two sitemap documents, and at most one feed.
    No discovered article/job is published as a canonical fact by this runner.
    """
    verified_url = verified_site_url(profile)
    if not verified_url:
        return None, {"requests": 0, "bytes": 0, "latencies_ms": [], "reason": "no_verified_site"}

    metrics: dict[str, Any] = {"requests": 0, "bytes": 0, "latencies_ms": []}
    sources: list[dict[str, Any]] = []
    surfaces: list[dict[str, Any]] = []

    def charge(operation: dict[str, Any]) -> None:
        metrics["requests"] += 1
        metrics["bytes"] += int(operation.get("bytes") or 0)
        metrics["latencies_ms"].append(int(operation.get("latency_ms") or 0))

    robots_url = _robots_url(verified_url)
    robots_text, robots_op = fetch_document(robots_url, timeout=timeout, accept="text/plain,*/*;q=0.5")
    charge(robots_op)
    robots_parser, declared_sitemaps = parse_robots(robots_text, robots_url=robots_url, verified_url=verified_url)
    sources.append({"kind": "robots", "url": robots_url, "status": robots_op.get("status"), "content_sha256": robots_op.get("content_sha256")})

    if metrics["requests"] >= MAX_REQUESTS_PER_VERIFIED_SITE:
        raise AssertionError("M2 request ceiling exhausted before homepage")

    homepage_text: str | None = None
    if robots_text is None or robots_parser.can_fetch(USER_AGENT, verified_url):
        homepage_text, homepage_op = fetch_document(verified_url, timeout=timeout, accept="text/html,application/xhtml+xml")
        charge(homepage_op)
        final_homepage = str(homepage_op.get("final_url") or verified_url)
        if homepage_text is not None and _same_registered_domain(final_homepage, verified_url):
            surfaces.extend(extract_structured_surfaces(homepage_text, page_url=final_homepage, verified_url=verified_url))
            feed_links = discover_feed_links(homepage_text, page_url=final_homepage, verified_url=verified_url)
        else:
            feed_links = []
        sources.append({"kind": "homepage", "url": final_homepage, "status": homepage_op.get("status"), "content_sha256": homepage_op.get("content_sha256")})
    else:
        feed_links = []
        sources.append({"kind": "homepage", "url": verified_url, "status": "robots_disallowed", "content_sha256": None})

    sitemap_queue = list(declared_sitemaps)
    fallback_sitemap = urllib.parse.urljoin(verified_url, "/sitemap.xml")
    if fallback_sitemap not in sitemap_queue:
        sitemap_queue.append(fallback_sitemap)

    fetched_sitemaps = 0
    seen_sitemaps: set[str] = set()
    while sitemap_queue and fetched_sitemaps < 2 and metrics["requests"] < MAX_REQUESTS_PER_VERIFIED_SITE:
        sitemap_url = sitemap_queue.pop(0)
        if sitemap_url in seen_sitemaps or not _same_registered_domain(sitemap_url, verified_url):
            continue
        if robots_text is not None and not robots_parser.can_fetch(USER_AGENT, sitemap_url):
            continue
        seen_sitemaps.add(sitemap_url)
        sitemap_text, sitemap_op = fetch_document(sitemap_url, timeout=timeout, accept="application/xml,text/xml,*/*;q=0.5")
        charge(sitemap_op)
        fetched_sitemaps += 1
        sources.append({"kind": "sitemap", "url": sitemap_url, "status": sitemap_op.get("status"), "content_sha256": sitemap_op.get("content_sha256")})
        if sitemap_text is None:
            continue
        parsed = parse_sitemap_xml(sitemap_text, sitemap_url=sitemap_url, verified_url=verified_url)
        surfaces.extend(parsed.get("surface_candidates") or [])
        for nested in parsed.get("nested_sitemaps") or []:
            if nested not in seen_sitemaps and nested not in sitemap_queue:
                sitemap_queue.append(nested)

    if feed_links and metrics["requests"] < MAX_REQUESTS_PER_VERIFIED_SITE:
        feed_url = feed_links[0]
        if robots_text is None or robots_parser.can_fetch(USER_AGENT, feed_url):
            feed_text, feed_op = fetch_document(feed_url, timeout=timeout, accept="application/rss+xml,application/atom+xml,application/xml,text/xml,*/*;q=0.5")
            charge(feed_op)
            sources.append({"kind": "feed", "url": feed_url, "status": feed_op.get("status"), "content_sha256": feed_op.get("content_sha256")})
            if feed_text is not None:
                surfaces.extend(parse_feed_xml(feed_text, feed_url=feed_url, verified_url=verified_url))

    assert metrics["requests"] <= MAX_REQUESTS_PER_VERIFIED_SITE, metrics
    surfaces = _dedupe_records(surfaces)
    result = {
        "organisation_number": str(profile.get("organisation_number") or ""),
        "verified_website": verified_url,
        "surface_candidates": surfaces,
        "sources": sources,
        "claim_boundary": "Discovery only. No candidate is a qualified article/update/job until a later milestone independently fetches and validates the destination.",
    }
    return result, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="V9 M2 bounded structured first-party discovery over already verified company sites.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=6.0)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    profiles = read_jsonl(Path(args.profiles))
    observations: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    total_requests = 0
    total_bytes = 0
    latencies: list[int] = []
    attempted = 0

    for profile in profiles:
        if attempted >= args.limit:
            break
        if not verified_site_url(profile):
            counts["unverified_site_skipped"] += 1
            continue
        attempted += 1
        observation, metrics = discover_profile(profile, timeout=args.timeout)
        total_requests += int(metrics.get("requests") or 0)
        total_bytes += int(metrics.get("bytes") or 0)
        latencies.extend(int(value) for value in metrics.get("latencies_ms") or [])
        if observation is None:
            counts["no_observation"] += 1
            continue
        observations.append(observation)
        candidates = observation.get("surface_candidates") or []
        counts["companies_processed"] += 1
        if candidates:
            counts["companies_with_surfaces"] += 1
        for item in candidates:
            counts[str(item.get("surface_kind") or "unknown_surface")] += 1

    write_jsonl(Path(args.output), observations)
    report = {
        "schema_version": "signalpost-v9-m2-structured-first-party-v1",
        "input_profiles": len(profiles),
        "verified_sites_attempted": attempted,
        "observations": len(observations),
        "counts": dict(sorted(counts.items())),
        "operations": {
            "requests": total_requests,
            "request_ceiling": attempted * MAX_REQUESTS_PER_VERIFIED_SITE,
            "bytes": total_bytes,
            "latency_p95_ms": sorted(latencies)[min(len(latencies) - 1, int((len(latencies) - 1) * 0.95))] if latencies else None,
            "third_party_api_cost_usd": 0.0,
        },
        "production_integration": False,
        "qualification": "experiment_only_no_fresh_cohort_consumed",
        "claim_boundary": "Discovery only; sitemap/feed/JSON-LD observations do not directly publish jobs or company updates.",
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
