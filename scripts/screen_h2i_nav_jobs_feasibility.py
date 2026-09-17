#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any

import requests

NAV_BASE = "https://pam-stilling-feed.nav.no"
BRREG_SUBUNITS = "https://data.brreg.no/enhetsregisteret/api/underenheter"
LEGAL_SUFFIXES = {
    "AS", "ASA", "ANS", "DA", "ENK", "NUF", "SA", "BA", "KS", "IKS", "HF", "KF", "SF"
}
JWT_RE = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def _org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if len(digits) == 9 else None


def _name(value: Any) -> str:
    text = str(value or "").upper()
    text = re.sub(r"[^A-Z0-9ÆØÅ]+", " ", text)
    words = [w for w in text.split() if w not in LEGAL_SUFFIXES]
    return " ".join(words).strip()


def _read_targets(path: Path) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = _org(row.get("organisation_number") or row.get("organisasjonsnummer") or row.get("orgnr"))
        name = row.get("name") or row.get("navn") or row.get("organisation_name") or row.get("organisasjonsnavn")
        if not org or not name:
            raise ValueError(f"Target row lacks org/name: {row}")
        out.append({"org": org, "name": str(name)})
    return out


def _public_token(session: requests.Session, timeout: float) -> str:
    r = session.get(f"{NAV_BASE}/api/publicToken", timeout=timeout)
    r.raise_for_status()
    text = r.text.strip()
    if text.startswith("{"):
        data = r.json()
        token = str(data.get("token") or data.get("access_token") or "").strip()
        if token:
            return token
    match = JWT_RE.search(text)
    if not match:
        raise RuntimeError("NAV public token endpoint returned no JWT")
    return match.group(0)


def main() -> None:
    p = argparse.ArgumentParser(description="Bounded, non-publishing NAV jobs feasibility screen")
    p.add_argument("--targets", required=True)
    p.add_argument("--audit", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--lookback-days", type=int, default=90)
    p.add_argument("--max-feed-pages", type=int, default=30)
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--min-start-interval", type=float, default=0.4)
    args = p.parse_args()

    targets = _read_targets(Path(args.targets))
    session = requests.Session()
    session.headers.update({"User-Agent": "signalpost-h2i-feasibility/1.0 (+https://github.com/navadeep-17/signal-post)"})

    request_count = 0
    last_start = 0.0

    def paced_get(url: str, **kwargs: Any) -> requests.Response:
        nonlocal request_count, last_start
        delay = args.min_start_interval - (time.monotonic() - last_start)
        if delay > 0:
            time.sleep(delay)
        last_start = time.monotonic()
        request_count += 1
        return session.get(url, timeout=args.timeout, **kwargs)

    allowed_orgs: dict[str, set[str]] = {t["org"]: {t["org"]} for t in targets}
    candidate_names: dict[str, set[str]] = {t["org"]: {_name(t["name"])} for t in targets}
    subunit_errors: list[dict[str, Any]] = []

    for target in targets:
        try:
            r = paced_get(BRREG_SUBUNITS, params={"overordnetEnhet": target["org"], "size": 100})
            r.raise_for_status()
            data = r.json()
            rows = ((data.get("_embedded") or {}).get("underenheter") or [])
            for row in rows:
                sub_org = _org(row.get("organisasjonsnummer"))
                if sub_org:
                    allowed_orgs[target["org"]].add(sub_org)
                n = _name(row.get("navn"))
                if n:
                    candidate_names[target["org"]].add(n)
        except Exception as exc:
            subunit_errors.append({"org": target["org"], "error": f"{type(exc).__name__}: {exc}"})

    token = _public_token(session, args.timeout)
    request_count += 1
    auth = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    modified_since = format_datetime(datetime.now(timezone.utc) - timedelta(days=args.lookback_days), usegmt=True)

    feed_url = f"{NAV_BASE}/api/v1/feed"
    feed_headers = dict(auth)
    feed_headers["If-Modified-Since"] = modified_since

    feed_pages = 0
    feed_items = 0
    active_headers = 0
    candidate_headers = 0
    detail_requests = 0
    jobs: list[dict[str, Any]] = []
    seen_detail_urls: set[str] = set()

    for page_no in range(args.max_feed_pages):
        r = paced_get(feed_url, headers=feed_headers if page_no == 0 else auth)
        if r.status_code == 304:
            break
        r.raise_for_status()
        page = r.json()
        feed_pages += 1
        items = page.get("items") or []
        feed_items += len(items)

        for item in items:
            header = item.get("_feed_entry") or {}
            if str(header.get("status") or "").upper() != "ACTIVE":
                continue
            active_headers += 1
            business = _name(header.get("businessName"))
            if not business:
                continue
            nominated: list[str] = []
            for target in targets:
                for known in candidate_names[target["org"]]:
                    if not known:
                        continue
                    if business == known or (len(known) >= 6 and (business in known or known in business)):
                        nominated.append(target["org"])
                        break
            if not nominated:
                continue
            candidate_headers += 1
            detail_url = str(item.get("url") or "")
            if not detail_url:
                continue
            if not detail_url.startswith("http"):
                detail_url = f"{NAV_BASE}/{detail_url.lstrip('/')}"
            if detail_url in seen_detail_urls:
                continue
            seen_detail_urls.add(detail_url)
            detail_requests += 1
            try:
                dr = paced_get(detail_url, headers=auth)
                dr.raise_for_status()
                detail = dr.json()
                payload = detail.get("ad_content") or detail.get("json") or detail
                employer = payload.get("employer") or {}
                employer_org = _org(employer.get("orgnr"))
                if not employer_org:
                    continue
                matched_target = next((org for org in nominated if employer_org in allowed_orgs[org]), None)
                if not matched_target:
                    continue
                jobs.append({
                    "target_org": matched_target,
                    "employer_org": employer_org,
                    "employer_name": employer.get("name"),
                    "title": payload.get("title") or payload.get("jobtitle"),
                    "published": payload.get("published"),
                    "expires": payload.get("expires"),
                    "updated": payload.get("updated"),
                    "positioncount": payload.get("positioncount"),
                    "sourceurl": payload.get("sourceurl") or payload.get("link"),
                    "nav_uuid": payload.get("uuid") or detail.get("uuid"),
                    "identity": "exact_main_or_brreg_subunit_org_number",
                })
            except Exception:
                continue

        next_url = page.get("next_url")
        if not next_url:
            break
        feed_url = next_url if str(next_url).startswith("http") else f"{NAV_BASE}/{str(next_url).lstrip('/')}"

    matched_companies = sorted({j["target_org"] for j in jobs})
    audit_path = Path(args.audit)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("w", encoding="utf-8") as f:
        for target in targets:
            f.write(json.dumps({
                "target_org": target["org"],
                "target_name": target["name"],
                "allowed_org_numbers": sorted(allowed_orgs[target["org"]]),
                "candidate_names": sorted(candidate_names[target["org"]]),
                "jobs": [j for j in jobs if j["target_org"] == target["org"]],
            }, ensure_ascii=False) + "\n")

    report = {
        "strategy": "nav_jobs_feasibility_v1",
        "publication_enabled": False,
        "rights_basis": "NAV API terms permit republication and statistical/analytical use; experiment only",
        "targets": len(targets),
        "lookback_days": args.lookback_days,
        "max_feed_pages": args.max_feed_pages,
        "feed_pages": feed_pages,
        "feed_items": feed_items,
        "active_headers": active_headers,
        "candidate_headers": candidate_headers,
        "detail_requests": detail_requests,
        "exact_job_matches": len(jobs),
        "companies_with_exact_active_job": len(matched_companies),
        "company_coverage": len(matched_companies) / len(targets) if targets else 0.0,
        "matched_company_orgs": matched_companies,
        "subunit_errors": subunit_errors,
        "logical_requests": request_count,
        "third_party_cost_usd": 0.0,
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
