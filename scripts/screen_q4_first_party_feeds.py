#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.final_site_discovery import BOUNDED_SAFE_OPENER, _robots_allowed  # noqa: E402
from norway_company_agent.first_party_feed import feed_candidate_urls, parse_company_feed  # noqa: E402
from norway_company_agent.website import USER_AGENT, assert_public_url  # noqa: E402


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _verified_site(profile: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    url = str(value.get("final_url") or website.get("source_url") or "").strip()
    if website.get("status") != "available" or not assessment.get("publishable") or not url:
        return None
    return url, website


def _fetch_feed(url: str, *, timeout: float, max_bytes: int) -> tuple[dict[str, Any], dict[str, int]]:
    metrics = {"logical_requests": 0, "bytes": 0, "latency_ms": 0}
    try:
        assert_public_url(url)
    except ValueError as exc:
        return {"status": "blocked", "reason": str(exc)}, metrics

    allowed, robots_requests = _robots_allowed(url, timeout)
    metrics["logical_requests"] += robots_requests
    if not allowed:
        return {"status": "blocked", "reason": "robots.txt disallows this user agent"}, metrics

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml;q=0.9,*/*;q=0.1",
        },
    )
    started = time.monotonic()
    metrics["logical_requests"] += 1
    try:
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            final_url = response.geturl()
            assert_public_url(final_url)
            content_type = str(response.headers.get("content-type", ""))
        metrics["latency_ms"] = int((time.monotonic() - started) * 1000)
        metrics["bytes"] = len(raw)
        if len(raw) > max_bytes:
            return {"status": "blocked", "reason": "feed exceeds byte limit", "final_url": final_url}, metrics
        return {
            "status": "available",
            "final_url": final_url,
            "content_type": content_type,
            "content_sha256": hashlib.sha256(raw).hexdigest(),
            "raw": raw,
        }, metrics
    except urllib.error.HTTPError as exc:
        metrics["latency_ms"] = int((time.monotonic() - started) * 1000)
        status = "not_found" if exc.code in {404, 410} else "source_error"
        return {"status": status, "reason": f"HTTP {exc.code}"}, metrics
    except Exception as exc:
        metrics["latency_ms"] = int((time.monotonic() - started) * 1000)
        return {"status": "source_error", "reason": f"{type(exc).__name__}: {str(exc)[:180]}"}, metrics


def screen(
    profiles: list[dict[str, Any]],
    *,
    timeout: float,
    candidates_per_site: int,
    max_bytes: int,
    max_entries: int,
) -> dict[str, Any]:
    verified: list[tuple[dict[str, Any], str]] = []
    for profile in profiles:
        site = _verified_site(profile)
        if site:
            verified.append((profile, site[0]))

    outcomes: list[dict[str, Any]] = []
    total_requests = 0
    total_bytes = 0
    sites_with_activity = 0
    dated_updates = 0

    for profile, verified_url in sorted(verified, key=lambda item: str(item[0].get("organisation_number") or "")):
        attempts: list[dict[str, Any]] = []
        accepted: dict[str, Any] | None = None
        for candidate_url in feed_candidate_urls(verified_url, limit=candidates_per_site):
            fetched, metrics = _fetch_feed(candidate_url, timeout=timeout, max_bytes=max_bytes)
            total_requests += metrics["logical_requests"]
            total_bytes += metrics["bytes"]
            attempt: dict[str, Any] = {
                "candidate_url": candidate_url,
                "fetch_status": fetched.get("status"),
                "logical_requests": metrics["logical_requests"],
                "bytes": metrics["bytes"],
                "latency_ms": metrics["latency_ms"],
            }
            if fetched.get("status") == "available":
                parsed = parse_company_feed(
                    fetched["raw"],
                    feed_url=str(fetched.get("final_url") or candidate_url),
                    verified_url=verified_url,
                    max_entries=max_entries,
                )
                attempt.update(
                    {
                        "final_url": fetched.get("final_url"),
                        "content_type": fetched.get("content_type"),
                        "content_sha256": fetched.get("content_sha256"),
                        "parse_status": parsed.get("status"),
                        "feed_type": parsed.get("feed_type"),
                        "entries": parsed.get("entries") or [],
                    }
                )
                if parsed.get("status") == "available" and parsed.get("entries"):
                    accepted = attempt
                    break
            else:
                attempt["reason"] = fetched.get("reason")
            attempts.append(attempt)
        if accepted is not None:
            attempts.append(accepted)
            sites_with_activity += 1
            dated_updates += len(accepted.get("entries") or [])

        outcomes.append(
            {
                "organisation_number": profile.get("organisation_number"),
                "legal_name": profile.get("name"),
                "verified_url": verified_url,
                "activity_feed_found": accepted is not None,
                "accepted_feed_url": (accepted or {}).get("final_url"),
                "dated_update_count": len((accepted or {}).get("entries") or []),
                "attempts": attempts,
            }
        )

    return {
        "profiles": len(profiles),
        "verified_websites": len(verified),
        "sites_with_dated_feed_activity": sites_with_activity,
        "dated_updates": dated_updates,
        "logical_requests": total_requests,
        "bytes": total_bytes,
        "candidates_per_site_max": candidates_per_site,
        "max_entries_per_feed": max_entries,
        "outcomes": outcomes,
        "policy": (
            "Consumed-only Q4 screen. Company identity comes only from the pre-existing exact verified website; "
            "feed entries must remain on that verified site and carry an explicit feed publication/update date."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen already-verified consumed company sites for strict dated RSS/Atom activity.")
    parser.add_argument("--input", required=True, help="Consumed profile JSONL")
    parser.add_argument("--report", required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--candidates-per-site", type=int, default=2, choices=range(1, 3), metavar="1..2")
    parser.add_argument("--max-bytes", type=int, default=500_000)
    parser.add_argument("--max-entries", type=int, default=5)
    args = parser.parse_args()

    if args.timeout <= 0 or args.max_bytes < 1 or args.max_entries < 1:
        parser.error("timeout, max-bytes and max-entries must be positive")

    report = screen(
        read_jsonl(Path(args.input)),
        timeout=args.timeout,
        candidates_per_site=args.candidates_per_site,
        max_bytes=args.max_bytes,
        max_entries=args.max_entries,
    )
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
