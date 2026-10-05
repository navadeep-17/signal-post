#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.final_site_discovery import BOUNDED_SAFE_OPENER, _robots_allowed  # noqa: E402
from norway_company_agent.job_surface_signal import same_company_host  # noqa: E402
from norway_company_agent.website import USER_AGENT, assert_public_url  # noqa: E402

STRONG_MARKERS = (
    "ledige stillinger",
    "ledige-stillinger",
    "jobb hos oss",
    "jobbe hos oss",
    "søk jobb",
    "sok jobb",
    "søk stilling",
    "sok stilling",
    "karriere",
    "career",
    "careers",
    "jobs",
    "vacancies",
    "open positions",
    "open roles",
    "join our team",
    "work with us",
    "career opportunities",
)
KNOWN_RECRUITMENT_HOSTS = (
    "teamtailor.com",
    "jobylon.com",
    "webcruiter.com",
    "webcruiter.no",
    "easycruit.com",
    "reachmee.com",
    "recman.no",
    "jobbnorge.no",
    "talentspace.io",
    "arbeidsplassen.nav.no",
    "finn.no",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        rows.append(value)
    return rows


def verified_website(profile: dict[str, Any]) -> str | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    url = str(value.get("final_url") or website.get("source_url") or "").strip()
    if website.get("status") != "available" or not assessment.get("publishable"):
        return None
    return url if url.startswith(("http://", "https://")) else None


def _host(url: str) -> str:
    try:
        return (urllib.parse.urlparse(url).hostname or "").casefold().rstrip(".")
    except ValueError:
        return ""


def _known_recruitment_host(host: str) -> str | None:
    normalized = host.casefold().rstrip(".")
    return next(
        (candidate for candidate in KNOWN_RECRUITMENT_HOSTS if normalized == candidate or normalized.endswith("." + candidate)),
        None,
    )


def extract_external_recruitment_links(*, html: str, final_url: str) -> list[dict[str, Any]]:
    """Return external recruitment surfaces explicitly declared by an exact homepage.

    This is source-selection only. A candidate is not a company-owned careers page and is
    not an active-vacancy claim. We retain it only when the exact homepage itself declares
    the external URL via an anchor/iframe and either strong hiring language or a known ATS
    host is present.
    """
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node, attribute, kind in [
        *( (item, "href", "anchor") for item in soup.select("a[href]") ),
        *( (item, "src", "iframe") for item in soup.select("iframe[src]") ),
    ]:
        raw = str(node.get(attribute) or "").strip()
        if not raw:
            continue
        absolute = urllib.parse.urljoin(final_url, raw)
        try:
            parsed = urllib.parse.urlparse(absolute)
        except ValueError:
            continue
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        normalized = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, ""))
        if normalized in seen or same_company_host(normalized, final_url):
            continue

        text_parts = [
            node.get_text(" ", strip=True),
            str(node.get("title") or ""),
            str(node.get("aria-label") or ""),
            urllib.parse.unquote(parsed.path),
            urllib.parse.unquote(parsed.query),
        ]
        context = " ".join(" ".join(str(part).split()) for part in text_parts if str(part or "").strip())
        folded = context.casefold()
        markers = sorted({marker for marker in STRONG_MARKERS if marker in folded})
        known_host = _known_recruitment_host(parsed.hostname)
        if not markers and not known_host:
            continue
        seen.add(normalized)
        rows.append(
            {
                "url": normalized,
                "host": parsed.hostname.casefold(),
                "element": kind,
                "anchor_text": " ".join(node.get_text(" ", strip=True).split())[:300] or None,
                "markers": markers,
                "known_recruitment_host": known_host,
                "evidence_span": f"Exact homepage declared external recruitment surface: {context or normalized}"[:700],
            }
        )
    rows.sort(key=lambda item: (0 if item.get("known_recruitment_host") else 1, item["host"], item["url"]))
    return rows[:20]


def fetch_homepage_recruitment_links(
    verified_url: str,
    *,
    timeout: float = 6.0,
    max_bytes: int = 750_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    metrics: dict[str, Any] = {"requests": 0, "bytes": 0, "latencies_ms": []}
    assert_public_url(verified_url)
    allowed, robots_requests = _robots_allowed(verified_url, timeout)
    metrics["requests"] += int(robots_requests)
    if not allowed:
        return {"status": "blocked", "source_url": verified_url, "candidates": []}, metrics

    request = urllib.request.Request(
        verified_url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    started = time.monotonic()
    metrics["requests"] += 1
    try:
        with BOUNDED_SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            final_url = response.geturl()
            content_type = response.headers.get("content-type", "")
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        metrics["bytes"] += len(raw)
        assert_public_url(final_url)
        if len(raw) > max_bytes:
            return {"status": "blocked", "source_url": final_url, "reason": "homepage_exceeds_byte_limit", "candidates": []}, metrics
        if "html" not in content_type.casefold():
            return {"status": "source_error", "source_url": final_url, "reason": "unsupported_content_type", "candidates": []}, metrics
        if not same_company_host(final_url, verified_url):
            return {"status": "rejected", "source_url": final_url, "reason": "redirect_outside_verified_company_host", "candidates": []}, metrics
        html = raw.decode("utf-8", errors="replace")
        candidates = extract_external_recruitment_links(html=html, final_url=final_url)
        return {
            "status": "available" if candidates else "not_found",
            "source_url": final_url,
            "content_sha256": hashlib.sha256(raw).hexdigest(),
            "candidates": candidates,
        }, metrics
    except Exception as exc:
        metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
        return {
            "status": "source_error",
            "source_url": verified_url,
            "reason": f"{type(exc).__name__}: {str(exc)[:180]}",
            "candidates": [],
        }, metrics


def screen_profiles(profiles: list[dict[str, Any]], *, timeout: float = 6.0) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    total_requests = 0
    total_bytes = 0
    exact_sites = 0
    companies_with_candidates = 0
    total_candidates = 0
    known_ats_candidates = 0

    for profile in profiles:
        verified_url = verified_website(profile)
        if not verified_url:
            continue
        exact_sites += 1
        record, metrics = fetch_homepage_recruitment_links(verified_url, timeout=timeout)
        candidates = list(record.get("candidates") or [])
        total_requests += int(metrics.get("requests") or 0)
        total_bytes += int(metrics.get("bytes") or 0)
        total_candidates += len(candidates)
        known_ats_candidates += sum(bool(item.get("known_recruitment_host")) for item in candidates)
        companies_with_candidates += int(bool(candidates))
        attempts.append(
            {
                "organisation_number": str(profile.get("organisation_number") or ""),
                "company_name": profile.get("name") or profile.get("legal_name"),
                "verified_url": verified_url,
                "status": record.get("status"),
                "source_url": record.get("source_url"),
                "content_sha256": record.get("content_sha256"),
                "requests": int(metrics.get("requests") or 0),
                "candidate_count": len(candidates),
                "candidates": candidates,
                "reason": record.get("reason"),
            }
        )

    return {
        "status": "SCREEN_ONLY_NO_PRODUCTION_CHANGE",
        "fresh_qualification": False,
        "profiles": len(profiles),
        "verified_sites": exact_sites,
        "network_requests": total_requests,
        "bytes_received": total_bytes,
        "companies_with_external_recruitment_candidates": companies_with_candidates,
        "external_recruitment_candidates": total_candidates,
        "known_ats_candidates": known_ats_candidates,
        "attempts": attempts,
        "production_decision": "UNDECIDED_SCREEN_ONLY",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Screen exact consumed homepages for company-declared external recruitment links.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--expect-profiles", type=int)
    parser.add_argument("--expect-verified-sites", type=int)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    profiles = read_jsonl(Path(args.profiles))
    if args.expect_profiles is not None and len(profiles) != args.expect_profiles:
        raise SystemExit(f"expected {args.expect_profiles} profiles, got {len(profiles)}")
    report = screen_profiles(profiles, timeout=args.timeout)
    if args.expect_verified_sites is not None and report["verified_sites"] != args.expect_verified_sites:
        raise SystemExit(f"expected {args.expect_verified_sites} exact sites, got {report['verified_sites']}")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
