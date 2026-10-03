#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs  # noqa: E402
from norway_company_agent.final_site_discovery import MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE  # noqa: E402
from norway_company_agent.h1g_hyphenated_no_recall import evaluate_hyphenated_no_fallback  # noqa: E402
from norway_company_agent.wikidata_discovery import (  # noqa: E402
    discover_final_website_with_wikidata,
    fetch_wikidata_website_candidates,
)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _publishable_website(profile: dict[str, Any]) -> bool:
    website = ((profile.get("evidence") or {}).get("website") or {})
    identity = ((website.get("value") or {}).get("identity_assessment") or {})
    return bool(website.get("status") == "available" and identity.get("publishable"))


def baseline_website_discovery(
    profiles: list[dict[str, Any]],
    *,
    site_timeout: float = 6.0,
    wikidata_timeout: float = 8.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run the incumbent website-discovery stack without unrelated enrichment modules.

    This intentionally mirrors the current production website order:
    H1c/H1d deterministic + registry-linked discovery, H1e exact-org Wikidata fallback,
    then H1g hyphenated .no fallback inside the same four-request per-company ceiling.
    Search/model discovery is not called here.
    """
    if site_timeout <= 0 or wikidata_timeout <= 0:
        raise ValueError("timeouts must be positive")
    orgs = [str(profile.get("organisation_number") or "") for profile in profiles]
    if len(orgs) != len(set(orgs)):
        raise ValueError("profiles contain duplicate organisation numbers")

    wikidata_candidates, wikidata_metrics = fetch_wikidata_website_candidates(
        orgs,
        timeout=wikidata_timeout,
    )
    rows: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    total_site_requests = 0
    total_site_bytes = 0

    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        row, site = discover_final_website_with_wikidata(
            profile,
            wikidata_candidate=wikidata_candidates.get(org),
            timeout=site_timeout,
        )
        row, h1g = evaluate_hyphenated_no_fallback(
            row,
            timeout=site_timeout,
            base_site_logical_requests=int(site.get("requests") or 0),
        )
        site_requests = int(site.get("requests") or 0) + int(h1g.get("requests_added") or 0)
        site_bytes = int(site.get("bytes") or 0) + int(h1g.get("bytes_added") or 0)
        if site_requests > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
            raise RuntimeError(
                f"Incumbent site request ceiling exceeded for {org}: "
                f"{site_requests}>{MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE}"
            )
        if h1g.get("verified"):
            site["selected_source"] = "h1g_hyphenated_no"
            site["promoted"] = True
        selected_source = str(site.get("selected_source") or "none") if _publishable_website(row) else "none"
        source_counts[selected_source] += 1
        row["v9_m1c_incumbent_site_audit"] = {
            "logical_requests": site_requests,
            "bytes": site_bytes,
            "selected_source": selected_source,
            "wikidata_candidate_available": bool(site.get("wikidata_candidate_available")),
            "wikidata_attempted": bool(site.get("wikidata_attempted")),
            "wikidata_verified": bool(site.get("wikidata_verified")),
            "h1g_attempted": bool(h1g.get("attempted")),
            "h1g_verified": bool(h1g.get("verified")),
        }
        total_site_requests += site_requests
        total_site_bytes += site_bytes
        rows.append(row)

    return rows, {
        "companies": len(rows),
        "resolved": sum(1 for row in rows if _publishable_website(row)),
        "unresolved": sum(1 for row in rows if not _publishable_website(row)),
        "source_counts": dict(sorted(source_counts.items())),
        "site_logical_requests": total_site_requests,
        "site_request_ceiling": len(rows) * MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
        "site_bytes": total_site_bytes,
        "wikidata": wikidata_metrics,
        "third_party_api_cost_usd": 0.0,
        "search_api_requests": 0,
    }


def prepare(
    *,
    organisations_path: Path,
    bulk_path: Path,
    baseline_profiles_path: Path,
    unresolved_output_path: Path,
    report_path: Path,
    target_unresolved: int,
    site_timeout: float,
    wikidata_timeout: float,
) -> dict[str, Any]:
    if target_unresolved < 1:
        raise ValueError("target_unresolved must be positive")
    input_records = read_organisation_inputs(organisations_path)
    orgs = [row["organisation_number"] for row in input_records]
    profiles, bulk_metrics = profiles_from_bulk(bulk_path, orgs)

    metadata = {row["organisation_number"]: row for row in input_records}
    for profile in profiles:
        input_meta = metadata.get(str(profile.get("organisation_number") or ""), {})
        for key in ("evaluation_split", "sample_slice"):
            if input_meta.get(key) is not None:
                profile[key] = input_meta[key]

    baseline_profiles, baseline_metrics = baseline_website_discovery(
        profiles,
        site_timeout=site_timeout,
        wikidata_timeout=wikidata_timeout,
    )
    unresolved = [row for row in baseline_profiles if not _publishable_website(row)]
    if len(unresolved) < target_unresolved:
        raise RuntimeError(
            f"Fresh pool yielded only {len(unresolved)} unresolved companies; "
            f"need {target_unresolved}. Increase the fresh pool before consuming a qualification cohort."
        )
    selected = unresolved[:target_unresolved]

    write_jsonl(baseline_profiles_path, baseline_profiles)
    write_jsonl(unresolved_output_path, selected)

    selected_orgs = [str(row["organisation_number"]) for row in selected]
    report = {
        "schema_version": "signalpost-v9-m1c-unresolved-cohort-v1",
        "fresh_pool_companies": len(baseline_profiles),
        "target_unresolved": target_unresolved,
        "incumbent_resolved": baseline_metrics["resolved"],
        "incumbent_unresolved": baseline_metrics["unresolved"],
        "selected_unresolved": len(selected),
        "selected_organisation_numbers": selected_orgs,
        "registry_snapshot": bulk_metrics,
        "incumbent_website_discovery": baseline_metrics,
        "model_or_search_called": False,
        "fresh_cohort_consumed_by_this_step": len(baseline_profiles),
        "note": (
            "All fresh-pool companies become touched by incumbent website screening. "
            "Only the first target_unresolved companies with no publishable incumbent website may enter M1c model-search qualification."
        ),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a fresh incumbent-unresolved cohort for V9 M1c model-search qualification.")
    parser.add_argument("--organisations", required=True, help="Fresh disjoint pool JSONL")
    parser.add_argument("--bulk", required=True, help="Current BRREG bulk CSV")
    parser.add_argument("--baseline-profiles", required=True)
    parser.add_argument("--unresolved-output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--target-unresolved", type=int, default=20)
    parser.add_argument("--site-timeout", type=float, default=6.0)
    parser.add_argument("--wikidata-timeout", type=float, default=8.0)
    args = parser.parse_args()

    report = prepare(
        organisations_path=Path(args.organisations),
        bulk_path=Path(args.bulk),
        baseline_profiles_path=Path(args.baseline_profiles),
        unresolved_output_path=Path(args.unresolved_output),
        report_path=Path(args.report),
        target_unresolved=args.target_unresolved,
        site_timeout=args.site_timeout,
        wikidata_timeout=args.wikidata_timeout,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
