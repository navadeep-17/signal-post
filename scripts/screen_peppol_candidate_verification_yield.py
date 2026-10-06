#!/usr/bin/env python3
"""Measure transient verification yield of net-new Peppol website candidates.

Research-only. Peppol is not a production source and its directory-data reuse
status remains unresolved. This screen downloads the public export, keeps candidate
URLs only in memory, applies Signalpost's existing bounded homepage fetch and exact
website identity gate, and persists aggregate counts only.

No raw Peppol URL, contact field, matched organisation list, fetched page content or
company-level result is written to disk.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
import urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from norway_company_agent.final_site_discovery import fetch_bounded_homepage
from norway_company_agent.identity import apply_website_identity_gate
from norway_company_agent.website import normalize_homepage

PARTICIPANT_RE = re.compile(
    r"^(?:iso6523-actorid-upis::)?0192:(\d{9})$",
    re.IGNORECASE,
)


def norm_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if len(digits) == 9 else None


def participant_org(value: str) -> str | None:
    decoded = urllib.parse.unquote(str(value or "").strip())
    match = PARTICIPANT_RE.fullmatch(decoded)
    return match.group(1) if match else None


def read_companies(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = norm_org(
            row.get("organisation_number")
            or row.get("organization_number")
            or row.get("orgnr")
        )
        if not org:
            raise ValueError(f"invalid target organisation number: {row!r}")
        if org in result:
            raise ValueError(f"duplicate target organisation number: {org}")
        result[org] = row
    if not result:
        raise ValueError("empty target cohort")
    return result


def current_verified_websites(path: Path, targets: set[str]) -> set[str]:
    found: set[str] = set()
    seen: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            org = norm_org(row.get("organisation_number"))
            if not org or org not in targets:
                continue
            if org in seen:
                raise ValueError(f"duplicate production output org: {org}")
            seen.add(org)
            if any(
                isinstance(claim, dict)
                and claim.get("field") == "official_website"
                and claim.get("availability") == "available"
                and claim.get("value")
                for claim in (row.get("claims") or [])
            ):
                found.add(org)
    if seen != targets:
        raise ValueError(f"production output missing {len(targets-seen)} target companies")
    return found


def split_websites(value: str | None) -> list[str]:
    result: set[str] = set()
    for raw in str(value or "").splitlines():
        normalized = normalize_homepage(raw.strip())
        if normalized:
            result.add(normalized)
    return sorted(result)


def collect_net_new_candidates(
    export_gz: Path,
    companies: dict[str, dict[str, Any]],
    current_web: set[str],
) -> dict[str, str]:
    targets = set(companies)
    candidates: dict[str, set[str]] = {}
    with gzip.open(export_gz, "rt", encoding="iso-8859-1", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        required = {"Participant ID", "Websites"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"Peppol CSV missing expected columns: {sorted(required)}")
        for row in reader:
            org = participant_org(str(row.get("Participant ID") or ""))
            if not org or org not in targets or org in current_web:
                continue
            urls = split_websites(str(row.get("Websites") or ""))
            if urls:
                candidates.setdefault(org, set()).update(urls)

    # One deterministic website candidate per company keeps the verification screen
    # bounded. No candidate value leaves memory.
    return {org: sorted(urls)[0] for org, urls in candidates.items() if urls}


def verify_one(org: str, row: dict[str, Any], url: str, timeout: float) -> dict[str, Any]:
    profile = {
        "organisation_number": org,
        "name": str(row.get("name") or ""),
    }
    record, metrics = fetch_bounded_homepage(
        url,
        source_type="peppol_directory_exact_org_candidate_research_only",
        timeout=timeout,
    )
    gated = apply_website_identity_gate(profile, record)
    assessment = gated.get("assessment") or {}
    reasons = [str(x) for x in assessment.get("reasons") or []]
    observed = set(str(x) for x in assessment.get("observed_organisation_numbers") or [])
    return {
        "status": str(record.get("status") or "unknown"),
        "publishable": bool(assessment.get("publishable")),
        "identity_status": str(assessment.get("status") or "none"),
        "score": float(assessment.get("score") or 0.0),
        "exact_org_observed": org in observed,
        "wrong_explicit_org": bool(observed and org not in observed),
        "site_owner_conflict": any("owned by a different" in reason for reason in reasons),
        "requests": int(metrics.get("requests") or 0),
        "bytes": int(metrics.get("bytes") or 0),
    }


def run_screen(
    export_gz: Path,
    companies: dict[str, dict[str, Any]],
    current_web: set[str],
    *,
    workers: int,
    timeout: float,
) -> dict[str, Any]:
    candidates = collect_net_new_candidates(export_gz, companies, current_web)
    status_counts: Counter[str] = Counter()
    identity_counts: Counter[str] = Counter()
    verified = 0
    exact_org = 0
    wrong_org = 0
    owner_conflict = 0
    requests = 0
    bytes_received = 0

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(verify_one, org, companies[org], url, timeout): org
            for org, url in candidates.items()
        }
        for future in as_completed(futures):
            item = future.result()
            status_counts[item["status"]] += 1
            identity_counts[item["identity_status"]] += 1
            verified += int(item["publishable"])
            exact_org += int(item["exact_org_observed"])
            wrong_org += int(item["wrong_explicit_org"])
            owner_conflict += int(item["site_owner_conflict"])
            requests += item["requests"]
            bytes_received += item["bytes"]

    return {
        "net_new_candidate_companies": len(candidates),
        "attempted_companies": len(candidates),
        "fetch_status_counts": dict(sorted(status_counts.items())),
        "identity_status_counts": dict(sorted(identity_counts.items())),
        "identity_publishable_companies": verified,
        "identity_publishable_rate_of_candidates": (
            round(verified / len(candidates), 6) if candidates else 0.0
        ),
        "exact_org_observed_companies": exact_org,
        "wrong_explicit_org_companies": wrong_org,
        "explicit_different_site_owner_companies": owner_conflict,
        "logical_site_requests": requests,
        "bytes_received": bytes_received,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-gz", type=Path, required=True)
    ap.add_argument("--companies", type=Path, required=True)
    ap.add_argument("--production-output-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=6.0)
    args = ap.parse_args()

    companies = read_companies(args.companies)
    current_web = current_verified_websites(args.production_output_gz, set(companies))
    result = run_screen(
        args.export_gz,
        companies,
        current_web,
        workers=args.workers,
        timeout=args.timeout,
    )
    n = len(companies)
    verified = int(result["identity_publishable_companies"])
    report = {
        "source": "Peppol Directory BusinessCard CSV export",
        "screen_type": "transient_net_new_candidate_existing_identity_gate_yield",
        "cohort_companies": n,
        "current_verified_website_companies": len(current_web),
        "current_verified_website_reach": round(len(current_web) / n, 6),
        **result,
        "verified_net_new_website_reach": round(verified / n, 6),
        "post_verified_website_companies": len(current_web) + verified,
        "post_verified_website_reach": round((len(current_web) + verified) / n, 6),
        "third_party_api_cost_usd": 0.0,
        "production_publication_enabled": False,
        "reuse_rights_status": "UNRESOLVED_FOR_DIRECTORY_DATA",
        "raw_candidate_urls_retained": False,
        "matched_org_lists_retained": False,
        "fetched_page_content_retained": False,
        "contact_fields_retained": False,
        "notes": [
            "This is research-only source qualification; Peppol is not a production source.",
            "Only consumed companies without an existing verified website are attempted.",
            "Only one deterministic Peppol website candidate per company is fetched.",
            "Signalpost's existing bounded homepage fetch and deterministic exact-company identity gate are reused unchanged.",
            "A positive research identity result does not clear Peppol reuse rights or authorize production publication.",
            "No raw Peppol URL, contact field, company-level result or fetched page content is persisted.",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
