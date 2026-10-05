#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from norway_company_agent.canonical_projection import validate_canonical_projection
from norway_company_agent.evidence_visibility import audit_contract_rows
from norway_company_agent.output_contract import validate_contract_object
from norway_company_agent.synthesis import validate_company_synthesis

ROOT = Path(__file__).resolve().parents[1]

EXTERNAL_AUDIT_FIELDS = {
    "official_website",
    "external.contact_email",
    "external.profile_handle",
    "social_links",
    "external.careers_page",
    "external.job_posting",
    "external.company_update",
    "external.news_update",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    exclusion_path = ROOT / "q8-exclude-8623.jsonl"
    cohort_path = ROOT / "q8-fresh-100.jsonl"
    selection_path = ROOT / "q8-selection.json"
    output_path = ROOT / "out/q8-fresh-output.jsonl"
    report_path = ROOT / "out/q8-fresh-report.json"
    product_path = ROOT / "out/signalpost-q8-fresh.html"

    excluded = rows(exclusion_path)
    cohort = rows(cohort_path)
    output = rows(output_path)
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    html = product_path.read_text(encoding="utf-8")

    excluded_orgs = {str(row["organisation_number"]) for row in excluded}
    cohort_orgs = {str(row["organisation_number"]) for row in cohort}
    output_orgs = {str(row["organisation_number"]) for row in output}

    assert len(excluded) == len(excluded_orgs) == 8623
    assert len(cohort) == len(cohort_orgs) == 100
    assert not (excluded_orgs & cohort_orgs)
    assert selection["seed"] == 20261106, selection
    assert selection["count"] == 100, selection
    assert selection["excluded_rows"] == 8623, selection
    assert selection["overlap_count"] == 0, selection
    assert selection["exclude_manifest_sha256"] == digest(exclusion_path), selection
    assert selection["output_sha256"] == digest(cohort_path), selection

    assert report["passed"] is True, report
    assert len(output) == 100
    assert len(output_orgs) == 100
    assert output_orgs == cohort_orgs
    assert all((row.get("run") or {}).get("terminal_status") == "completed" for row in output)

    support_report = report.get("support_registry") or {}
    assert support_report.get("status") == "available", support_report
    assert int(support_report.get("requests") or 0) == 1, support_report
    assert len(str(support_report.get("source_snapshot_sha256") or "")) == 64, support_report

    budget = report.get("request_budget") or {}
    assert int(budget.get("support_registry_observed_logical_requests") or 0) == 1, budget
    assert int(budget.get("brreg_change_feed_observed_logical_requests") or 0) <= 1, budget
    assert int(budget.get("observed_conservative_challenge_request_charge") or 0) <= 2000, budget
    assert int(budget.get("theoretical_challenge_request_charge_ceiling") or 0) == 2000, budget

    assert not (report.get("canonical_projection") or {}).get("validation_errors"), report.get("canonical_projection")
    assert not (report.get("synthesis") or {}).get("validation_errors"), report.get("synthesis")
    assert not (report.get("registry_change_feed") or {}).get("integrity_errors"), report.get("registry_change_feed")
    support_errors = report.get("support_projection_errors") or {}
    assert not support_errors.get("contract"), support_errors
    assert not support_errors.get("canonical"), support_errors
    assert not support_errors.get("synthesis"), support_errors
    assert float((report.get("source_policy") or {}).get("third_party_cost_usd") or 0.0) == 0.0
    assert int((report.get("source_policy") or {}).get("search_api_requests") or 0) == 0
    assert float((report.get("runtime") or {}).get("wall_runtime_seconds") or 0) <= 2400

    contract_errors: list[tuple[str, str]] = []
    canonical_errors: list[tuple[str, str]] = []
    synthesis_errors: list[tuple[str, str]] = []
    dangling_evidence: list[tuple[str, str, str]] = []
    support_claims: list[tuple[str, dict]] = []
    support_facts: list[tuple[str, dict]] = []
    support_audit: list[dict] = []
    external_audit: list[dict] = []

    for row in output:
        org = str(row.get("organisation_number") or "")
        contract_errors.extend((org, error) for error in validate_contract_object(row))
        canonical_errors.extend((org, error) for error in validate_canonical_projection(row))
        synthesis_errors.extend((org, error) for error in validate_company_synthesis(row))

        evidence = {
            str(item.get("id")): item
            for item in (row.get("evidence") or [])
            if isinstance(item, dict) and item.get("id")
        }

        for claim in row.get("claims") or []:
            if not isinstance(claim, dict):
                continue
            refs = [str(ref) for ref in (claim.get("evidence_ids") or [])]
            field = str(claim.get("field") or "")
            for ref in refs:
                if ref not in evidence:
                    dangling_evidence.append((org, field, ref))

            if field == "official.support_award" and claim.get("availability") == "available":
                support_claims.append((org, claim))
                value = claim.get("value") or {}
                assert value.get("kind") == "support_award"
                assert value.get("awarded_at")
                if value.get("amount") is not None:
                    assert value.get("currency"), (org, value)
                if value.get("amount_interval_from") is not None or value.get("amount_interval_to") is not None:
                    assert value.get("amount_interval_currency"), (org, value)
                assert len(refs) == 1, (org, refs)
                ev = evidence[refs[0]]
                assert len(str(ev.get("content_sha256") or "")) == 64, ev
                assert len(str(ev.get("source_snapshot_sha256") or "")) == 64, ev
                assert ev.get("source_row_number") is not None, ev
                assert ev.get("source_row_key"), ev
                assert ev.get("retrieved_at"), ev
                assert ev.get("effective_at") == value.get("awarded_at"), (ev, value)
                assert ev.get("identity_proof"), ev
                assert ev.get("extraction_method") == "official_support_registry_primary_recipient_exact_org_v1", ev
                span = str(ev.get("claim_span") or "")
                assert f"recipient org: {org}" in span, (org, span)
                support_audit.append(
                    {
                        "organisation_number": org,
                        "recipient_name": value.get("recipient_name"),
                        "awarded_at": value.get("awarded_at"),
                        "support_measure_number": value.get("support_measure_number"),
                        "amount": value.get("amount"),
                        "currency": value.get("currency"),
                        "amount_interval_from": value.get("amount_interval_from"),
                        "amount_interval_to": value.get("amount_interval_to"),
                        "amount_interval_currency": value.get("amount_interval_currency"),
                        "source_url": ev.get("source_url"),
                        "row_sha256": ev.get("content_sha256"),
                        "snapshot_sha256": ev.get("source_snapshot_sha256"),
                        "source_row_number": ev.get("source_row_number"),
                        "source_row_key": ev.get("source_row_key"),
                        "retrieved_at": ev.get("retrieved_at"),
                        "identity_proof": ev.get("identity_proof"),
                        "extraction_method": ev.get("extraction_method"),
                        "claim_span": span,
                    }
                )

            if (
                field in EXTERNAL_AUDIT_FIELDS
                and claim.get("availability") == "available"
                and claim.get("value") not in (None, "", [], {})
            ):
                external_audit.append(
                    {
                        "organisation_number": org,
                        "field": field,
                        "value": claim.get("value"),
                        "confidence": claim.get("confidence"),
                        "claim_scope": claim.get("claim_scope"),
                        "platform": claim.get("platform"),
                        "signal_type": claim.get("signal_type"),
                        "evidence": [evidence.get(ref) for ref in refs],
                    }
                )

        for fact in row.get("canonical_facts") or []:
            if isinstance(fact, dict) and fact.get("canonical_field") == "public.official_support_award":
                support_facts.append((org, fact))

    assert not contract_errors, contract_errors[:5]
    assert not canonical_errors, canonical_errors[:5]
    assert not synthesis_errors, synthesis_errors[:5]
    assert not dangling_evidence, dangling_evidence[:5]
    assert len(support_claims) == len(support_facts), (len(support_claims), len(support_facts))

    projection = (report.get("canonical_projection") or {}).get("support_award_projection") or {}
    assert int(projection.get("published_claims") or 0) == len(support_claims), projection
    assert int(projection.get("published_canonical_facts") or 0) == len(support_facts), projection
    if support_claims:
        assert "public.official_support_award" in html

    visibility = audit_contract_rows(output)
    assert visibility["core_evidence_complete_claims"] == visibility["available_claims"], visibility
    assert visibility["reopenable_source_claims"] == visibility["available_claims"], visibility
    assert visibility["identity_proof_visible"] == visibility["identity_sensitive_claims"], visibility
    assert visibility["extraction_method_visible"] == visibility["identity_sensitive_claims"], visibility
    assert visibility["issues"] == [], visibility["issues"][:10]

    summary = {
        "schema_version": "signalpost-q8-fresh-release-qualification-v2",
        "qualification_sha": os.environ["QUALIFICATION_SHA"],
        "production_main_sha": os.environ["PRODUCTION_MAIN_SHA"],
        "selection_seed": selection["seed"],
        "excluded_companies": len(excluded_orgs),
        "exclude_sha256": digest(exclusion_path),
        "fresh_cohort_sha256": digest(cohort_path),
        "fresh_overlap_count": len(cohort_orgs & excluded_orgs),
        "input_companies": len(cohort),
        "terminal_completed": sum((row.get("run") or {}).get("terminal_status") == "completed" for row in output),
        "available_claims": visibility["available_claims"],
        "core_evidence_complete_claims": visibility["core_evidence_complete_claims"],
        "reopenable_source_claims": visibility["reopenable_source_claims"],
        "identity_sensitive_claims": visibility["identity_sensitive_claims"],
        "identity_proof_visible": visibility["identity_proof_visible"],
        "extraction_method_visible": visibility["extraction_method_visible"],
        "evidence_visibility_issues": len(visibility["issues"]),
        "support_companies": len({org for org, _ in support_claims}),
        "support_claims": len(support_claims),
        "support_canonical_facts": len(support_facts),
        "support_snapshot_sha256": support_report.get("source_snapshot_sha256"),
        "support_requests": int(support_report.get("requests") or 0),
        "support_bytes": int(support_report.get("bytes") or 0),
        "brreg_change_feed_requests": int(budget.get("brreg_change_feed_observed_logical_requests") or 0),
        "observed_conservative_request_charge": int(budget.get("observed_conservative_challenge_request_charge") or 0),
        "theoretical_conservative_request_ceiling": int(budget.get("theoretical_challenge_request_charge_ceiling") or 0),
        "wall_runtime_seconds": float((report.get("runtime") or {}).get("wall_runtime_seconds") or 0),
        "third_party_api_cost_usd": float((report.get("source_policy") or {}).get("third_party_cost_usd") or 0.0),
        "search_api_requests": int((report.get("source_policy") or {}).get("search_api_requests") or 0),
        "contract_errors": len(contract_errors),
        "canonical_errors": len(canonical_errors),
        "synthesis_errors": len(synthesis_errors),
        "dangling_evidence_refs": len(dangling_evidence),
        "support_projection_errors": sum(len(value or []) for value in support_errors.values()),
        "support_evidence_rows_for_manual_audit": len(support_audit),
        "external_publications_for_manual_audit": len(external_audit),
        "product_bytes": len(html.encode("utf-8")),
        "output_sha256": digest(output_path),
        "report_sha256": digest(report_path),
        "product_sha256": digest(product_path),
        "machine_gates_passed": True,
        "manual_precision_audit_required": True,
        "release_qualified": False,
    }

    (ROOT / "out/q8-support-audit.json").write_text(
        json.dumps(support_audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (ROOT / "out/q8-external-audit.json").write_text(
        json.dumps(external_audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (ROOT / "out/q8-evidence-visibility.json").write_text(
        json.dumps(visibility, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (ROOT / "out/q8-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
