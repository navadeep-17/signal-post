#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_jobs import (  # noqa: E402
    build_job_observation,
    career_link_candidates,
    extract_structured_job_postings,
)
from norway_company_agent.evidence import utc_now  # noqa: E402
from norway_company_agent.website import (  # noqa: E402
    SAFE_OPENER,
    USER_AGENT,
    _registered_domain,
    _robots_allowed,
    assert_public_url,
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fetch_html(url: str, *, root_domain: str, timeout: float, max_bytes: int = 750_000) -> tuple[dict | None, dict]:
    ops = {"requests": 0, "bytes": 0, "latencies_ms": []}
    try:
        assert_public_url(url)
        if not _robots_allowed(url, timeout):
            ops["requests"] += 1
            return None, ops
        ops["requests"] += 1
        started = time.monotonic()
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
        with SAFE_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            elapsed = int((time.monotonic() - started) * 1000)
            final_url = response.geturl()
            content_type = response.headers.get("content-type", "")
        ops["requests"] += 1
        ops["bytes"] += len(raw)
        ops["latencies_ms"].append(elapsed)
        if len(raw) > max_bytes or "html" not in content_type.casefold():
            return None, ops
        assert_public_url(final_url)
        if _registered_domain(final_url) != root_domain:
            return None, ops
        return {
            "url": final_url,
            "html": raw.decode("utf-8", errors="replace"),
            "content_sha256": hashlib.sha256(raw).hexdigest(),
            "retrieved_at": utc_now(),
        }, ops
    except (ValueError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None, ops


def process_profile(profile: dict, *, timeout: float, max_career_pages: int) -> tuple[list[dict], dict]:
    result = {
        "organisation_number": str(profile.get("organisation_number") or ""),
        "eligible": False,
        "career_links": 0,
        "career_pages_fetched": 0,
        "structured_postings": 0,
        "accepted_jobs": 0,
        "rejected_job_identity": 0,
        "requests": 0,
        "bytes": 0,
        "latencies_ms": [],
    }
    website = (profile.get("evidence") or {}).get("website") or {}
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return [], result
    homepage = str(value.get("final_url") or website.get("source_url") or "").strip()
    if not homepage:
        return [], result

    result["eligible"] = True
    root_domain = _registered_domain(homepage)
    home, ops = fetch_html(homepage, root_domain=root_domain, timeout=timeout)
    result["requests"] += ops["requests"]
    result["bytes"] += ops["bytes"]
    result["latencies_ms"].extend(ops["latencies_ms"])
    if not home:
        return [], result

    pages = [home]
    links = career_link_candidates(home["url"], home["html"], limit=max_career_pages)
    result["career_links"] = len(links)
    for url in links:
        page, page_ops = fetch_html(url, root_domain=root_domain, timeout=timeout)
        result["requests"] += page_ops["requests"]
        result["bytes"] += page_ops["bytes"]
        result["latencies_ms"].extend(page_ops["latencies_ms"])
        if page:
            pages.append(page)
            result["career_pages_fetched"] += 1

    observations: list[dict] = []
    for page in pages:
        postings = extract_structured_job_postings(page["html"], base_url=page["url"])
        result["structured_postings"] += len(postings)
        for index, posting in enumerate(postings):
            observation = build_job_observation(
                profile,
                source_url=page["url"],
                retrieved_at=page["retrieved_at"],
                content_sha256=page["content_sha256"],
                posting=posting,
                index=index,
            )
            if observation:
                observations.append(observation)
                result["accepted_jobs"] += 1
            else:
                result["rejected_job_identity"] += 1
    deduped = {item["id"]: item for item in observations}
    return list(deduped.values()), result


def percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract high-precision structured jobs from exact company-owned sites.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--max-career-pages", type=int, default=2, choices=(1, 2))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.profiles))
    all_observations: list[dict] = []
    results: list[dict] = []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(process_profile, profile, timeout=args.timeout, max_career_pages=args.max_career_pages): profile
            for profile in rows
        }
        for future in as_completed(futures):
            observations, result = future.result()
            all_observations.extend(observations)
            results.append(result)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in all_observations), encoding="utf-8")

    latencies = [value for result in results for value in result["latencies_ms"]]
    report = {
        "connector": "exact_company_site_structured_jobs_v1",
        "profiles": len(rows),
        "eligible_exact_sites": sum(int(item["eligible"]) for item in results),
        "career_links": sum(item["career_links"] for item in results),
        "career_pages_fetched": sum(item["career_pages_fetched"] for item in results),
        "structured_postings": sum(item["structured_postings"] for item in results),
        "accepted_jobs": sum(item["accepted_jobs"] for item in results),
        "rejected_job_identity": sum(item["rejected_job_identity"] for item in results),
        "requests": sum(item["requests"] for item in results),
        "bytes": sum(item["bytes"] for item in results),
        "request_latency_ms": {"p50": percentile(latencies, 0.5), "p95": percentile(latencies, 0.95)},
        "wall_runtime_ms": int((time.monotonic() - started) * 1000),
        "third_party_cost_usd": 0.0,
        "search_api_requests": 0,
        "claim_boundary": "Only JSON-LD JobPosting records whose hiringOrganization matches the exact verified legal company are published. A generic careers page does not become a job claim.",
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
