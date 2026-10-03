#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from norway_company_agent.first_party_updates import qualify_first_party_update  # noqa: E402
from norway_company_agent.structured_first_party import verified_site_url  # noqa: E402
from norway_company_agent.website import _registered_domain, _robots_allowed  # noqa: E402
from run_structured_first_party_discovery import discover_profile, fetch_document  # noqa: E402

MAX_DISCOVERY_REQUESTS_PER_SITE = 5
MAX_DESTINATIONS_PER_SITE = 2
MAX_DESTINATION_REQUEST_CHARGE = 2  # robots + page


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def same_registered_domain(left: str, right: str) -> bool:
    try:
        a = _registered_domain(left)
        b = _registered_domain(right)
        return bool(a and b and a.casefold() == b.casefold())
    except Exception:
        return False


def candidate_priority(row: dict[str, Any]) -> tuple[int, int, str]:
    kind = str(row.get("surface_kind") or "")
    via = str(row.get("discovered_via") or "")
    # Structured article metadata on a specific URL is the strongest nomination,
    # followed by feed entries; sitemap URLs remain useful but weaker nominations.
    kind_rank = {"structured_article": 0, "news_or_article": 1}.get(kind, 9)
    via_rank = {"jsonld": 0, "rss_or_atom": 1, "sitemap": 2}.get(via, 9)
    return kind_rank, via_rank, str(row.get("url") or "")


def screen_profile(profile: dict[str, Any], *, timeout: float, as_of: date) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    verified = verified_site_url(profile)
    if not verified:
        return None, {"requests": 0, "request_ceiling": 0, "reason": "no_verified_site"}

    discovery, discovery_metrics = discover_profile(profile, timeout=timeout)
    requests = int(discovery_metrics.get("requests") or 0)
    bytes_received = int(discovery_metrics.get("bytes") or 0)
    candidates = [] if discovery is None else [
        row for row in (discovery.get("surface_candidates") or [])
        if str(row.get("surface_kind") or "") in {"structured_article", "news_or_article"}
    ]

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in sorted(candidates, key=candidate_priority):
        url = str(row.get("url") or "")
        if not url or url in seen or not same_registered_domain(url, verified):
            continue
        seen.add(url)
        deduped.append(row)
        if len(deduped) >= MAX_DESTINATIONS_PER_SITE:
            break

    attempts: list[dict[str, Any]] = []
    for candidate in deduped:
        url = str(candidate["url"])
        # Conservative accounting: one robots request plus one destination request.
        requests += 1
        try:
            allowed = _robots_allowed(url, timeout)
        except Exception:
            allowed = False
        if not allowed:
            attempts.append({"candidate": candidate, "status": "robots_disallowed", "publishable": False})
            continue

        body, operation = fetch_document(url, timeout=timeout, accept="text/html,application/xhtml+xml")
        requests += 1
        bytes_received += int(operation.get("bytes") or 0)
        final_url = str(operation.get("final_url") or url)
        if body is None or not same_registered_domain(final_url, verified):
            attempts.append({
                "candidate": candidate,
                "page_url": final_url,
                "status": "fetch_failed_or_cross_domain",
                "publishable": False,
                "http_status": operation.get("status"),
                "error": operation.get("error"),
            })
            continue

        qualified = qualify_first_party_update(
            verified_company_url=verified,
            page_url=final_url,
            html=body,
            content_sha256=str(operation.get("content_sha256") or ""),
            as_of=as_of,
        )
        attempts.append({
            "candidate": candidate,
            "page_url": final_url,
            "http_status": operation.get("status"),
            **qualified,
        })

    publishable = [row for row in attempts if row.get("publishable")]
    result = {
        "organisation_number": str(profile.get("organisation_number") or ""),
        "verified_website": verified,
        "discovery_candidates": len(candidates),
        "destination_attempts": attempts,
        "publishable_updates": publishable,
        "claim_boundary": (
            "Only independently fetched, same-company, specific destination pages with an explicit page-level publication date "
            "and bounded article text may publish as company-authored updates. Sitemap lastmod/feed dates nominate only."
        ),
    }
    ceiling = MAX_DISCOVERY_REQUESTS_PER_SITE + MAX_DESTINATIONS_PER_SITE * MAX_DESTINATION_REQUEST_CHARGE
    assert requests <= ceiling, {"requests": requests, "ceiling": ceiling, "organisation_number": result["organisation_number"]}
    return result, {"requests": requests, "request_ceiling": ceiling, "bytes": bytes_received}


def main() -> None:
    parser = argparse.ArgumentParser(description="V9 M4 reused-site dated first-party update qualification screen.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--as-of", default="2026-10-03")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    as_of = date.fromisoformat(args.as_of)

    profiles = read_jsonl(Path(args.profiles))
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    total_requests = 0
    total_ceiling = 0
    total_bytes = 0
    attempted = 0

    for profile in profiles:
        if attempted >= args.limit:
            break
        if not verified_site_url(profile):
            counts["unverified_site_skipped"] += 1
            continue
        attempted += 1
        row, metrics = screen_profile(profile, timeout=args.timeout, as_of=as_of)
        total_requests += int(metrics.get("requests") or 0)
        total_ceiling += int(metrics.get("request_ceiling") or 0)
        total_bytes += int(metrics.get("bytes") or 0)
        if row is None:
            counts["no_observation"] += 1
            continue
        rows.append(row)
        if row["discovery_candidates"]:
            counts["companies_with_article_candidates"] += 1
        if row["publishable_updates"]:
            counts["companies_with_publishable_updates"] += 1
        counts["publishable_updates"] += len(row["publishable_updates"])
        for attempt in row["destination_attempts"]:
            counts[f"destination_{attempt.get('status') or 'unknown'}"] += 1

    write_jsonl(Path(args.output), rows)
    report = {
        "schema_version": "signalpost-v9-m4-dated-first-party-screen-v1",
        "input_profiles": len(profiles),
        "verified_sites_attempted": attempted,
        "observations": len(rows),
        "counts": dict(sorted(counts.items())),
        "operations": {
            "requests": total_requests,
            "request_ceiling": total_ceiling,
            "bytes": total_bytes,
            "third_party_api_cost_usd": 0.0,
        },
        "production_integration": False,
        "qualification": "reused_sites_only_no_fresh_cohort_consumed",
        "claim_boundary": (
            "Sitemap/feed/JSON-LD discovery is nomination only. Publication requires an independently fetched same-company "
            "specific page with explicit page-level publication date, specific title, content hash and bounded article text."
        ),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
