#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ALLOWED_METHODS = {
    "verified_same_site_rss_atom_entry_v1",
    "jsonld_newsarticle_date_published",
    "jsonld_article_date_published",
    "jsonld_blogposting_date_published",
    "meta_article_published_time",
    "meta_itemprop_date_published",
    "meta_name_pubdate",
    "meta_name_date",
    "time_datetime",
    "time_text",
    "date_labelled_element",
    "unambiguous_page_text",
}


def _read(path: Path) -> list[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        org = str(row.get("organisation_number") or "")
        if len(org) != 9 or not org.isdigit() or org in out:
            raise ValueError(f"invalid or duplicate organisation number: {org!r}")
        out[org] = row
    return out


def _available_updates(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for claim in row.get("claims") or []:
        if (
            isinstance(claim, dict)
            and claim.get("field") == "external.company_update"
            and claim.get("availability") == "available"
            and isinstance(claim.get("value"), dict)
        ):
            key = json.dumps(claim.get("value"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            out[key] = claim
    return out


def _evidence(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in row.get("evidence") or []
        if isinstance(item, dict) and str(item.get("id") or "")
    }


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").casefold().removeprefix("www.")
    except ValueError:
        return ""


def _same_site(left: str, right: str) -> bool:
    a, b = _host(left), _host(right)
    if not a or not b:
        return False
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def _retrieval_date(value: Any) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).date()


def audit(
    baseline_rows: list[dict[str, Any]],
    challenger_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    baseline = _index(baseline_rows)
    challenger = _index(challenger_rows)
    if set(baseline) != set(challenger):
        raise ValueError("baseline/challenger organisation sets differ")

    manual: list[dict[str, Any]] = []
    lost: list[dict[str, Any]] = []
    before_companies: set[str] = set()
    after_companies: set[str] = set()

    for org in sorted(baseline):
        before = _available_updates(baseline[org])
        after = _available_updates(challenger[org])
        if before:
            before_companies.add(org)
        if after:
            after_companies.add(org)

        for key in sorted(set(before) - set(after)):
            lost.append(
                {
                    "organisation_number": org,
                    "value": before[key].get("value"),
                }
            )

        evidence_by_id = _evidence(challenger[org])
        for key in sorted(set(after) - set(before)):
            claim = after[key]
            value = claim.get("value") or {}
            linked = [
                evidence_by_id[str(eid)]
                for eid in claim.get("evidence_ids") or []
                if str(eid) in evidence_by_id
            ]
            article_url = str(value.get("url") or "")
            published_raw = str(value.get("published_date") or "")
            try:
                published = date.fromisoformat(published_raw)
            except ValueError:
                published = None

            evidence_checks = []
            for item in linked:
                source_url = str(item.get("source_url") or "")
                method = str(item.get("extraction_method") or "")
                observed_on = _retrieval_date(item.get("retrieved_at"))
                effective = str(item.get("effective_at") or "")
                is_feed = method == "verified_same_site_rss_atom_entry_v1"
                method_root = method.split(":", 1)[0]
                evidence_checks.append(
                    {
                        "source_url_present": source_url.startswith(("http://", "https://")),
                        "content_hash_valid": len(str(item.get("content_sha256") or "")) == 64,
                        "retrieved_at_valid": observed_on is not None,
                        "claim_span_present": bool(str(item.get("claim_span") or "").strip()),
                        "method_allowed": method in ALLOWED_METHODS or method_root in ALLOWED_METHODS,
                        "not_sitemap_or_index_timestamp": "sitemap" not in method.casefold()
                        and "lastmod" not in method.casefold()
                        and "index_timestamp" not in method.casefold(),
                        "page_or_feed_scope_valid": (
                            _same_site(source_url, article_url) if is_feed else source_url.rstrip("/") == article_url.rstrip("/")
                        ),
                        "effective_date_matches_claim": (
                            effective == published_raw if effective else True
                        ),
                        "not_future_vs_retrieval": bool(
                            published is not None
                            and observed_on is not None
                            and published <= observed_on
                        ),
                    }
                )

            complete = bool(linked) and all(all(check.values()) for check in evidence_checks)
            manual.append(
                {
                    "organisation_number": org,
                    "field": "external.company_update",
                    "value": value,
                    "claim_scope": claim.get("claim_scope"),
                    "evidence_complete_and_strict": complete,
                    "evidence_checks": evidence_checks,
                    "evidence": [
                        {
                            "source_url": item.get("source_url"),
                            "retrieved_at": item.get("retrieved_at"),
                            "effective_at": item.get("effective_at"),
                            "content_sha256": item.get("content_sha256"),
                            "claim_span": item.get("claim_span"),
                            "identity_proof": item.get("identity_proof"),
                            "extraction_method": item.get("extraction_method"),
                        }
                        for item in linked
                    ],
                    "manual_exact_entity_review_required": True,
                    "manual_date_scope_review_required": True,
                }
            )

    report = {
        "screen_type": "v9_m6_structured_dated_activity_transfer_audit",
        "companies": len(baseline),
        "baseline_dated_activity_companies": len(before_companies),
        "challenger_dated_activity_companies": len(after_companies),
        "net_new_dated_activity_companies": len(after_companies - before_companies),
        "lost_dated_activity_companies": len(before_companies - after_companies),
        "new_activity_publications": len(manual),
        "lost_activity_publications": len(lost),
        "lost_publications": lost,
        "all_new_evidence_strict": all(
            bool(item.get("evidence_complete_and_strict")) for item in manual
        ),
        "network_requests_added_by_audit": 0,
        "manual_audit_required_for_every_new_activity_publication": True,
        "notes": [
            "Dates must come from the feed snapshot or the same fetched article page as the claimed fact.",
            "Sitemap/index timestamps are not accepted publication dates.",
            "Future dates relative to retrieval are rejected.",
            "A feed snapshot may support its own same-site entry fact; an article page hash may not be borrowed across pages.",
        ],
    }
    return report, manual


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--challenger", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manual-audit", type=Path, required=True)
    args = parser.parse_args()

    report, manual = audit(_read(args.baseline), _read(args.challenger))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.manual_audit.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in manual),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print("--- M6 manual audit rows ---")
    for row in manual:
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
