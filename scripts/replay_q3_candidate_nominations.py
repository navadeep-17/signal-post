#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from norway_company_agent.discovery import qualify_search_discovered_website  # noqa: E402
from norway_company_agent.final_site_discovery import fetch_bounded_homepage  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.model_web_search import choose_model_url_candidates  # noqa: E402
from run_model_search_discovery import _conflict_quarantine, _q3_multi_entity_org_conflict  # noqa: E402
from run_search_discovery import read_jsonl, unresolved_for_search  # noqa: E402


def _load_nominations(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("nominations") or []
    by_org: dict[str, Any] = {}
    for item in rows:
        org = str((item or {}).get("organisation_number") or "").strip()
        if len(org) != 9 or not org.isdigit():
            raise ValueError(f"Invalid nomination organisation number: {org!r}")
        if org in by_org:
            raise ValueError(f"Duplicate nomination organisation number: {org}")
        by_org[org] = item
    return {"metadata": {key: value for key, value in payload.items() if key != "nominations"}, "by_org": by_org}


def _candidate_results(urls: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "url": url,
            "rank": index,
            "provider": "frozen_consumed_nomination",
        }
        for index, url in enumerate(urls, start=1)
    ]


def replay(
    profiles: list[dict[str, Any]],
    nominations: dict[str, Any],
    *,
    timeout: float,
    candidate_limit: int,
) -> dict[str, Any]:
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if candidate_limit < 1:
        raise ValueError("candidate_limit must be positive")

    profiles_by_org = {
        str(row.get("organisation_number") or ""): row
        for row in profiles
        if row.get("organisation_number")
    }
    outcomes: list[dict[str, Any]] = []
    total_requests = 0
    total_bytes = 0
    accepted = 0
    quarantined = 0
    unavailable = 0

    for org, nomination in sorted((nominations.get("by_org") or {}).items()):
        profile = profiles_by_org.get(org)
        if profile is None:
            outcomes.append(
                {
                    "organisation_number": org,
                    "legal_name": nomination.get("legal_name"),
                    "status": "profile_missing",
                    "accepted": False,
                }
            )
            unavailable += 1
            continue
        if not unresolved_for_search(profile):
            outcomes.append(
                {
                    "organisation_number": org,
                    "legal_name": profile.get("name"),
                    "status": "already_has_publishable_website",
                    "accepted": False,
                }
            )
            unavailable += 1
            continue

        selected = choose_model_url_candidates(
            _candidate_results([str(url) for url in (nomination.get("urls") or [])]),
            limit=candidate_limit,
        )
        if not selected:
            outcomes.append(
                {
                    "organisation_number": org,
                    "legal_name": profile.get("name"),
                    "status": "no_candidate_after_filter",
                    "accepted": False,
                    "expected_risk": nomination.get("expected_risk"),
                }
            )
            unavailable += 1
            continue

        accepted_row: dict[str, Any] | None = None
        attempts: list[dict[str, Any]] = []
        for candidate in selected:
            website, operations = fetch_bounded_homepage(
                candidate["url"],
                source_type="q3_frozen_consumed_nomination",
                timeout=timeout,
            )
            total_requests += int(operations.get("requests") or 0)
            total_bytes += int(operations.get("bytes") or 0)

            gated = apply_website_identity_gate(profile, website)
            website = gated["website"]
            base_assessment = gated.get("assessment")
            multi_entity_conflict = bool(
                base_assessment
                and base_assessment.get("publishable")
                and _q3_multi_entity_org_conflict(profile, base_assessment)
            )
            if multi_entity_conflict:
                assessment = _conflict_quarantine(base_assessment)
            else:
                assessment = qualify_search_discovered_website(profile, website, base_assessment)
            if assessment is not None:
                (website.get("value") or {})["identity_assessment"] = assessment

            final_url = (website.get("value") or {}).get("final_url") or website.get("source_url")
            publishable = bool(
                website.get("status") == "available"
                and assessment
                and assessment.get("publishable")
            )
            attempt = {
                "candidate_url": candidate.get("url"),
                "final_url": final_url,
                "website_status": website.get("status"),
                "content_sha256": website.get("content_sha256"),
                "identity_status": (assessment or {}).get("status"),
                "identity_score": (assessment or {}).get("score"),
                "identity_method": (assessment or {}).get("method"),
                "identity_reasons": list((assessment or {}).get("reasons") or []),
                "observed_organisation_numbers": list(
                    (assessment or {}).get("observed_organisation_numbers") or []
                ),
                "multi_entity_conflict": multi_entity_conflict,
                "publishable": publishable,
                "logical_requests": int(operations.get("requests") or 0),
                "bytes": int(operations.get("bytes") or 0),
            }
            attempts.append(attempt)
            if publishable:
                accepted_row = attempt
                break

        if accepted_row is not None:
            accepted += 1
            status = "accepted"
        else:
            quarantined += 1
            status = "quarantined"
        outcomes.append(
            {
                "organisation_number": org,
                "legal_name": profile.get("name"),
                "expected_risk": nomination.get("expected_risk"),
                "status": status,
                "accepted": accepted_row is not None,
                "accepted_url": (accepted_row or {}).get("final_url"),
                "attempts": attempts,
            }
        )

    return {
        "metadata": nominations.get("metadata") or {},
        "profiles": len(profiles),
        "nominated_companies": len(nominations.get("by_org") or {}),
        "accepted": accepted,
        "quarantined": quarantined,
        "unavailable": unavailable,
        "logical_requests": total_requests,
        "bytes": total_bytes,
        "outcomes": outcomes,
        "policy": (
            "Consumed-only downstream verification replay. Frozen nominations are not evidence; "
            "only independently fetched destination-page evidence may be accepted."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay frozen consumed Q3 URL nominations through the current exact-company gate.")
    parser.add_argument("--input", required=True, help="Consumed profile JSONL")
    parser.add_argument("--nominations", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--candidate-limit", type=int, default=2, choices=range(1, 3), metavar="1..2")
    args = parser.parse_args()

    report = replay(
        read_jsonl(Path(args.input)),
        _load_nominations(Path(args.nominations)),
        timeout=args.timeout,
        candidate_limit=args.candidate_limit,
    )
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
