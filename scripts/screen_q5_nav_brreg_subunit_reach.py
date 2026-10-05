#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any, Callable

NAV_BASE = "https://pam-stilling-feed.nav.no"
NAV_TOKEN_URL = f"{NAV_BASE}/api/publicToken"
NAV_FEED_URL = f"{NAV_BASE}/api/v1/feed"
BRREG_SUBUNITS_URL = "https://data.brreg.no/enhetsregisteret/api/underenheter"
USER_AGENT = "SignalpostQualificationScreen/1.0 (+https://github.com/navadeep-17/signal-post)"
JWT_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)(?![A-Za-z0-9_-])")
LEGAL_SUFFIXES = {"as", "asa", "enk", "ans", "da", "sa", "ba", "nuf", "stiftelse", "stiftelsen"}


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


def digits9(value: Any) -> str:
    value = re.sub(r"\D", "", str(value or ""))
    return value if len(value) == 9 else ""


def normalize_name(value: Any) -> str:
    text = " ".join(str(value or "").casefold().split())
    words = [part for part in re.findall(r"[\wæøå]+", text, flags=re.UNICODE) if part]
    while words and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words)


def request_bytes(
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
        response_headers = {str(k).casefold(): str(v) for k, v in response.headers.items()}
    return raw, response_headers


def request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> tuple[dict[str, Any], int]:
    raw, _ = request_bytes(url, headers=headers, timeout=timeout)
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object from {url}")
    return value, len(raw)


def extract_nav_token(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    match = JWT_PATTERN.search(text)
    if not match:
        raise ValueError("NAV public token endpoint did not return a JWT-like token")
    return match.group(1)


def embedded_subunits(body: dict[str, Any]) -> list[dict[str, Any]]:
    embedded = body.get("_embedded") or {}
    if isinstance(embedded, dict):
        for key in ("underenheter", "subunits"):
            rows = embedded.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    rows = body.get("underenheter")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def fetch_official_identity_aliases(
    profiles: list[dict[str, Any]],
    *,
    timeout: float,
    brreg_fetcher: Callable[..., tuple[dict[str, Any], int]] = request_json,
) -> tuple[dict[str, set[tuple[str, str]]], dict[str, str], dict[str, Any]]:
    """Build alias -> {(target main org, exact accepted employer org)} from BRREG.

    Main target names are included with accepted employer org == main org. Every retained
    subunit must explicitly report overordnetEnhet == target main org; deleted subunits are
    skipped. Name matching is only a detail-request shortlist, never final identity proof.
    """
    alias_map: dict[str, set[tuple[str, str]]] = {}
    accepted_to_main: dict[str, str] = {}
    requests = 0
    bytes_received = 0
    subunits = 0
    active_subunits = 0
    targets_with_subunits: set[str] = set()
    pages = 0

    def add_alias(name: Any, main_org: str, accepted_org: str) -> None:
        alias = normalize_name(name)
        if len(alias) >= 3:
            alias_map.setdefault(alias, set()).add((main_org, accepted_org))

    for profile in profiles:
        main_org = digits9(profile.get("organisation_number"))
        if not main_org:
            continue
        accepted_to_main[main_org] = main_org
        add_alias(profile.get("name"), main_org, main_org)
        add_alias(profile.get("legal_name"), main_org, main_org)

        page = 0
        while True:
            query = urllib.parse.urlencode({"overordnetEnhet": main_org, "size": 1000, "page": page})
            body, body_bytes = brreg_fetcher(
                f"{BRREG_SUBUNITS_URL}?{query}",
                headers={"Accept": "application/vnd.brreg.enhetsregisteret.underenhet.v2+json"},
                timeout=timeout,
            )
            requests += 1
            pages += 1
            bytes_received += body_bytes
            rows = embedded_subunits(body)
            for row in rows:
                subunits += 1
                child_org = digits9(row.get("organisasjonsnummer"))
                parent_org = digits9(row.get("overordnetEnhet"))
                if not child_org or parent_org != main_org:
                    continue
                if row.get("slettedato") or row.get("nedleggelsesdato"):
                    continue
                active_subunits += 1
                targets_with_subunits.add(main_org)
                accepted_to_main[child_org] = main_org
                add_alias(row.get("navn"), main_org, child_org)
                for historical in row.get("historiskeNavn") or []:
                    if isinstance(historical, dict) and not historical.get("tilDato"):
                        add_alias(historical.get("navn"), main_org, child_org)

            page_info = body.get("page") or {}
            total_pages = int(page_info.get("totalPages") or 1) if isinstance(page_info, dict) else 1
            if page + 1 >= total_pages:
                break
            page += 1
            if page >= 20:
                raise ValueError(f"unexpected BRREG pagination depth for target {main_org}")

    return alias_map, accepted_to_main, {
        "requests": requests,
        "bytes_received": bytes_received,
        "pages": pages,
        "subunits_returned": subunits,
        "active_subunits": active_subunits,
        "targets_with_active_subunits": len(targets_with_subunits),
        "accepted_employer_orgs": len(accepted_to_main),
        "normalized_aliases": len(alias_map),
    }


def with_page_size(url: str, page_size: int) -> str:
    absolute = urllib.parse.urljoin(NAV_BASE + "/", str(url or ""))
    parsed = urllib.parse.urlparse(absolute)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    query["pageSize"] = [str(page_size)]
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urllib.parse.urlencode(query, doseq=True), ""))


def feed_entry(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("_feed_entry") or item.get("feed_entry") or {}
    return value if isinstance(value, dict) else {}


def modified_key(item: dict[str, Any]) -> str:
    entry = feed_entry(item)
    return str(item.get("date_modified") or entry.get("sistEndret") or "")


def detail_payload(body: dict[str, Any]) -> dict[str, Any]:
    value = body.get("ad_content")
    if value is None:
        value = body.get("json")
    return value if isinstance(value, dict) else {}


def parse_time(value: Any) -> datetime | None:
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


def current_detail(body: dict[str, Any], *, now: datetime) -> bool:
    if str(body.get("status") or "").upper() != "ACTIVE":
        return False
    expires = parse_time(detail_payload(body).get("expires"))
    return expires is None or expires >= now.astimezone(timezone.utc)


def nav_json(
    url: str,
    *,
    token: str,
    if_modified_since: str | None,
    timeout: float,
) -> tuple[dict[str, Any], int]:
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    if if_modified_since:
        headers["If-Modified-Since"] = if_modified_since
    return request_json(url, headers=headers, timeout=timeout)


def screen(
    profiles: list[dict[str, Any]],
    *,
    now: datetime,
    timeout: float = 45.0,
    lookback_days: int = 183,
    page_size: int = 10_000,
    max_feed_pages: int = 50,
    max_detail_requests: int = 500,
    brreg_fetcher: Callable[..., tuple[dict[str, Any], int]] = request_json,
    token_fetcher: Callable[..., tuple[bytes, dict[str, str]]] = request_bytes,
    nav_fetcher: Callable[..., tuple[dict[str, Any], int]] = nav_json,
) -> dict[str, Any]:
    alias_map, accepted_to_main, brreg = fetch_official_identity_aliases(
        profiles, timeout=timeout, brreg_fetcher=brreg_fetcher
    )
    token_raw, _ = token_fetcher(NAV_TOKEN_URL, timeout=timeout)
    token = extract_nav_token(token_raw)
    requests = brreg["requests"] + 1
    bytes_received = brreg["bytes_received"] + len(token_raw)

    since = now.astimezone(timezone.utc) - timedelta(days=lookback_days)
    ims = format_datetime(since, usegmt=True)
    next_url: str | None = with_page_size(NAV_FEED_URL, page_size)
    feed_pages = 0
    headers_scanned = 0
    shortlisted_events = 0
    latest_by_uuid: dict[str, dict[str, Any]] = {}
    reached_end = False

    while next_url and feed_pages < max_feed_pages:
        body, body_bytes = nav_fetcher(next_url, token=token, if_modified_since=ims, timeout=timeout)
        requests += 1
        bytes_received += body_bytes
        feed_pages += 1
        items = body.get("items") or []
        if not isinstance(items, list):
            raise ValueError("NAV feed items must be a list")
        headers_scanned += len(items)
        for item in items:
            if not isinstance(item, dict):
                continue
            entry = feed_entry(item)
            alias = normalize_name(entry.get("businessName"))
            identities = alias_map.get(alias)
            if not identities:
                continue
            uuid = str(entry.get("uuid") or item.get("id") or "").strip()
            detail_url = str(item.get("url") or "").strip()
            if not uuid or not detail_url:
                continue
            shortlisted_events += 1
            candidate = {
                "uuid": uuid,
                "status": str(entry.get("status") or "").upper(),
                "business_name": str(entry.get("businessName") or "")[:300],
                "alias": alias,
                "candidate_identities": sorted([{"main_org": m, "accepted_org": a} for m, a in identities], key=lambda x:(x["main_org"],x["accepted_org"])),
                "detail_url": urllib.parse.urljoin(NAV_BASE + "/", detail_url),
                "modified": modified_key(item),
            }
            existing = latest_by_uuid.get(uuid)
            if existing is None or candidate["modified"] >= existing["modified"]:
                latest_by_uuid[uuid] = candidate

        if body.get("next_url") in (None, "") or body.get("next_id") in (None, ""):
            reached_end = True
            break
        next_url = with_page_size(str(body.get("next_url")), page_size)

    active_candidates = [row for row in latest_by_uuid.values() if row["status"] == "ACTIVE"]
    active_candidates.sort(key=lambda row: (row["modified"], row["uuid"]))
    detail_limit_hit = len(active_candidates) > max_detail_requests
    exact_hits: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    detail_errors: list[dict[str, str]] = []
    detail_requests = 0

    for candidate in active_candidates[:max_detail_requests]:
        try:
            body, body_bytes = nav_fetcher(
                candidate["detail_url"], token=token, if_modified_since=None, timeout=timeout
            )
        except Exception as exc:
            detail_errors.append({"uuid": candidate["uuid"], "error": f"{type(exc).__name__}: {str(exc)[:180]}"})
            continue
        requests += 1
        detail_requests += 1
        bytes_received += body_bytes
        detail = detail_payload(body)
        employer = detail.get("employer") or {}
        if not isinstance(employer, dict):
            employer = {}
        employer_org = digits9(employer.get("orgnr"))
        current = current_detail(body, now=now)
        candidate_pairs = {(row["main_org"], row["accepted_org"]) for row in candidate["candidate_identities"]}
        matching_pairs = sorted((m, a) for m, a in candidate_pairs if a == employer_org)
        if current and employer_org and matching_pairs:
            main_org, accepted_org = matching_pairs[0]
            exact_hits.append({
                "main_target_org": main_org,
                "employing_org": accepted_org,
                "relationship": "main" if accepted_org == main_org else "official_brreg_subunit",
                "identity_method": "nav_employer_orgnr_exact_brreg_main_or_subunit_v1",
                "uuid": str(detail.get("uuid") or body.get("uuid") or candidate["uuid"]),
                "title": str(detail.get("title") or "")[:500],
                "employer_name": str(employer.get("name") or "")[:300],
                "business_name_shortlist": candidate["business_name"],
                "published": detail.get("published"),
                "expires": detail.get("expires"),
                "link": detail.get("link"),
                "application_url": detail.get("applicationUrl"),
                "detail_url": candidate["detail_url"],
            })
        else:
            rejected.append({
                "uuid": candidate["uuid"],
                "business_name_shortlist": candidate["business_name"],
                "employer_name": str(employer.get("name") or "")[:300],
                "employer_org": employer_org,
                "detail_current": current,
                "candidate_identities": candidate["candidate_identities"],
            })

    companies = sorted({hit["main_target_org"] for hit in exact_hits})
    subunit_hits = [hit for hit in exact_hits if hit["relationship"] == "official_brreg_subunit"]
    main_hits = [hit for hit in exact_hits if hit["relationship"] == "main"]
    return {
        "status": "SCREEN_ONLY_NO_PRODUCTION_CHANGE",
        "fresh_qualification": False,
        "profiles": len(profiles),
        "source_identity_method": "NAV employer.orgnr exact main target or exact BRREG child whose overordnetEnhet equals target",
        "brreg": brreg,
        "nav": {
            "lookback_days": lookback_days,
            "page_size": page_size,
            "feed_pages_fetched": feed_pages,
            "reached_feed_end": reached_end,
            "feed_page_limit_hit": bool(next_url and not reached_end and feed_pages >= max_feed_pages),
            "headers_scanned": headers_scanned,
            "name_shortlisted_events": shortlisted_events,
            "latest_name_candidates": len(latest_by_uuid),
            "active_name_candidates": len(active_candidates),
            "detail_requests": detail_requests,
            "detail_limit_hit": detail_limit_hit,
            "detail_errors": detail_errors,
        },
        "logical_network_requests": requests,
        "bytes_received": bytes_received,
        "companies_with_exact_active_vacancies": len(companies),
        "organisation_numbers_with_exact_active_vacancies": companies,
        "exact_active_vacancies": len(exact_hits),
        "exact_main_org_vacancies": len(main_hits),
        "exact_official_subunit_vacancies": len(subunit_hits),
        "exact_hits": exact_hits,
        "rejected_active_shortlist_details": rejected[:150],
        "public_token_retained": False,
        "production_decision": "UNDECIDED_SCREEN_ONLY",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Screen NAV active vacancies using exact BRREG main/subunit identity.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-profiles", type=int, default=100)
    args = parser.parse_args(argv)
    profiles = read_jsonl(Path(args.profiles))
    if len(profiles) != args.expect_profiles:
        raise SystemExit(f"expected {args.expect_profiles} profiles, got {len(profiles)}")
    report = screen(profiles, now=datetime.now(timezone.utc), timeout=args.timeout)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
