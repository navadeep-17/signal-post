#!/usr/bin/env python3
"""Consumed-only transfer test for BRREG historical-name .no website candidates.

The candidate source is exact BRREG legal-name history. A former-name domain is only a
nomination hint. Publication requires the existing Signalpost current-entity website
identity gate and registry-risk guard unchanged.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import re
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from norway_company_agent.domain_discovery import distinctive_legal_name_tokens
from norway_company_agent.final_site_discovery import fetch_bounded_homepage
from norway_company_agent.identity import apply_website_identity_gate
from norway_company_agent.zero_cost_discovery import qualify_deterministic_domain_identity
from norway_company_agent.zero_cost_registry_guard import apply_registry_risk_guard

BRREG_ENTITY = "https://data.brreg.no/enhetsregisteret/api/enheter/{}"
USER_AGENT = "Signalpost-research-source-screen/1.0"


def labels(name: Any) -> list[str]:
    tokens = distinctive_legal_name_tokens(name)
    if not tokens:
        return []
    candidates = ["".join(tokens), "-".join(tokens)]
    result: list[str] = []
    seen: set[str] = set()
    for label in candidates:
        label = label.strip("-")
        if label in seen:
            continue
        if not 3 <= len(label) <= 63:
            continue
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?", label):
            continue
        seen.add(label)
        result.append(f"{label}.no")
    return result


def latest_historical_candidate(body: dict[str, Any]) -> dict[str, Any] | None:
    current_labels = set(labels(body.get("navn")))
    choices: list[tuple[dt.date, int, str, str]] = []
    for index, item in enumerate(body.get("historiskeNavn") or []):
        if not isinstance(item, dict):
            continue
        name = " ".join(str(item.get("navn") or "").split())
        if not name:
            continue
        raw_date = str(item.get("tilDato") or "")[:10]
        try:
            end_date = dt.date.fromisoformat(raw_date)
        except ValueError:
            end_date = dt.date.min
        for rank, domain in enumerate(labels(name)):
            if domain in current_labels:
                continue
            # Most recent former name first; compact before hyphenated.
            choices.append((end_date, -rank, domain, name))
    if not choices:
        return None
    end_date, neg_rank, domain, name = max(choices, key=lambda row: (row[0], row[1], row[2]))
    return {
        "domain": domain,
        "url": f"https://{domain}/",
        "historical_name": name,
        "historical_name_end": None if end_date == dt.date.min else end_date.isoformat(),
        "strategy": "most_recent_historical_name_compact" if neg_rank == 0 else "most_recent_historical_name_hyphenated",
    }


def fetch_entity(org: str, timeout: float) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(
        BRREG_ENTITY.format(org),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.brreg.enhetsregisteret.enhet.v2+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except Exception as exc:
        return 0, {"_error": type(exc).__name__}


def profile_from_entity(body: dict[str, Any]) -> dict[str, Any]:
    address = body.get("forretningsadresse") or {}
    raw = {
        "forretningsadresse.postnummer": address.get("postnummer"),
        "forretningsadresse.poststed": address.get("poststed"),
        "forretningsadresse.kommune": address.get("kommune"),
        "forretningsadresse.adresse": " ".join(address.get("adresse") or []),
    }
    return {
        "organisation_number": str(body.get("organisasjonsnummer") or ""),
        "name": body.get("navn"),
        "municipality": address.get("kommune"),
        "evidence": {"registry": {"status": "available", "value": raw}},
    }


def verify_one(org: str, *, entity_timeout: float, site_timeout: float) -> dict[str, Any]:
    status, body = fetch_entity(org, entity_timeout)
    result: dict[str, Any] = {
        "organisation_number": org,
        "entity_http_status": status,
        "candidate": None,
        "site_status": None,
        "site_requests": 0,
        "identity_publishable": False,
        "guard_publishable": False,
        "identity_score": None,
        "identity_reasons": [],
        "observed_organisation_numbers": [],
        "observed_site_owners": [],
    }
    if status != 200 or not body:
        return result

    candidate = latest_historical_candidate(body)
    if not candidate:
        return result
    result["candidate"] = {
        "domain": candidate["domain"],
        "historical_name_end": candidate["historical_name_end"],
        "strategy": candidate["strategy"],
    }

    profile = profile_from_entity(body)
    record, ops = fetch_bounded_homepage(
        candidate["url"],
        source_type="brreg_historical_name_domain_candidate",
        timeout=site_timeout,
    )
    result["site_requests"] = int(ops.get("requests") or 0)
    result["site_status"] = record.get("status")

    gated = apply_website_identity_gate(profile, record)
    candidate_record = gated["website"]
    assessment = qualify_deterministic_domain_identity(
        profile,
        candidate["domain"],
        candidate_record,
        gated.get("assessment"),
    )
    if assessment is not None:
        value = candidate_record.get("value") or {}
        value["identity_assessment"] = assessment
        candidate_record["value"] = value

    result["identity_publishable"] = bool(
        assessment
        and assessment.get("publishable")
        and candidate_record.get("status") == "available"
    )
    result["identity_score"] = (assessment or {}).get("score")
    result["identity_reasons"] = list((assessment or {}).get("reasons") or [])
    result["observed_organisation_numbers"] = list(
        (assessment or {}).get("observed_organisation_numbers") or []
    )
    result["observed_site_owners"] = list((assessment or {}).get("observed_site_owners") or [])

    if result["identity_publishable"]:
        trial = dict(profile)
        trial["evidence"] = {**profile.get("evidence", {}), "website": candidate_record}
        trial["website"] = (
            (candidate_record.get("value") or {}).get("final_url")
            or candidate_record.get("source_url")
            or ""
        )
        trial, guard_reasons = apply_registry_risk_guard(trial)
        guarded = (trial.get("evidence") or {}).get("website") or {}
        guarded_identity = (guarded.get("value") or {}).get("identity_assessment") or {}
        result["guard_publishable"] = bool(
            guarded.get("status") == "available" and guarded_identity.get("publishable")
        )
        if guard_reasons:
            result["identity_reasons"].extend(str(x) for x in guard_reasons)

    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-orgs", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--entity-timeout", type=float, default=12.0)
    ap.add_argument("--site-timeout", type=float, default=8.0)
    args = ap.parse_args()

    orgs: list[str] = []
    for line in args.candidate_orgs.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = re.sub(r"\D", "", str(row.get("organisation_number") or ""))
        if len(org) == 9:
            orgs.append(org)
    orgs = sorted(set(orgs))
    if not orgs:
        raise SystemExit("no candidate organisation numbers")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(
            pool.map(
                lambda org: verify_one(
                    org,
                    entity_timeout=args.entity_timeout,
                    site_timeout=args.site_timeout,
                ),
                orgs,
            )
        )

    entity_status = Counter(str(row["entity_http_status"]) for row in rows)
    site_status = Counter(str(row.get("site_status") or "not_attempted") for row in rows)
    selected = [row for row in rows if row.get("candidate")]
    identity_ok = [row for row in selected if row.get("identity_publishable")]
    guard_ok = [row for row in selected if row.get("guard_publishable")]
    wrong_org = [
        row for row in selected
        if row.get("observed_organisation_numbers")
        and row["organisation_number"] not in row["observed_organisation_numbers"]
    ]

    reason_counts = Counter(
        reason
        for row in selected
        for reason in row.get("identity_reasons") or []
    )
    report = {
        "screen_type": "brreg_historical_name_single_candidate_exact_site_transfer",
        "candidate_companies": len(orgs),
        "entity_http_status_counts": dict(sorted(entity_status.items())),
        "companies_with_recomputed_candidate": len(selected),
        "site_status_counts": dict(sorted(site_status.items())),
        "site_logical_requests": sum(int(row.get("site_requests") or 0) for row in selected),
        "identity_publishable_companies": len(identity_ok),
        "registry_guard_publishable_companies": len(guard_ok),
        "verified_yield_per_candidate_company": round(len(guard_ok) / len(selected), 6) if selected else 0.0,
        "explicit_wrong_org_companies": len(wrong_org),
        "identity_reason_counts": dict(reason_counts.most_common()),
        "incremental_production_entity_requests": 0,
        "third_party_cost_usd": 0.0,
        "search_api_requests": 0,
        "reuse_rights_status": "NLOD_2_0",
        "production_publication_enabled": False,
        "notes": [
            "One most-recent historical-name .no candidate is attempted per eligible consumed company.",
            "Historical name is nomination evidence only; the existing current-entity identity gate remains authoritative.",
            "Existing registry-risk guard is applied after identity qualification.",
            "No fresh evaluator cohort is used.",
        ],
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "attempts.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
