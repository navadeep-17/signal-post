#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.domain_discovery import registry_email_domain_candidates  # noqa: E402
from norway_company_agent.evidence import evidence, utc_now  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.website import fetch_website  # noqa: E402

BRREG_BULK_URL = "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "H1a experiment: derive candidate company domains from public BRREG email domains, "
            "then independently fetch and exact-entity verify them."
        )
    )
    parser.add_argument("--input", required=True, help="Baseline profile JSONL")
    parser.add_argument("--output", required=True, help="Enriched profile JSONL")
    parser.add_argument("--predictions", required=True, help="Compact per-company H1a prediction JSONL")
    parser.add_argument("--report", required=True)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--limit", type=int, default=0, help="0 means all eligible profiles")
    parser.add_argument("--max-candidates-per-company", type=int, default=2)
    parser.add_argument(
        "--promote-verified",
        action="store_true",
        help="Copy only exact independently verified sites into canonical website evidence/top-level website.",
    )
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit cannot be negative")
    if args.max_candidates_per_company < 1:
        parser.error("--max-candidates-per-company must be positive")

    rows = read_jsonl(Path(args.input))
    predictions: list[dict] = []
    counts: Counter[str] = Counter()
    latencies: list[int] = []
    requests = 0
    bytes_received = 0
    queried = 0
    started_at = utc_now()

    for row in rows:
        discovery = registry_email_domain_candidates(row)
        reason = discovery.get("reason") or "unknown"
        if not discovery.get("eligible"):
            counts[reason] += 1
            continue
        if args.limit and queried >= args.limit:
            counts["eligible_not_run_due_to_limit"] += 1
            continue

        queried += 1
        counts["eligible_email_domain_profiles"] += 1
        candidate_results = []
        selected = None
        for candidate in discovery.get("candidates", [])[: args.max_candidates_per_company]:
            counts["candidate_domains"] += 1
            website, metrics = fetch_website(candidate["url"], timeout=args.timeout)
            requests += int(metrics.get("requests") or 0)
            bytes_received += int(metrics.get("bytes") or 0)
            latencies.extend(int(value) for value in metrics.get("latencies_ms", []) if value is not None)

            website["source_type"] = "registry_email_domain_candidate_website"
            website["source_class"] = "company_owned_candidate"
            gated = apply_website_identity_gate(row, website)
            verified_website = gated["website"]
            assessment = gated.get("assessment")
            final_url = ((verified_website.get("value") or {}).get("final_url") or verified_website.get("source_url"))
            result = {
                "domain": candidate["domain"],
                "requested_url": candidate["url"],
                "final_url": final_url,
                "fetch_status": verified_website.get("status"),
                "identity": assessment,
                "requests": int(metrics.get("requests") or 0),
                "bytes": int(metrics.get("bytes") or 0),
                "content_sha256": verified_website.get("content_sha256"),
            }
            candidate_results.append(result)
            counts[f"fetch_{verified_website.get('status') or 'unknown'}"] += 1
            identity_status = (assessment or {}).get("status")
            if identity_status:
                counts[f"identity_{identity_status}"] += 1

            if assessment and assessment.get("publishable") and verified_website.get("status") == "available":
                selected = (candidate, verified_website, assessment)
                counts["verified_exact_sites"] += 1
                break

        discovery_value = {
            "method": "brreg_registry_email_domain_then_independent_fetch_v1",
            "candidate_domains": [item["domain"] for item in discovery.get("candidates", [])],
            "generic_domains_skipped": discovery.get("generic_domains", []),
            "selected_domain": selected[0]["domain"] if selected else None,
            "selected_url": (selected[1].get("value") or {}).get("final_url") if selected else None,
            "publishable": bool(selected),
            "policy": "Registry email domains are candidates only; publication requires independently fetched exact-entity evidence.",
        }
        row.setdefault("evidence", {})["website_email_discovery"] = evidence(
            "website_email_discovery",
            "available" if selected else "not_found",
            "official_registry_email_domain_discovery",
            BRREG_BULK_URL,
            value=discovery_value,
            source_row_key=row.get("organisation_number"),
            note="Candidate derived from public BRREG email field; no search provider used.",
        )

        if selected:
            candidate, verified_website, assessment = selected
            row["evidence"]["website_email_candidate"] = verified_website
            if args.promote_verified:
                row["evidence"]["website"] = verified_website
                row["website"] = (verified_website.get("value") or {}).get("final_url") or verified_website.get("source_url") or ""
                counts["promoted_sites"] += 1
        elif candidate_results:
            # Retain the last independently fetched candidate only for audit. It remains quarantined.
            last = candidate_results[-1]
            counts["quarantined_profiles"] += 1

        predictions.append(
            {
                "organisation_number": row.get("organisation_number"),
                "name": row.get("name"),
                "municipality": row.get("municipality"),
                "candidate_results": candidate_results,
                "selected_domain": selected[0]["domain"] if selected else None,
                "selected_url": (selected[1].get("value") or {}).get("final_url") if selected else None,
                "identity_status": selected[2].get("status") if selected else None,
                "identity_score": selected[2].get("score") if selected else None,
                "identity_reasons": selected[2].get("reasons") if selected else [],
                "publishable_by_gate": bool(selected),
            }
        )

    write_jsonl(Path(args.output), rows)
    write_jsonl(Path(args.predictions), predictions)

    report = {
        "generated_at": utc_now(),
        "started_at": started_at,
        "method": "H1a registry email domain -> independent website fetch -> exact entity gate",
        "input_profiles": len(rows),
        "queried_profiles": queried,
        "counts": dict(sorted(counts.items())),
        "operations": {
            "requests": requests,
            "bytes": bytes_received,
            "p50_ms": percentile(latencies, 0.50),
            "p95_ms": percentile(latencies, 0.95),
            "mean_ms": round(statistics.fmean(latencies), 2) if latencies else None,
            "third_party_cost_usd": 0.0,
        },
        "raw_search_results_persisted": False,
        "search_provider_used": False,
        "promote_verified_enabled": args.promote_verified,
        "qualification": "experiment_only_pending_human_exact_domain_audit_and_zero_overlap_validation",
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
