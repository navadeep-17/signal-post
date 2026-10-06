#!/usr/bin/env python3
"""Aggregate inventory of exact verified YouTube profile URLs in frozen output.

Zero-network, aggregate-only. No profile URLs or organisation-number lists are persisted.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any

CHANNEL_ID_RE = re.compile(r"^UC[A-Za-z0-9_-]{20,32}$")


def classify_youtube_url(value: Any) -> tuple[str, bool]:
    raw = str(value or "").strip()
    if not raw.startswith(("http://", "https://")):
        return "invalid", False
    try:
        parsed = urllib.parse.urlparse(raw)
    except Exception:
        return "invalid", False
    host = (parsed.hostname or "").casefold().lstrip("www.")
    if host not in {"youtube.com", "m.youtube.com"}:
        return "non_youtube", False

    parts = [urllib.parse.unquote(p) for p in (parsed.path or "").split("/") if p]
    if len(parts) >= 2 and parts[0].casefold() == "channel":
        cid = parts[1]
        return "channel_id", bool(CHANNEL_ID_RE.fullmatch(cid))
    if parts and parts[0].startswith("@"):
        return "handle", False
    if len(parts) >= 2 and parts[0].casefold() == "user":
        return "legacy_user", False
    if len(parts) >= 2 and parts[0].casefold() == "c":
        return "custom_channel", False
    if parts and parts[0].casefold() in {"watch", "shorts", "embed"}:
        return "content_url", False
    return "other_youtube", False


def inventory(path: Path) -> dict[str, Any]:
    companies = 0
    social_companies = 0
    youtube_companies: set[str] = set()
    youtube_claims = 0
    url_classes: Counter[str] = Counter()
    direct_channel_id_companies: set[str] = set()
    invalid_youtube_claims = 0

    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            companies += 1
            org = str(row.get("organisation_number") or "")
            has_social = False
            for claim in row.get("claims") or []:
                if not isinstance(claim, dict):
                    continue
                if (
                    claim.get("field") != "external.profile_handle"
                    or claim.get("availability") != "available"
                ):
                    continue
                has_social = True
                if str(claim.get("platform") or "").casefold() != "youtube":
                    continue
                youtube_claims += 1
                youtube_companies.add(org)
                kind, direct = classify_youtube_url(claim.get("value"))
                url_classes[kind] += 1
                if direct:
                    direct_channel_id_companies.add(org)
                if kind in {"invalid", "non_youtube"}:
                    invalid_youtube_claims += 1
            if has_social:
                social_companies += 1

    return {
        "screen_type": "zero_network_verified_youtube_profile_inventory",
        "companies": companies,
        "companies_with_any_social_profile": social_companies,
        "youtube_profile_companies": len(youtube_companies),
        "youtube_profile_claims": youtube_claims,
        "youtube_company_reach": round(len(youtube_companies) / companies, 6) if companies else 0.0,
        "direct_channel_id_companies": len(direct_channel_id_companies),
        "direct_channel_id_company_reach": round(
            len(direct_channel_id_companies) / companies, 6
        ) if companies else 0.0,
        "url_class_counts": dict(sorted(url_classes.items())),
        "invalid_youtube_claims": invalid_youtube_claims,
        "logical_requests": 0,
        "raw_profile_urls_retained": False,
        "organisation_lists_retained": False,
        "aggregate_counts_only": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    report = inventory(args.output_contract_gz)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
