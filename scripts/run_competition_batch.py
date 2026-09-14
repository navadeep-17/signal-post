#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profile_complete_for_modules, profiles_from_bulk, read_organisation_inputs, terminal_envelope, validate_envelopes  # noqa: E402
from norway_company_agent.domain_discovery import (  # noqa: E402
    distinctive_legal_name_compact,
    qualify_registry_email_domain_identity,
    registry_email_domain_candidates,
    simple_two_label_domain_name,
)
from norway_company_agent.evidence import evidence, utc_now  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.official import fetch_official_modules  # noqa: E402
from norway_company_agent.website import fetch_website  # noqa: E402

BRREG_BULK_URL = "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def _registry_homepage(profile: dict[str, Any]) -> str:
    raw = profile.get("evidence", {}).get("registry", {}).get("value") or {}
    return str(raw.get("hjemmeside") or raw.get("Hjemmeside") or "").strip()


def _complete_for_requested_strategy(
    profile: dict[str, Any],
    requested_modules: list[str],
    *,
    enable_email_domain_discovery: bool,
) -> bool:
    if not profile_complete_for_modules(profile, requested_modules):
        return False
    if not enable_email_domain_discovery or "website" not in requested_modules:
        return True
    if _registry_homepage(profile):
        return True
    return "website_email_discovery" in profile.get("evidence", {})


def _discover_email_domain_website(
    profile: dict[str, Any],
    *,
    timeout: float,
    retry_timeout: float,
    max_candidates: int,
) -> tuple[dict[str, Any] | None, dict[str, Any], Counter[str]]:
    """Try H1a only when the registry has no website seed.

    Registry email domains are discovery hints, never identity evidence by themselves.
    Every candidate is independently fetched and must pass the hardened H1 page-level
    exact-entity guard before it can replace canonical website evidence.
    """
    totals = {"requests": 0, "bytes": 0, "latencies_ms": []}
    counts: Counter[str] = Counter()
    discovery = registry_email_domain_candidates(profile)
    reason = discovery.get("reason") or "unknown"
    if not discovery.get("eligible"):
        counts[reason] += 1
        profile.setdefault("evidence", {})["website_email_discovery"] = evidence(
            "website_email_discovery",
            "not_found",
            "official_registry_email_domain_discovery",
            BRREG_BULK_URL,
            value={
                "method": "brreg_registry_email_domain_then_independent_fetch_v3",
                "candidate_domains": [],
                "generic_domains_skipped": discovery.get("generic_domains", []),
                "selected_domain": None,
                "selected_url": None,
                "publishable": False,
                "reason": reason,
            },
            source_row_key=profile.get("organisation_number"),
            note="No eligible non-consumer registry email domain; no search provider used.",
        )
        return None, totals, counts

    counts["eligible_email_domain_profiles"] += 1
    selected: tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None = None
    candidate_summaries = []

    for candidate in discovery.get("candidates", [])[:max_candidates]:
        counts["candidate_domains"] += 1
        website, metrics = fetch_website(candidate["url"], timeout=timeout)

        def add_metrics(item: dict[str, Any]) -> None:
            totals["requests"] += int(item.get("requests") or 0)
            totals["bytes"] += int(item.get("bytes") or 0)
            totals["latencies_ms"].extend(int(value) for value in item.get("latencies_ms", []) if value is not None)

        add_metrics(metrics)

        def assess(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
            record["source_type"] = "registry_email_domain_candidate_website"
            record["source_class"] = "company_owned_candidate"
            gated = apply_website_identity_gate(profile, record)
            verified = gated["website"]
            base = gated.get("assessment")
            final = qualify_registry_email_domain_identity(profile, candidate["domain"], verified, base)
            if final is not base and final is not None:
                (verified.get("value") or {})["identity_assessment"] = final
            return verified, final

        verified_website, assessment = assess(website)
        exact_domain_name = (
            simple_two_label_domain_name(candidate["domain"])
            == distinctive_legal_name_compact(profile.get("name"))
            != ""
        )
        retried = False
        if retry_timeout > timeout and exact_domain_name and verified_website.get("status") == "source_error":
            retry_website, retry_metrics = fetch_website(candidate["url"], timeout=retry_timeout)
            add_metrics(retry_metrics)
            retried = True
            counts["long_timeout_retries"] += 1
            verified_website, assessment = assess(retry_website)

        identity_status = (assessment or {}).get("status")
        if identity_status:
            counts[f"identity_{identity_status}"] += 1
        counts[f"fetch_{verified_website.get('status') or 'unknown'}"] += 1
        candidate_summaries.append(
            {
                "domain": candidate["domain"],
                "requested_url": candidate["url"],
                "final_url": (verified_website.get("value") or {}).get("final_url") or verified_website.get("source_url"),
                "fetch_status": verified_website.get("status"),
                "identity_status": identity_status,
                "identity_score": (assessment or {}).get("score"),
                "identity_reasons": (assessment or {}).get("reasons") or [],
                "retried_with_long_timeout": retried,
            }
        )
        if assessment and assessment.get("publishable") and verified_website.get("status") == "available":
            selected = (candidate, verified_website, assessment)
            counts["verified_exact_sites"] += 1
            break

    discovery_value = {
        "method": "brreg_registry_email_domain_then_independent_fetch_v3",
        "candidate_domains": [item["domain"] for item in discovery.get("candidates", [])],
        "generic_domains_skipped": discovery.get("generic_domains", []),
        "selected_domain": selected[0]["domain"] if selected else None,
        "selected_url": ((selected[1].get("value") or {}).get("final_url") or selected[1].get("source_url")) if selected else None,
        "publishable": bool(selected),
        "candidates": candidate_summaries,
        "policy": "Registry email domains are candidates only; publication requires independently fetched page-level exact-entity evidence.",
    }
    profile.setdefault("evidence", {})["website_email_discovery"] = evidence(
        "website_email_discovery",
        "available" if selected else "not_found",
        "official_registry_email_domain_discovery",
        BRREG_BULK_URL,
        value=discovery_value,
        source_row_key=profile.get("organisation_number"),
        note="Candidate derived from public BRREG email field; no search provider used.",
    )

    if selected:
        _, selected_website, _ = selected
        profile["evidence"]["website_email_candidate"] = selected_website
        counts["promoted_sites"] += 1
        return selected_website, totals, counts

    if candidate_summaries:
        counts["quarantined_profiles"] += 1
    return None, totals, counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluator-owned Signalpost batch contract")
    parser.add_argument("--organisations", required=True, help="JSON, JSONL, or text organisation-number list")
    parser.add_argument("--bulk", required=True, help="Frozen Brreg entity snapshot")
    parser.add_argument("--output", required=True, help="Terminal envelope JSONL")
    parser.add_argument("--profiles-output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-count", type=int, default=100)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--modules", default="registry,accounting_obligation,registry_live,financials,roles,group,locations,website")
    parser.add_argument(
        "--enable-email-domain-discovery",
        action="store_true",
        help="Opt in to H1a for companies with no registry website. Off by default.",
    )
    parser.add_argument("--email-domain-timeout", type=float, default=8.0)
    parser.add_argument("--email-domain-retry-timeout", type=float, default=15.0)
    parser.add_argument("--email-domain-max-candidates", type=int, default=2)
    args = parser.parse_args()

    if args.email_domain_timeout <= 0 or args.email_domain_retry_timeout <= 0:
        parser.error("email-domain timeouts must be positive")
    if args.email_domain_max_candidates < 1 or args.email_domain_max_candidates > 4:
        parser.error("--email-domain-max-candidates must be between 1 and 4")

    started_at = utc_now()
    organisation_inputs = read_organisation_inputs(args.organisations)
    orgs = [item["organisation_number"] for item in organisation_inputs]
    if len(orgs) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} organisations, received {len(orgs)}")
    profiles, registry_metadata = profiles_from_bulk(args.bulk, orgs)
    annotations = {item["organisation_number"]: item for item in organisation_inputs}
    for profile in profiles:
        for key in ("evaluation_split", "sample_slice"):
            if key in annotations[profile["organisation_number"]]:
                profile[key] = annotations[profile["organisation_number"]][key]
    requested_modules = [item.strip() for item in args.modules.split(",") if item.strip()]
    fetch_modules = set(requested_modules) - {"registry", "accounting_obligation", "website"}
    operations = {"requests": 0, "bytes": 0, "latencies_ms": []}
    h1_counts: Counter[str] = Counter()

    def enrich(profile: dict) -> tuple[dict, dict, Counter[str]]:
        records, metrics = fetch_official_modules(profile["organisation_number"], fetch_modules)
        profile["evidence"].update(records)
        website_metrics = {"requests": 0, "bytes": 0, "latencies_ms": []}
        local_h1: Counter[str] = Counter()
        if "website" in requested_modules:
            website_record, website_metrics = fetch_website(profile.get("website"))
            profile["evidence"]["website"] = apply_website_identity_gate(profile, website_record)["website"]

            if args.enable_email_domain_discovery and not _registry_homepage(profile):
                discovered_website, h1_metrics, local_h1 = _discover_email_domain_website(
                    profile,
                    timeout=args.email_domain_timeout,
                    retry_timeout=args.email_domain_retry_timeout,
                    max_candidates=args.email_domain_max_candidates,
                )
                website_metrics = {
                    "requests": int(website_metrics.get("requests") or 0) + int(h1_metrics.get("requests") or 0),
                    "bytes": int(website_metrics.get("bytes") or 0) + int(h1_metrics.get("bytes") or 0),
                    "latencies_ms": [
                        *list(website_metrics.get("latencies_ms") or []),
                        *list(h1_metrics.get("latencies_ms") or []),
                    ],
                }
                if discovered_website is not None:
                    profile["evidence"]["website"] = discovered_website
                    profile["website"] = (discovered_website.get("value") or {}).get("final_url") or discovered_website.get("source_url") or ""

        metric = {
            "requests": len(metrics) + website_metrics["requests"],
            "bytes": sum(item.bytes_received for item in metrics) + website_metrics["bytes"],
            "latencies_ms": [item.elapsed_ms for item in metrics] + website_metrics["latencies_ms"],
        }
        profile["run_metrics"] = metric
        return profile, metric, local_h1

    state: dict[str, dict] = {}
    resumed_profiles = 0
    profiles_output = Path(args.profiles_output)
    if args.resume and profiles_output.exists():
        prior = [json.loads(line) for line in profiles_output.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not set(item["organisation_number"] for item in prior).issubset(set(orgs)):
            raise SystemExit("Resume profile membership is not a subset of this batch")
        state = {
            item["organisation_number"]: item
            for item in prior
            if _complete_for_requested_strategy(
                item,
                requested_modules,
                enable_email_domain_discovery=args.enable_email_domain_discovery,
            )
        }
        resumed_profiles = len(state)
    pending_profiles = [profile for profile in profiles if profile["organisation_number"] not in state]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(enrich, profile): profile["organisation_number"] for profile in pending_profiles}
        for index, future in enumerate(as_completed(futures), 1):
            profile, metric, local_h1 = future.result()
            state[profile["organisation_number"]] = profile
            h1_counts.update(local_h1)
            operations["requests"] += metric["requests"]
            operations["bytes"] += metric["bytes"]
            operations["latencies_ms"].extend(metric["latencies_ms"])
            if index % args.checkpoint_every == 0 or index == len(pending_profiles):
                checkpoint = [state[org] for org in orgs if org in state]
                write_jsonl(profiles_output, checkpoint)

    completed_at = utc_now()
    ordered_profiles = [state[org] for org in orgs]
    envelopes = [
        terminal_envelope(profile, run_id=args.run_id, modules=requested_modules, started_at=started_at, completed_at=completed_at)
        for profile in ordered_profiles
    ]
    validation = validate_envelopes(envelopes, args.expected_count)
    write_jsonl(profiles_output, ordered_profiles)
    write_jsonl(Path(args.output), envelopes)
    latencies = sorted(operations.pop("latencies_ms"))
    operations["p50_ms"] = latencies[len(latencies) // 2] if latencies else None
    operations["p95_ms"] = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else None
    report = {
        "run_id": args.run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "expected_count": args.expected_count,
        "emitted_envelopes": len(envelopes),
        "resumed_profiles": resumed_profiles,
        "profiles_fetched_this_run": len(pending_profiles),
        "modules": requested_modules,
        "registry": registry_metadata,
        "operations": operations,
        "h1_email_domain_discovery": {
            "enabled": args.enable_email_domain_discovery,
            "normal_timeout_seconds": args.email_domain_timeout,
            "retry_timeout_seconds": args.email_domain_retry_timeout,
            "max_candidates_per_company": args.email_domain_max_candidates,
            "counts": dict(sorted(h1_counts.items())),
            "third_party_cost_usd": 0.0,
            "search_provider_used": False,
        },
        "validation": validation,
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if validation["passed"] else 1)


if __name__ == "__main__":
    main()
