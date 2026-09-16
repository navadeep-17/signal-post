#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

UA = "SignalpostResearchPOC/1.0 (https://builderr.ai; bounded source-coverage screen)"
MAX_HTML_BYTES = 2_000_000


def slug(value: object) -> str:
    text = str(value or "").translate(
        str.maketrans({"ø": "o", "å": "a", "æ": "ae", "Ø": "O", "Å": "A", "Æ": "AE"})
    )
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return "-".join(re.findall(r"[a-z0-9]+", text))


def extract_aggregate_rating(raw: bytes) -> tuple[float, int] | None:
    soup = BeautifulSoup(raw, "html.parser")
    for node in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(node.string or node.get_text() or "{}")
        except Exception:
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            rating = item.get("aggregateRating")
            if not isinstance(rating, dict):
                continue
            value = rating.get("ratingValue")
            count = rating.get("ratingCount") or rating.get("reviewCount")
            if value is None or count is None:
                continue
            try:
                numeric_value = float(value)
                numeric_count = int(count)
            except (TypeError, ValueError):
                continue
            if 0 < numeric_value <= 5 and numeric_count > 0:
                return numeric_value, numeric_count
    return None


def screen(profile: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    org = str(profile.get("organisation_number") or "")
    name = str(profile.get("name") or "").strip()
    url = f"https://www.fagfolkguiden.no/bedrift/{slug(name)}-{org}"
    started = time.monotonic()
    result: dict[str, Any] = {
        "organisation_number": org,
        "name": name,
        "url": url,
        "request_count": 1,
    }
    try:
        request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_HTML_BYTES + 1)
            status = int(getattr(response, "status", 200) or 200)
            content_type = str(response.headers.get("content-type") or "")
        result["latency_ms"] = int((time.monotonic() - started) * 1000)
        result["http_status"] = status
        result["content_type"] = content_type
        result["bytes"] = len(raw)
        if len(raw) > MAX_HTML_BYTES:
            return {**result, "status": "response_too_large"}

        soup = BeautifulSoup(raw, "html.parser")
        text = soup.get_text(" ", strip=True)
        digits = re.sub(r"\D", "", text)
        name_match = bool(name) and name.casefold() in text.casefold()
        org_match = bool(org) and org in digits
        result["exact_name_in_page"] = name_match
        result["exact_org_in_page"] = org_match
        if not (name_match and org_match):
            return {**result, "status": "identity_mismatch"}

        rating = extract_aggregate_rating(raw)
        if rating is None:
            return {**result, "status": "exact_unrated"}
        value, count = rating
        return {
            **result,
            "status": "exact_rated",
            "rating": value,
            "review_count": count,
        }
    except urllib.error.HTTPError as exc:
        return {
            **result,
            "status": f"http_{exc.code}",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "error": f"HTTPError: {exc}",
        }
    except Exception as exc:
        return {
            **result,
            "status": "error",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "error": f"{type(exc).__name__}: {str(exc)[:180]}",
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bounded H2h source-coverage screen for exact Fagfolkguiden pages and aggregate ratings."
    )
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--min-start-interval", type=float, default=1.5)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.min_start_interval < 0:
        parser.error("--min-start-interval cannot be negative")

    profiles = [
        json.loads(line)
        for line in Path(args.profiles).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ][: args.limit]

    audit: list[dict[str, Any]] = []
    last_start = 0.0
    started = time.monotonic()
    for profile in profiles:
        remaining = args.min_start_interval - (time.monotonic() - last_start)
        if remaining > 0:
            time.sleep(remaining)
        last_start = time.monotonic()
        audit.append(screen(profile, timeout=args.timeout))

    Path(args.audit).parent.mkdir(parents=True, exist_ok=True)
    Path(args.audit).write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in audit),
        encoding="utf-8",
    )
    statuses = Counter(str(row.get("status") or "unknown") for row in audit)
    exact_pages = sum(row.get("status") in {"exact_rated", "exact_unrated"} for row in audit)
    rated = int(statuses.get("exact_rated") or 0)
    requests = sum(int(row.get("request_count") or 0) for row in audit)
    report = {
        "experiment": "h2h_fagfolkguiden_review_source_coverage_v1",
        "profiles": len(profiles),
        "requests": requests,
        "status_counts": dict(sorted(statuses.items())),
        "exact_pages": exact_pages,
        "exact_page_coverage": exact_pages / len(profiles) if profiles else 0.0,
        "rated_companies": rated,
        "rated_company_coverage": rated / len(profiles) if profiles else 0.0,
        "runtime_seconds": round(time.monotonic() - started, 3),
        "third_party_cost_usd": 0.0,
        "publication_enabled": False,
        "rights_status": "review_required",
        "claim_boundary": (
            "Coverage screen only. No observations are published. A hit means an exact-name + exact-org "
            "Fagfolkguiden page exposed a valid aggregateRating in JSON-LD at retrieval time."
        ),
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
