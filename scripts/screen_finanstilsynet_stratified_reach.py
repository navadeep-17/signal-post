#!/usr/bin/env python3
"""Research-only exact-org screen for sampled Finanstilsynet report pages.

The report row can name both a licence owner and a service provider. Signalpost
counts a company only when the *serviceProvider* carries the target's exact
9-digit Norwegian organisation number. A target appearing only as licenceOwner
never inherits the service provider's activity.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ORG_RE = re.compile(r"^\d{9}$")


def normalize_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if ORG_RE.fullmatch(digits) else None


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def translated(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("norwegian", "english"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()
    return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def target_orgs(path: Path) -> set[str]:
    result: set[str] = set()
    for row in read_jsonl(path):
        org = normalize_org(row.get("organisation_number"))
        if org:
            result.add(org)
    return result


def page_number(path: Path, payload: dict[str, Any]) -> int | None:
    value = payload.get("page")
    if isinstance(value, int):
        return value
    match = re.search(r"(\d+)", path.stem)
    return int(match.group(1)) if match else None


def screen_pages(
    pages: list[Path],
    targets: set[str],
    *,
    today: date,
    recent_days: int = 365,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    matched: dict[str, dict[str, Any]] = {}
    sampled_pages: list[int] = []
    total_pages_seen: set[int] = set()
    total_rows_reported: set[int] = set()
    sampled_rows = 0
    unique_provider_orgs: set[str] = set()
    unique_owner_orgs: set[str] = set()
    owner_only_targets: set[str] = set()
    malformed_provider_numbers = 0

    observations: dict[str, dict[tuple[Any, ...], dict[str, Any]]] = defaultdict(dict)

    for path in pages:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected object payload in {path}")
        page = page_number(path, payload)
        if page is not None:
            sampled_pages.append(page)
        if isinstance(payload.get("totalPages"), int):
            total_pages_seen.add(payload["totalPages"])
        if isinstance(payload.get("total"), int):
            total_rows_reported.add(payload["total"])

        rows = payload.get("data") or []
        if not isinstance(rows, list):
            raise ValueError(f"Expected data list in {path}")
        sampled_rows += len(rows)

        for row in rows:
            if not isinstance(row, dict):
                continue
            provider = row.get("serviceProvider")
            owner = row.get("licenceOwner")
            provider_org = normalize_org(provider.get("legalEntityNumber")) if isinstance(provider, dict) else None
            owner_org = normalize_org(owner.get("legalEntityNumber")) if isinstance(owner, dict) else None

            if isinstance(provider, dict) and provider.get("legalEntityNumber") not in (None, "") and provider_org is None:
                malformed_provider_numbers += 1
            if provider_org:
                unique_provider_orgs.add(provider_org)
            if owner_org:
                unique_owner_orgs.add(owner_org)

            if owner_org in targets and provider_org != owner_org:
                owner_only_targets.add(owner_org)

            # Critical identity gate: only the service provider exact org may count.
            if provider_org not in targets:
                continue

            licence = row.get("licence") if isinstance(row.get("licence"), dict) else {}
            registered = parse_date(licence.get("registeredDate"))
            age_days = (today - registered).days if registered and registered <= today else None
            recent = age_days is not None and age_days <= recent_days
            observation = {
                "organisation_number": provider_org,
                "legal_entity_name": provider.get("legalEntityName"),
                "finanstilsynet_id": provider.get("finanstilsynetId"),
                "service_provider_type": provider.get("serviceProviderType"),
                "licence_type_code": licence.get("licenceTypeCode"),
                "licence_type_name": translated(licence.get("licenceTypeName")),
                "registered_date": registered.isoformat() if registered else None,
                "recent_registration_within_days": recent,
                "licence_owner_org": owner_org,
                "licence_owner_name": owner.get("legalEntityName") if isinstance(owner, dict) else None,
                "owner_same_as_provider": owner_org == provider_org if owner_org else None,
            }
            key = (
                observation["licence_type_code"],
                observation["licence_type_name"],
                observation["registered_date"],
                observation["service_provider_type"],
                observation["licence_owner_org"],
            )
            observations[provider_org][key] = observation

    for org, deduped in observations.items():
        values = sorted(
            deduped.values(),
            key=lambda row: (
                str(row.get("licence_type_code") or ""),
                str(row.get("registered_date") or ""),
                str(row.get("service_provider_type") or ""),
            ),
        )
        matched[org] = {
            "organisation_number": org,
            "observations": values,
            "observation_count": len(values),
            "has_recent_registration": any(v["recent_registration_within_days"] for v in values),
            "licence_type_codes": sorted({str(v["licence_type_code"]) for v in values if v.get("licence_type_code")}),
        }

    total_pages = next(iter(total_pages_seen)) if len(total_pages_seen) == 1 else None
    total_rows = next(iter(total_rows_reported)) if len(total_rows_reported) == 1 else None
    requests = len(pages)
    exact_hits = len(matched)
    projected_full_hits = round(exact_hits * total_pages / requests) if requests and total_pages is not None else None

    report = {
        "source": "Finanstilsynet registry v2 domestic report",
        "screen_type": "stratified_exact_service_provider_org",
        "production_publication_enabled": False,
        "sampled_pages": sorted(sampled_pages),
        "sample_request_count": requests,
        "reported_total_pages": total_pages,
        "reported_total_rows": total_rows,
        "sampled_rows": sampled_rows,
        "unique_provider_orgs_in_sample": len(unique_provider_orgs),
        "unique_owner_orgs_in_sample": len(unique_owner_orgs),
        "exact_target_company_hits": exact_hits,
        "exact_target_reach": exact_hits / len(targets) if targets else 0.0,
        "observed_hits_per_request": exact_hits / requests if requests else 0.0,
        "naive_projected_full_hits": projected_full_hits,
        "recent_registration_companies": sum(1 for row in matched.values() if row["has_recent_registration"]),
        "owner_only_target_matches_not_counted": len(owner_only_targets),
        "owner_only_target_orgs_not_counted": sorted(owner_only_targets),
        "malformed_provider_numbers": malformed_provider_numbers,
        "notes": [
            "Only exact 9-digit serviceProvider legalEntityNumber matches count.",
            "A target appearing only as licenceOwner does not inherit service-provider activity.",
            "The projected full-hit count is a naive stratified-sample estimate and is not publication evidence.",
            "This research screen does not touch production code or a fresh evaluator cohort.",
        ],
    }
    return report, [matched[key] for key in sorted(matched)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages-dir", type=Path, required=True)
    parser.add_argument("--companies", type=Path, required=True)
    parser.add_argument("--today", type=date.fromisoformat, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    pages = sorted(args.pages_dir.glob("page-*.json"), key=lambda path: int(re.search(r"(\d+)", path.stem).group(1)))
    if not pages:
        raise SystemExit("No page-*.json files found")
    targets = target_orgs(args.companies)
    report, matches = screen_pages(pages, targets, today=args.today)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "matched-companies.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in matches),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
