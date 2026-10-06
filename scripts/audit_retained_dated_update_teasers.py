#!/usr/bin/env python3
"""Audit zero-network dated update teasers retained on exact verified homepages.

This is a research-only coverage audit. It does not turn homepage cards into production
claims. The strict tier requires all publication evidence to be page-local to the same
retained homepage card nomination:

- the primary website was already exact-verified and publishable;
- the nominated URL stays on the verified company's registered domain;
- the same retained card context contains exactly one unambiguous date;
- the date is not in the future and is within the requested lookback window;
- the anchor itself is a specific headline, not "read more"/"les mer"/a section label;
- the homepage content hash is retained.

A second diagnostic tier counts dated cards whose anchors are generic. Those are NOT
promotion candidates; the count tells us how much recall would require a stronger
card-title extraction in the collector.

No network access occurs and no raw titles/URLs/org lists are persisted.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import sys
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.first_party_activity import _all_dates  # noqa: E402
from norway_company_agent.homepage_news_signal import GENERIC_NEWS_TITLES  # noqa: E402
from norway_company_agent.website import _registered_domain  # noqa: E402


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _verified_website(profile: dict[str, Any]) -> dict[str, Any] | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") if isinstance(website.get("value"), dict) else {}
    assessment = value.get("identity_assessment") if isinstance(value.get("identity_assessment"), dict) else {}
    final_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    digest = str(website.get("content_sha256") or value.get("content_sha256") or "").strip()
    if (
        website.get("status") != "available"
        or not assessment.get("publishable")
        or not final_url.startswith(("http://", "https://"))
        or len(digest) != 64
    ):
        return None
    return website


def _same_registered_domain(url: str, base: str) -> bool:
    try:
        return bool(
            _registered_domain(url)
            and _registered_domain(url).casefold() == _registered_domain(base).casefold()
        )
    except Exception:
        return False


def _specific_anchor(value: str) -> bool:
    text = " ".join(str(value or "").split()).strip(" -|:.!?")
    if not text:
        return False
    folded = text.casefold()
    if folded in {x.casefold().strip(" -|:.!?") for x in GENERIC_NEWS_TITLES}:
        return False
    # Homepage cards often use "Les mer" / "Read more", which are intentionally not facts.
    if folded in {
        "les mer", "les meir", "read more", "more", "se mer", "sjå meir",
        "learn more", "view more", "details", "mer",
    }:
        return False
    words = re.findall(r"[A-Za-zÆØÅæøå0-9][A-Za-zÆØÅæøå0-9-]*", text)
    return len(words) >= 3 and len(text) >= 12


def _existing_update_orgs(contracts: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for row in contracts:
        org = str(row.get("organisation_number") or "")
        if any(
            isinstance(claim, dict)
            and claim.get("field") == "external.company_update"
            and claim.get("availability") == "available"
            for claim in row.get("claims") or []
        ):
            out.add(org)
    return out


def audit(
    profiles: list[dict[str, Any]],
    contracts: list[dict[str, Any]],
    *,
    as_of: dt.date,
    lookback_days: int,
) -> dict[str, Any]:
    pindex = {str(row.get("organisation_number") or ""): row for row in profiles}
    cindex = {str(row.get("organisation_number") or ""): row for row in contracts}
    if (
        len(pindex) != len(profiles)
        or len(cindex) != len(contracts)
        or set(pindex) != set(cindex)
    ):
        raise ValueError("profile/contract org sets differ or contain duplicates")

    cutoff = as_of - dt.timedelta(days=lookback_days)
    existing = _existing_update_orgs(contracts)
    verified_sites: set[str] = set()
    any_news_nomination: set[str] = set()
    dated_context_orgs: set[str] = set()
    unambiguous_date_orgs: set[str] = set()
    in_window_orgs: set[str] = set()
    strict_orgs: set[str] = set()
    generic_anchor_orgs: set[str] = set()

    total_links = 0
    dated_links = 0
    unambiguous_links = 0
    in_window_links = 0
    strict_links = 0
    generic_anchor_links = 0
    date_parse_failures = 0
    out_of_window_links = 0
    cross_domain_links = 0
    missing_hash_links = 0
    marker_counts: Counter[str] = Counter()

    for org, profile in pindex.items():
        website = _verified_website(profile)
        if website is None:
            continue
        verified_sites.add(org)
        value = website.get("value") or {}
        final_url = str(value.get("final_url") or website.get("source_url") or "").strip()
        homepage_hash = str(website.get("content_sha256") or value.get("content_sha256") or "").strip()

        links = [
            row for row in (value.get("news_detail_links") or [])
            if isinstance(row, dict) and row.get("url")
        ]
        if links:
            any_news_nomination.add(org)

        for row in links:
            total_links += 1
            marker_counts[str(row.get("marker") or "unknown")] += 1
            url = str(row.get("url") or "").strip()
            if not _same_registered_domain(url, final_url):
                cross_domain_links += 1
                continue

            retained_hash = str(row.get("homepage_content_sha256") or homepage_hash).strip()
            if len(retained_hash) != 64:
                missing_hash_links += 1
                continue

            context = " ".join(str(row.get("dated_context") or "").split())
            if not context:
                continue
            dated_links += 1
            dated_context_orgs.add(org)

            dates = _all_dates(context)
            if len(dates) != 1:
                date_parse_failures += 1
                continue
            unambiguous_links += 1
            unambiguous_date_orgs.add(org)

            raw_date = next(iter(dates))
            try:
                date_value = dt.date.fromisoformat(raw_date)
            except ValueError:
                date_parse_failures += 1
                continue
            if date_value < cutoff or date_value > as_of:
                out_of_window_links += 1
                continue
            in_window_links += 1
            in_window_orgs.add(org)

            anchor = str(row.get("anchor_text") or "").strip()
            if _specific_anchor(anchor):
                strict_links += 1
                strict_orgs.add(org)
            else:
                generic_anchor_links += 1
                generic_anchor_orgs.add(org)

    strict_net_new = strict_orgs - existing
    generic_only = generic_anchor_orgs - strict_orgs
    report = {
        "screen_type": "zero_network_retained_homepage_dated_update_teaser_audit",
        "companies": len(profiles),
        "as_of": as_of.isoformat(),
        "lookback_days": lookback_days,
        "verified_site_companies": len(verified_sites),
        "baseline_dated_update_companies": len(existing),
        "companies_with_any_news_nomination": len(any_news_nomination),
        "companies_with_dated_card_context": len(dated_context_orgs),
        "companies_with_unambiguous_card_date": len(unambiguous_date_orgs),
        "companies_with_in_window_dated_card": len(in_window_orgs),
        "strict_specific_headline_dated_card_companies": len(strict_orgs),
        "strict_net_new_dated_update_teaser_companies": len(strict_net_new),
        "strict_net_new_reach": round(len(strict_net_new) / len(profiles), 6),
        "generic_anchor_in_window_companies": len(generic_anchor_orgs),
        "generic_anchor_only_companies": len(generic_only),
        "news_nomination_links": total_links,
        "dated_context_links": dated_links,
        "unambiguous_date_links": unambiguous_links,
        "in_window_dated_links": in_window_links,
        "strict_specific_headline_links": strict_links,
        "generic_anchor_in_window_links": generic_anchor_links,
        "out_of_window_links": out_of_window_links,
        "ambiguous_or_unparsed_date_links": date_parse_failures,
        "cross_domain_links_rejected": cross_domain_links,
        "missing_homepage_hash_links_rejected": missing_hash_links,
        "marker_counts": dict(sorted(marker_counts.items())),
        "logical_network_requests_added": 0,
        "conservative_request_charge_added": 0,
        "third_party_api_cost_usd_added": 0.0,
        "search_api_requests_added": 0,
        "production_publication_enabled": False,
        "raw_titles_urls_orgs_retained": False,
        "notes": [
            "Strict tier is a coverage hypothesis only; this audit publishes no claims.",
            "Strict tier requires exact-verified homepage, same registered domain, retained homepage hash, one page-local date, <=lookback age, and a specific non-generic anchor headline.",
            "Generic-anchor dated cards are diagnostic only and cannot become claims without a stronger card-title extraction.",
            "No article detail page or body is implied by a homepage teaser.",
            "Phase-4 date ambiguity rules remain fail-closed.",
        ],
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--output-contract-gz", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--as-of", default="2026-10-06")
    parser.add_argument("--lookback-days", type=int, default=365)
    args = parser.parse_args()

    profiles: list[dict[str, Any]] = []
    for path in sorted(args.profiles_dir.rglob("profiles.jsonl")):
        profiles.extend(read_jsonl(path))
    contracts = read_jsonl_gz(args.output_contract_gz)
    if len(profiles) != 1000 or len(contracts) != 1000:
        raise SystemExit(
            f"expected 1000 profiles/contracts, got {len(profiles)}/{len(contracts)}"
        )
    report = audit(
        profiles,
        contracts,
        as_of=dt.date.fromisoformat(args.as_of),
        lookback_days=args.lookback_days,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
