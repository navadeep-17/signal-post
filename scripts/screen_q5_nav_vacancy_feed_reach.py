#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any, Callable

BASE_URL = "https://pam-stilling-feed.nav.no"
PUBLIC_TOKEN_URL = f"{BASE_URL}/api/publicToken"
FEED_URL = f"{BASE_URL}/api/v1/feed"
DEFAULT_PAGE_SIZE = 10_000
DEFAULT_LOOKBACK_DAYS = 183
DEFAULT_MAX_FEED_PAGES = 50
DEFAULT_MAX_DETAIL_REQUESTS = 200
USER_AGENT = "SignalpostQualificationScreen/1.0 (+https://github.com/navadeep-17/signal-post)"
LEGAL_SUFFIXES = {
    "as",
    "asa",
    "enk",
    "ans",
    "da",
    "sa",
    "ba",
    "nuf",
    "stiftelse",
    "stiftelsen",
}


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


def normalize_company_name(value: Any) -> str:
    text = " ".join(str(value or "").casefold().split())
    words = [part for part in re.findall(r"[\wæøå]+", text, flags=re.UNICODE) if part]
    while words and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words)


def target_name_index(profiles: list[dict[str, Any]]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for profile in profiles:
        org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
        if len(org) != 9:
            continue
        aliases = {
            normalize_company_name(profile.get("name")),
            normalize_company_name(profile.get("legal_name")),
        }
        for alias in aliases:
            if len(alias) >= 3:
                index.setdefault(alias, set()).add(org)
    return index


def _extract_public_token(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError("NAV public token endpoint returned an empty response")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = None
    candidates: list[str] = []
    if isinstance(value, str):
        candidates.append(value)
    elif isinstance(value, dict):
        for key in ("token", "access_token", "jwt", "value"):
            if value.get(key):
                candidates.append(str(value[key]))
    candidates.append(text.strip('"'))
    token = next((candidate.strip() for candidate in candidates if candidate.count(".") >= 2), "")
    if not token:
        raise ValueError("NAV public token endpoint did not return a JWT-like token")
    return token


def _request_bytes(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    max_bytes: int = 40_000_000,
) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError(f"response exceeded byte ceiling for {url}")
        response_headers = {str(key).casefold(): str(value) for key, value in response.headers.items()}
    return raw, response_headers


def _request_json(
    url: str,
    *,
    token: str,
    if_modified_since: str | None = None,
    timeout: float = 30.0,
) -> tuple[dict[str, Any], int]:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if if_modified_since:
        headers["If-Modified-Since"] = if_modified_since
    raw, _ = _request_bytes(url, headers=headers, timeout=timeout)
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object from {url}")
    return value, len(raw)


def _with_page_size(url: str, page_size: int) -> str:
    absolute = urllib.parse.urljoin(BASE_URL + "/", str(url or ""))
    parsed = urllib.parse.urlparse(absolute)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    query["pageSize"] = [str(page_size)]
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, urllib.parse.urlencode(query, doseq=True), "")
    )


def _feed_entry(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("_feed_entry") or item.get("feed_entry") or {}
    return value if isinstance(value, dict) else {}


def _modified_key(item: dict[str, Any]) -> str:
    entry = _feed_entry(item)
    return str(item.get("date_modified") or entry.get("sistEndret") or "")


def _detail_payload(body: dict[str, Any]) -> dict[str, Any]:
    value = body.get("ad_content")
    if value is None:
        value = body.get("json")
    return value if isinstance(value, dict) else {}


def _parse_time(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def detail_is_current(body: dict[str, Any], *, now: datetime) -> bool:
    if str(body.get("status") or "").upper() != "ACTIVE":
        return False
    detail = _detail_payload(body)
    expires = _parse_time(detail.get("expires"))
    return expires is None or expires >= now.astimezone(timezone.utc)


def _safe_vacancy_summary(body: dict[str, Any]) -> dict[str, Any]:
    detail = _detail_payload(body)
    employer = detail.get("employer") or {}
    if not isinstance(employer, dict):
        employer = {}
    return {
        "uuid": str(detail.get("uuid") or body.get("uuid") or ""),
        "status": str(body.get("status") or ""),
        "title": str(detail.get("title") or "")[:500],
        "jobtitle": str(detail.get("jobtitle") or "")[:300] or None,
        "employer_name": str(employer.get("name") or "")[:300],
        "employer_orgnr": re.sub(r"\D", "", str(employer.get("orgnr") or "")),
        "published": detail.get("published"),
        "expires": detail.get("expires"),
        "application_due": detail.get("applicationDue"),
        "link": detail.get("link"),
        "application_url": detail.get("applicationUrl"),
        "source": detail.get("source"),
    }


def screen_nav_feed(
    profiles: list[dict[str, Any]],
    *,
    now: datetime,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_feed_pages: int = DEFAULT_MAX_FEED_PAGES,
    max_detail_requests: int = DEFAULT_MAX_DETAIL_REQUESTS,
    timeout: float = 30.0,
    token_fetcher: Callable[..., tuple[bytes, dict[str, str]]] = _request_bytes,
    json_fetcher: Callable[..., tuple[dict[str, Any], int]] = _request_json,
) -> dict[str, Any]:
    if lookback_days < 1 or page_size < 1 or max_feed_pages < 1 or max_detail_requests < 1:
        raise ValueError("screen bounds must be positive")
    if page_size > 10_000:
        raise ValueError("NAV feed page_size cannot exceed 10000")

    names = target_name_index(profiles)
    targets = {
        re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
        for profile in profiles
        if len(re.sub(r"\D", "", str(profile.get("organisation_number") or ""))) == 9
    }
    token_raw, _ = token_fetcher(PUBLIC_TOKEN_URL, timeout=timeout)
    token = _extract_public_token(token_raw)
    logical_requests = 1
    bytes_received = len(token_raw)

    since = now.astimezone(timezone.utc) - timedelta(days=lookback_days)
    if_modified_since = format_datetime(since, usegmt=True)
    next_url: str | None = _with_page_size(FEED_URL, page_size)
    feed_pages = 0
    headers_scanned = 0
    active_headers_scanned = 0
    name_shortlisted_events = 0
    latest_by_uuid: dict[str, dict[str, Any]] = {}
    reached_feed_end = False

    while next_url and feed_pages < max_feed_pages:
        body, body_bytes = json_fetcher(
            next_url,
            token=token,
            if_modified_since=if_modified_since,
            timeout=timeout,
        )
        logical_requests += 1
        bytes_received += body_bytes
        feed_pages += 1
        items = body.get("items") or []
        if not isinstance(items, list):
            raise ValueError("NAV feed page items must be a list")
        headers_scanned += len(items)
        for item in items:
            if not isinstance(item, dict):
                continue
            entry = _feed_entry(item)
            status = str(entry.get("status") or "").upper()
            active_headers_scanned += int(status == "ACTIVE")
            alias = normalize_company_name(entry.get("businessName"))
            candidate_targets = sorted(names.get(alias) or [])
            if not candidate_targets:
                continue
            uuid = str(entry.get("uuid") or item.get("id") or "").strip()
            detail_url = str(item.get("url") or "").strip()
            if not uuid or not detail_url:
                continue
            name_shortlisted_events += 1
            candidate = {
                "uuid": uuid,
                "status": status,
                "business_name": str(entry.get("businessName") or "")[:300],
                "normalized_business_name": alias,
                "target_organisation_numbers": candidate_targets,
                "detail_url": urllib.parse.urljoin(BASE_URL + "/", detail_url),
                "date_modified": _modified_key(item),
            }
            existing = latest_by_uuid.get(uuid)
            if existing is None or candidate["date_modified"] >= existing["date_modified"]:
                latest_by_uuid[uuid] = candidate

        raw_next = body.get("next_url")
        raw_next_id = body.get("next_id")
        if raw_next in (None, "") or raw_next_id in (None, ""):
            reached_feed_end = True
            break
        next_url = _with_page_size(str(raw_next), page_size)

    latest_candidates = sorted(latest_by_uuid.values(), key=lambda item: (item["date_modified"], item["uuid"]))
    active_candidates = [item for item in latest_candidates if item["status"] == "ACTIVE"]
    detail_limit_hit = len(active_candidates) > max_detail_requests
    details_to_fetch = active_candidates[:max_detail_requests]

    exact_matches: list[dict[str, Any]] = []
    nonmatching_detail_candidates: list[dict[str, Any]] = []
    detail_errors: list[dict[str, str]] = []
    detail_requests = 0
    for candidate in details_to_fetch:
        try:
            body, body_bytes = json_fetcher(
                candidate["detail_url"],
                token=token,
                if_modified_since=None,
                timeout=timeout,
            )
        except Exception as exc:
            detail_errors.append({"uuid": candidate["uuid"], "error": f"{type(exc).__name__}: {str(exc)[:180]}"})
            continue
        logical_requests += 1
        detail_requests += 1
        bytes_received += body_bytes
        summary = _safe_vacancy_summary(body)
        current = detail_is_current(body, now=now)
        org = summary["employer_orgnr"]
        target_candidates = set(candidate["target_organisation_numbers"])
        if current and len(org) == 9 and org in targets and org in target_candidates:
            exact_matches.append(
                {
                    **summary,
                    "identity_method": "nav_feed_employer_orgnr_exact_target_v1",
                    "business_name_shortlist": candidate["business_name"],
                    "detail_url": candidate["detail_url"],
                }
            )
        else:
            nonmatching_detail_candidates.append(
                {
                    "uuid": candidate["uuid"],
                    "business_name_shortlist": candidate["business_name"],
                    "target_organisation_numbers": candidate["target_organisation_numbers"],
                    "detail_status": summary["status"],
                    "detail_current": current,
                    "employer_name": summary["employer_name"],
                    "employer_orgnr": org,
                }
            )

    exact_by_org: dict[str, list[dict[str, Any]]] = {}
    for match in exact_matches:
        exact_by_org.setdefault(match["employer_orgnr"], []).append(match)

    return {
        "status": "SCREEN_ONLY_NO_PRODUCTION_CHANGE",
        "fresh_qualification": False,
        "source": "NAV Job Vacancy Feed",
        "source_url": FEED_URL,
        "source_identity_field": "ad_content.employer.orgnr",
        "source_identity_requirement": "exact nine-digit target organisation number",
        "profiles": len(profiles),
        "target_organisation_numbers": len(targets),
        "lookback_days": lookback_days,
        "if_modified_since": if_modified_since,
        "page_size": page_size,
        "max_feed_pages": max_feed_pages,
        "feed_pages_fetched": feed_pages,
        "reached_feed_end": reached_feed_end,
        "feed_page_limit_hit": bool(next_url and not reached_feed_end and feed_pages >= max_feed_pages),
        "headers_scanned": headers_scanned,
        "active_headers_scanned": active_headers_scanned,
        "name_shortlisted_events": name_shortlisted_events,
        "latest_name_candidates": len(latest_candidates),
        "active_name_candidates": len(active_candidates),
        "max_detail_requests": max_detail_requests,
        "detail_limit_hit": detail_limit_hit,
        "detail_requests": detail_requests,
        "detail_errors": detail_errors,
        "logical_network_requests_including_public_token": logical_requests,
        "bytes_received": bytes_received,
        "companies_with_exact_active_vacancies": len(exact_by_org),
        "exact_active_vacancies": len(exact_matches),
        "organisation_numbers_with_exact_active_vacancies": sorted(exact_by_org),
        "exact_matches": exact_matches,
        "nonmatching_name_shortlist_details": nonmatching_detail_candidates[:100],
        "public_token_retained": False,
        "production_decision": "UNDECIDED_SCREEN_ONLY",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Screen NAV Job Vacancy Feed for exact-org active hiring reach on a consumed cohort.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--max-feed-pages", type=int, default=DEFAULT_MAX_FEED_PAGES)
    parser.add_argument("--max-detail-requests", type=int, default=DEFAULT_MAX_DETAIL_REQUESTS)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-profiles", type=int)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    profiles = read_jsonl(Path(args.profiles))
    if args.expect_profiles is not None and len(profiles) != args.expect_profiles:
        raise SystemExit(f"expected {args.expect_profiles} profiles, got {len(profiles)}")
    report = screen_nav_feed(
        profiles,
        now=datetime.now(timezone.utc),
        lookback_days=args.lookback_days,
        page_size=args.page_size,
        max_feed_pages=args.max_feed_pages,
        max_detail_requests=args.max_detail_requests,
        timeout=args.timeout,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
