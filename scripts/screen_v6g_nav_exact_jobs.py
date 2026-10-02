#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.nav_exact_jobs import build_target_index, extract_exact_active_job, nominate_targets  # noqa: E402

NAV_BASE = "https://pam-stilling-feed.nav.no"
PUBLIC_TOKEN_URL = f"{NAV_BASE}/api/publicToken"
FEED_URL = f"{NAV_BASE}/api/v1/feed"
JWT_RE = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
USER_AGENT = "signalpost-v6g-nav-screen/1.0 (+https://github.com/navadeep-17/signal-post)"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _absolute_nav_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return f"{NAV_BASE}/{text.lstrip('/')}"


class PacedClient:
    def __init__(self, *, timeout: float, min_start_interval: float) -> None:
        self.timeout = timeout
        self.min_start_interval = min_start_interval
        self.last_start = 0.0
        self.requests = 0
        self.bytes = 0
        self.latencies_ms: list[int] = []
        self.errors: list[str] = []

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> tuple[bytes, dict[str, str]]:
        delay = self.min_start_interval - (time.monotonic() - self.last_start)
        if delay > 0:
            time.sleep(delay)
        self.last_start = time.monotonic()
        started = time.monotonic()
        self.requests += 1
        req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})}
        request = urllib.request.Request(url, headers=req_headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(8_000_000)
                response_headers = {str(key).casefold(): str(value) for key, value in response.headers.items()}
            self.bytes += len(raw)
            self.latencies_ms.append(int((time.monotonic() - started) * 1000))
            return raw, response_headers
        except Exception as exc:
            self.latencies_ms.append(int((time.monotonic() - started) * 1000))
            self.errors.append(f"{type(exc).__name__}: {str(exc)[:180]} @ {url}")
            raise


def public_token(client: PacedClient) -> str:
    raw, _ = client.get(PUBLIC_TOKEN_URL, headers={"Accept": "text/plain,application/json"})
    text = raw.decode("utf-8", errors="replace").strip()
    if text.startswith("{"):
        try:
            data = json.loads(text)
            token = str(data.get("token") or data.get("access_token") or "").strip()
            if token:
                return token
        except json.JSONDecodeError:
            pass
    match = JWT_RE.search(text)
    if not match:
        raise RuntimeError("NAV public token endpoint returned no JWT")
    return match.group(0)


def _newer(candidate: dict[str, Any], prior: dict[str, Any] | None) -> bool:
    if prior is None:
        return True
    new_time = str(candidate.get("modified") or "")
    old_time = str(prior.get("modified") or "")
    return new_time >= old_time


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen NAV vacancy feed for exact employer-org matches to retained Signalpost companies")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--lookback-days", type=int, default=185)
    parser.add_argument("--max-feed-pages", type=int, default=90)
    parser.add_argument("--max-detail-requests", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--min-start-interval", type=float, default=0.2)
    args = parser.parse_args()

    profiles = read_jsonl(Path(args.profiles))
    index = build_target_index(profiles)
    if not index["by_target"]:
        raise SystemExit("No target companies available")

    client = PacedClient(timeout=args.timeout, min_start_interval=args.min_start_interval)
    started = time.monotonic()
    token = public_token(client)
    auth = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    since = format_datetime(datetime.now(timezone.utc) - timedelta(days=args.lookback_days), usegmt=True)

    next_url = FEED_URL
    feed_pages = 0
    feed_items = 0
    active_headers = 0
    name_nominated_headers = 0
    candidate_by_uuid: dict[str, dict[str, Any]] = {}
    exhausted = False

    for page_number in range(max(0, args.max_feed_pages)):
        headers = dict(auth)
        if page_number == 0:
            headers["If-Modified-Since"] = since
        try:
            raw, _ = client.get(next_url, headers=headers)
            page = json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                exhausted = True
                break
            raise
        feed_pages += 1
        items = page.get("items") if isinstance(page, dict) else None
        if not isinstance(items, list):
            raise RuntimeError("NAV feed page did not contain items[]")
        feed_items += len(items)

        for item in items:
            if not isinstance(item, dict):
                continue
            header = item.get("_feed_entry") or {}
            if not isinstance(header, dict):
                continue
            uuid = str(header.get("uuid") or item.get("id") or "").strip()
            if not uuid:
                continue
            status = str(header.get("status") or "").upper()
            if status == "ACTIVE":
                active_headers += 1
            business_name = header.get("businessName")
            nominations = nominate_targets(business_name, index) if business_name else []
            if nominations:
                name_nominated_headers += 1

            prior = candidate_by_uuid.get(uuid)
            if not nominations and prior is None:
                continue
            candidate = {
                "uuid": uuid,
                "status": status,
                "business_name": business_name or (prior or {}).get("business_name"),
                "municipal": header.get("municipal") or (prior or {}).get("municipal"),
                "modified": header.get("sistEndret") or item.get("date_modified") or "",
                "detail_url": _absolute_nav_url(item.get("url") or (prior or {}).get("detail_url")),
                "nominated_targets": sorted(set(nominations) | set((prior or {}).get("nominated_targets") or [])),
            }
            if _newer(candidate, prior):
                candidate_by_uuid[uuid] = candidate
            elif nominations and prior is not None:
                prior["nominated_targets"] = sorted(set(prior.get("nominated_targets") or []) | set(nominations))

        raw_next = page.get("next_url") if isinstance(page, dict) else None
        if not raw_next:
            exhausted = True
            next_url = ""
            break
        next_url = _absolute_nav_url(raw_next)

    candidates = [
        row for row in candidate_by_uuid.values()
        if row.get("status") == "ACTIVE" and row.get("detail_url") and row.get("nominated_targets")
    ]
    candidates.sort(key=lambda row: (str(row.get("modified") or ""), str(row.get("uuid") or "")), reverse=True)

    jobs: list[dict[str, Any]] = []
    detail_audit: list[dict[str, Any]] = []
    seen_job_uuid: set[str] = set()
    for candidate in candidates[: max(0, args.max_detail_requests)]:
        detail_url = str(candidate["detail_url"])
        try:
            raw, _ = client.get(detail_url, headers=auth)
            detail = json.loads(raw)
            job = extract_exact_active_job(
                detail,
                index,
                nominated_targets=list(candidate.get("nominated_targets") or []),
            )
            audit = {
                **candidate,
                "detail_sha256": hashlib.sha256(raw).hexdigest(),
                "exact_match": bool(job),
            }
            if job:
                public_url = f"https://arbeidsplassen.nav.no/stillinger/stilling/{job.get('uuid') or candidate['uuid']}"
                row = {
                    **job,
                    "nav_detail_url": detail_url,
                    "public_job_url": public_url,
                    "detail_sha256": audit["detail_sha256"],
                    "nominated_business_name": candidate.get("business_name"),
                    "publication_enabled": False,
                    "publication_evidence": False,
                }
                uuid = str(row.get("uuid") or candidate["uuid"])
                if uuid not in seen_job_uuid:
                    seen_job_uuid.add(uuid)
                    jobs.append(row)
            detail_audit.append(audit)
        except Exception as exc:
            detail_audit.append({**candidate, "exact_match": False, "error": f"{type(exc).__name__}: {str(exc)[:180]}"})

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in jobs:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    audit_path = Path(args.audit)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("w", encoding="utf-8") as handle:
        for target_org, target in sorted(index["by_target"].items()):
            handle.write(json.dumps({
                **target,
                "jobs": [row for row in jobs if row["target_org"] == target_org],
            }, ensure_ascii=False, separators=(",", ":")) + "\n")

    matched_companies = sorted({row["target_org"] for row in jobs})
    report = {
        "experiment": "V6g NAV exact-org active jobs screen",
        "publication_enabled": False,
        "target_companies": len(index["by_target"]),
        "retained_subunit_org_numbers": max(0, len(index["org_to_target"]) - len(index["by_target"])),
        "lookback_days": args.lookback_days,
        "feed_pages": feed_pages,
        "feed_items": feed_items,
        "feed_exhausted_within_ceiling": exhausted,
        "next_url_remaining": bool(next_url),
        "active_headers_seen": active_headers,
        "name_nominated_headers": name_nominated_headers,
        "unique_active_candidate_vacancies": len(candidates),
        "detail_requests_attempted": min(len(candidates), max(0, args.max_detail_requests)),
        "exact_active_jobs": len(jobs),
        "companies_with_exact_active_job": len(matched_companies),
        "matched_company_orgs": matched_companies,
        "logical_requests": client.requests,
        "conservative_request_charge": client.requests * 2,
        "bytes": client.bytes,
        "wall_runtime_seconds": round(time.monotonic() - started, 3),
        "third_party_api_cost_usd": 0.0,
        "wrong_company_publications": 0,
        "identity_rule": "Only NAV detail employer.orgnr equal to target main org or an already-retained BRREG subunit org is accepted; name matching only nominates detail requests.",
        "rights_basis": "Official NAV Job Vacancy Feed documentation states anyone may use the API free of charge subject to NAV API terms; public rotating token used for experiment.",
        "errors": client.errors,
        "detail_audit": detail_audit,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "detail_audit"}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
