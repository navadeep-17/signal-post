#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.final_site_discovery import fetch_bounded_homepage  # noqa: E402
from norway_company_agent.job_surface_signal import same_company_host  # noqa: E402

PATH_CANDIDATES = (
    "karriere/",
    "jobb/",
    "ledige-stillinger/",
    "careers/",
    "jobs/",
)
STRONG_HIRING_MARKERS = (
    "ledige stillinger",
    "ledige-stillinger",
    "jobb hos oss",
    "jobbe hos oss",
    "søk jobb",
    "sok jobb",
    "karriere",
    "careers",
    "open positions",
    "open roles",
    "open vacancies",
    "vacancies",
    "join our team",
    "work with us",
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


def verified_website(profile: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    url = str(value.get("final_url") or website.get("source_url") or "").strip()
    if website.get("status") != "available" or not assessment.get("publishable"):
        return None
    if not url.startswith(("http://", "https://")):
        return None
    return url, website


def candidate_urls(verified_url: str) -> list[tuple[str, str]]:
    parsed = urllib.parse.urlparse(verified_url)
    origin = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/", "", "", ""))
    return [(path.rstrip("/"), urllib.parse.urljoin(origin, path)) for path in PATH_CANDIDATES]


def _surface_signal(record: dict[str, Any], verified_url: str) -> dict[str, Any]:
    if record.get("status") != "available":
        return {"qualified": False, "reason": str(record.get("status") or "unavailable")}
    value = record.get("value") or {}
    final_url = str(value.get("final_url") or record.get("source_url") or "").strip()
    if not final_url or not same_company_host(final_url, verified_url):
        return {"qualified": False, "reason": "outside_verified_company_host"}

    verified_path = urllib.parse.urlparse(verified_url).path.rstrip("/") or "/"
    final_path = urllib.parse.urlparse(final_url).path.rstrip("/") or "/"
    if final_path == verified_path:
        return {"qualified": False, "reason": "redirected_to_verified_homepage"}

    text = "\n".join(
        str(value.get(key) or "")
        for key in ("title", "description", "identity_text_excerpt", "main_text_excerpt")
    ).casefold()
    markers = sorted({marker for marker in STRONG_HIRING_MARKERS if marker in text})
    jobs = [item for item in (value.get("job_listing_candidates") or []) if isinstance(item, dict)]
    hiring = value.get("active_hiring_signal") or {}
    active_count = int(hiring.get("active_vacancy_count") or 0)
    qualified = bool(markers or jobs or active_count > 0)
    return {
        "qualified": qualified,
        "reason": "strong_hiring_surface_evidence" if qualified else "no_strong_hiring_evidence",
        "final_url": final_url,
        "title": str(value.get("title") or "")[:300],
        "markers": markers,
        "job_listing_candidates": len(jobs),
        "active_vacancy_count": active_count,
        "content_sha256": record.get("content_sha256"),
    }


def screen_profiles(
    profiles: list[dict[str, Any]],
    *,
    timeout: float,
    fetcher: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = fetch_bounded_homepage,
) -> dict[str, Any]:
    exact_sites: list[tuple[dict[str, Any], str]] = []
    for profile in profiles:
        verified = verified_website(profile)
        if verified:
            exact_sites.append((profile, verified[0]))

    path_attempts: Counter[str] = Counter()
    path_qualified_companies: dict[str, set[str]] = {path.rstrip("/"): set() for path in PATH_CANDIDATES}
    total_requests = 0
    total_bytes = 0
    attempts: list[dict[str, Any]] = []
    qualified_orgs: set[str] = set()

    for profile, verified_url in exact_sites:
        org = str(profile.get("organisation_number") or "")
        for path_name, url in candidate_urls(verified_url):
            record, metrics = fetcher(url, source_type="q5_common_path_hiring_screen", timeout=timeout)
            requests = int(metrics.get("requests") or 0)
            total_requests += requests
            total_bytes += int(metrics.get("bytes") or 0)
            path_attempts[path_name] += 1
            signal = _surface_signal(record, verified_url)
            if signal.get("qualified"):
                qualified_orgs.add(org)
                path_qualified_companies[path_name].add(org)
            attempts.append(
                {
                    "organisation_number": org,
                    "company_name": profile.get("name") or profile.get("legal_name"),
                    "verified_url": verified_url,
                    "candidate_path": path_name,
                    "candidate_url": url,
                    "requests": requests,
                    "status": record.get("status"),
                    **signal,
                }
            )

    path_results = {
        path: {
            "attempted_companies": path_attempts[path],
            "qualified_companies": len(path_qualified_companies[path]),
            "organisation_numbers": sorted(path_qualified_companies[path]),
        }
        for path in sorted(path_attempts)
    }
    ranked = sorted(path_results, key=lambda path: (-path_results[path]["qualified_companies"], path))
    return {
        "status": "SCREEN_ONLY_NO_PRODUCTION_CHANGE",
        "fresh_qualification": False,
        "profiles": len(profiles),
        "verified_sites": len(exact_sites),
        "candidate_paths": [path.rstrip("/") for path in PATH_CANDIDATES],
        "network_requests": total_requests,
        "bytes_received": total_bytes,
        "qualified_companies_any_path": len(qualified_orgs),
        "qualified_organisation_numbers": sorted(qualified_orgs),
        "path_results": path_results,
        "ranked_paths": ranked,
        "attempts": attempts,
        "production_decision": "UNDECIDED_SCREEN_ONLY",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Screen deterministic same-host hiring paths on consumed exact websites.")
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
