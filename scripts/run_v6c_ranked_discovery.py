#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.candidate_ranking import (  # noqa: E402
    ML_RANKER_ID,
    RULES_RANKER_ID,
    load_model,
    ranked_probe_plan,
)
from norway_company_agent.company_site_contact import company_site_contact_email_observations  # noqa: E402
from norway_company_agent.company_site_social import company_site_social_observations  # noqa: E402
from norway_company_agent.domain_discovery import (  # noqa: E402
    _page_contains_full_legal_name,
    _page_contains_org_number,
    _page_matches_registry_location,
)
from norway_company_agent.evidence import evidence, utc_now  # noqa: E402
from norway_company_agent.final_site_discovery import (  # noqa: E402
    BRREG_BULK_URL,
    _has_conflicting_explicit_org_number,
    _publishable,
    fetch_bounded_homepage,
)
from norway_company_agent.first_party_activity import extract_strict_first_party_facts  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.zero_cost_registry_guard import registry_risk_reasons  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def strict_candidate_identity(profile: dict, record: dict, assessment: dict | None) -> dict | None:
    """Narrow the existing website gate; ranking can never upgrade identity by itself."""
    if not assessment or not assessment.get("publishable") or record.get("status") != "available":
        return assessment
    reasons = list(assessment.get("reasons") or [])
    if _has_conflicting_explicit_org_number(profile, record):
        return {
            **assessment,
            "status": "review",
            "score": min(float(assessment.get("score") or 0.85), 0.85),
            "publishable": False,
            "reasons": [*reasons, "V6c candidate page explicitly identifies a conflicting organisation number"],
            "method": "v6c_ranked_candidate_identity_guard_v1",
        }
    if _page_contains_org_number(profile, record):
        narrowed = {
            **assessment,
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "reasons": [*reasons, "V6c independently fetched candidate contains exact target organisation number"],
            "method": "v6c_ranked_candidate_identity_guard_v1",
        }
    elif _page_contains_full_legal_name(profile, record) and _page_matches_registry_location(profile, record):
        narrowed = {
            **assessment,
            "status": "exact",
            "score": max(float(assessment.get("score") or 0.95), 0.98),
            "publishable": True,
            "reasons": [*reasons, "V6c candidate contains full legal name plus BRREG location corroboration"],
            "method": "v6c_ranked_candidate_identity_guard_v1",
        }
    else:
        return {
            **assessment,
            "status": "review",
            "score": min(float(assessment.get("score") or 0.85), 0.85),
            "publishable": False,
            "reasons": [*reasons, "V6c candidate lacks exact org-number or legal-name-plus-location proof"],
            "method": "v6c_ranked_candidate_identity_guard_v1",
        }

    risk = registry_risk_reasons(profile, record)
    if risk:
        return {
            **narrowed,
            "status": "review",
            "score": min(float(narrowed.get("score") or 0.85), 0.85),
            "publishable": False,
            "reasons": [*list(narrowed.get("reasons") or []), *risk],
            "method": "v6c_ranked_candidate_registry_risk_guard_v1",
        }
    return narrowed


def downstream_counts(profile: dict) -> dict[str, int]:
    activity = extract_strict_first_party_facts(profile)
    return {
        "contact_emails": len(company_site_contact_email_observations(profile)),
        "social_profiles": len(company_site_social_observations(profile)),
        "strict_jobs": len(activity.get("jobs") or []),
        "strict_updates": len(activity.get("updates") or []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="V6c ranked zero-cost candidate probes after the frozen V5 pipeline.")
    parser.add_argument("--input-profiles", required=True)
    parser.add_argument("--output-profiles", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--new-websites", required=True)
    parser.add_argument("--ranker", required=True, choices=[RULES_RANKER_ID, ML_RANKER_ID])
    parser.add_argument("--model")
    parser.add_argument("--max-probes", type=int, default=2, choices=[1, 2])
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--max-added-logical-requests", type=int, default=220)
    args = parser.parse_args()

    model = load_model(args.model) if args.ranker == ML_RANKER_ID else None
    rows = read_jsonl(Path(args.input_profiles))
    output: list[dict] = []
    new_sites: list[dict] = []
    attempted_probes = 0
    added_requests = 0
    added_bytes = 0
    top1_hits = 0
    top2_hits = 0
    unresolved = 0
    no_candidates = 0
    started = time.monotonic()
    downstream = {"contact_emails": 0, "social_profiles": 0, "strict_jobs": 0, "strict_updates": 0}

    for original in rows:
        row = deepcopy(original)
        website = (row.get("evidence") or {}).get("website") or {}
        if _publishable(website):
            output.append(row)
            continue
        unresolved += 1
        plan = ranked_probe_plan(row, ranker_id=args.ranker, model=model, max_probes=args.max_probes)
        probes = list(plan["probe_candidates"])
        if not probes:
            no_candidates += 1
            output.append(row)
            continue

        attempts: list[dict] = []
        verified_rank: int | None = None
        for candidate in probes:
            if added_requests + 2 > args.max_added_logical_requests:
                break
            attempted_probes += 1
            record, operations = fetch_bounded_homepage(
                candidate["url"],
                source_type=f"v6c_ranked_zero_cost_candidate:{args.ranker}",
                timeout=args.timeout,
            )
            reqs = int(operations.get("requests") or 0)
            added_requests += reqs
            added_bytes += int(operations.get("bytes") or 0)
            record["source_class"] = "company_owned_candidate"
            gated = apply_website_identity_gate(row, record)
            candidate_record = gated["website"]
            assessment = strict_candidate_identity(row, candidate_record, gated.get("assessment"))
            if assessment is not None:
                value = candidate_record.get("value") or {}
                value["identity_assessment"] = assessment
                candidate_record["value"] = value
            selected = bool(assessment and assessment.get("publishable") and candidate_record.get("status") == "available")
            attempts.append({
                "rank": candidate["rank"],
                "domain": candidate["domain"],
                "strategy": candidate["strategy"],
                "rank_score": candidate["rank_score"],
                "fetch_status": candidate_record.get("status"),
                "identity_status": (assessment or {}).get("status"),
                "identity_score": (assessment or {}).get("score"),
                "publishable": selected,
                "requests": reqs,
                "source_url": candidate_record.get("source_url"),
                "final_url": (candidate_record.get("value") or {}).get("final_url"),
                "identity_reasons": list((assessment or {}).get("reasons") or []),
            })
            if not selected:
                continue

            row.setdefault("evidence", {})["website"] = candidate_record
            row["website"] = (candidate_record.get("value") or {}).get("final_url") or candidate_record.get("source_url") or ""
            verified_rank = int(candidate["rank"])
            if verified_rank == 1:
                top1_hits += 1
            if verified_rank <= 2:
                top2_hits += 1
            unlocked = downstream_counts(row)
            for key, value in unlocked.items():
                downstream[key] += value
            new_sites.append({
                "organisation_number": row.get("organisation_number"),
                "name": row.get("name"),
                "municipality": row.get("municipality"),
                "ranker_id": args.ranker,
                "verified_rank": verified_rank,
                "candidate_domain": candidate["domain"],
                "candidate_strategy": candidate["strategy"],
                "rank_score": candidate["rank_score"],
                "selected_url": row.get("website"),
                "identity_assessment": assessment,
                "content_sha256": candidate_record.get("content_sha256") or (candidate_record.get("value") or {}).get("content_sha256"),
                "identity_text_excerpt": (candidate_record.get("value") or {}).get("identity_text_excerpt"),
                "main_text_excerpt": (candidate_record.get("value") or {}).get("main_text_excerpt"),
                "downstream_facts_unlocked": unlocked,
            })
            break

        row.setdefault("evidence", {})["website_v6c_candidate_ranking"] = evidence(
            "website_v6c_candidate_ranking",
            "available" if verified_rank is not None else "not_found",
            args.ranker,
            BRREG_BULK_URL,
            value={
                "ranker_id": args.ranker,
                "generated_candidate_count": len(plan["generated_candidates"]),
                "eligible_candidate_count": len(plan["eligible_candidates"]),
                "max_probes": args.max_probes,
                "verified_rank": verified_rank,
                "attempts": attempts,
                "ranking_is_evidence": False,
                "third_party_cost_usd": 0.0,
            },
            source_row_key=row.get("organisation_number"),
            note="V6c ranker nominated bounded zero-cost candidates; publication remained controlled by independently fetched exact-company identity evidence.",
        )
        output.append(row)

    write_jsonl(Path(args.output_profiles), output)
    write_jsonl(Path(args.new_websites), new_sites)
    elapsed = time.monotonic() - started
    report = {
        "generated_at": utc_now(),
        "ranker_id": args.ranker,
        "input_profiles": len(rows),
        "unresolved_profiles": unresolved,
        "profiles_without_eligible_candidates": no_candidates,
        "max_probes_per_unresolved": args.max_probes,
        "network_probes": attempted_probes,
        "net_new_verified_websites": len(new_sites),
        "top1_verified_site_hits": top1_hits,
        "top2_verified_site_hits": top2_hits,
        "top1_hit_rate_over_unresolved": top1_hits / unresolved if unresolved else 0.0,
        "top2_hit_rate_over_unresolved": top2_hits / unresolved if unresolved else 0.0,
        "logical_requests_added": added_requests,
        "conservative_request_charge_added": added_requests * 2,
        "bytes_added": added_bytes,
        "wall_runtime_seconds": round(elapsed, 3),
        "verified_websites_per_conservative_request": len(new_sites) / (added_requests * 2) if added_requests else 0.0,
        "third_party_api_cost_usd": 0.0,
        "downstream_facts_unlocked": downstream,
        "automatic_identity_conflicts_published": 0,
        "manual_wrong_company_audit": "required_for_every_net_new_site_before_promotion",
        "publication_policy": "Rank score is nomination only. Existing website identity gate plus exact-org or legal-name+BRREG-location proof is authoritative.",
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
