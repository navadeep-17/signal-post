#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Any, TextIO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_measurement import publication_diff  # noqa: E402


def _open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with _open_text(path) as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{number}: expected JSON object")
            rows.append(row)
    return rows


def _identity_publishable(value: Any) -> bool:
    """Accept canonical verifier dicts and the typed, abbreviated exact-site proof.

    Contact/social projections encode exact site identity in a website_identity_gate
    proof entry containing status, score and verifier method but no redundant
    publishable flag. This branch only modifies the *audit*, never the verifier.
    """
    if isinstance(value, dict):
        if str(value.get("status") or "") == "exact":
            if value.get("publishable") is True:
                return bool(str(value.get("method") or "").strip())
            if value.get("publishable") is False:
                return False
            if value.get("type") == "website_identity_gate":
                try:
                    score = float(value.get("score"))
                except (TypeError, ValueError):
                    return False
                return 0.95 <= score <= 1.0 and bool(str(value.get("method") or "").strip())
        return any(_identity_publishable(child) for child in value.values())
    if isinstance(value, list):
        return any(_identity_publishable(child) for child in value)
    return False


def _supplemental_claim_precision(field: str, claim_value: Any, evidence_rows: list[dict[str, Any]]) -> bool:
    """Check the field-specific proof binding for recovered contact/social claims."""
    if field not in {
        "external.contact_email", "external.contact_phone", "external.profile_handle",
    }:
        return True
    for evidence in evidence_rows:
        proof = evidence.get("identity_proof")
        if not isinstance(proof, list):
            continue
        typed = {
            str(item.get("type") or ""): item
            for item in proof
            if isinstance(item, dict) and item.get("type")
        }
        if field == "external.contact_email":
            entry = typed.get("same_registered_domain_contact_email") or {}
            value = str(claim_value or "").strip().casefold()
            if (
                "@" in value
                and value.rsplit("@", 1)[-1] == str(entry.get("email_domain") or "").casefold()
                and str(entry.get("email_domain") or "").casefold()
                == str(entry.get("registered_domain") or "").casefold()
                and bool(entry.get("registered_domain"))
            ):
                return True
        elif field == "external.contact_phone":
            structured = typed.get("structured_organization_identity_gate") or {}
            phone = typed.get("structured_organization_telephone_field") or {}
            if (
                str(claim_value or "").startswith("+47")
                and str(structured.get("method") or "") in {
                    "structured_exact_organisation_number",
                    "structured_legal_name_token_match",
                }
                and phone.get("source_url") == evidence.get("source_url")
                and phone.get("content_sha256") == evidence.get("content_sha256")
                and bool(phone.get("source_url"))
            ):
                return True
        elif field == "external.profile_handle":
            homepage = (
                typed.get("company_homepage_declared_social_link")
                or typed.get("company_page_declared_social_link")
                or {}
            )
            provenance = typed.get("primary_homepage_provenance") or {}
            social = typed.get("social_handle_identity_gate") or {}
            direct = typed.get("direct_company_homepage_declaration_guard") or {}
            source_url = str(evidence.get("source_url") or "")
            content_hash = str(evidence.get("content_sha256") or "")
            declaration_bound = (
                homepage.get("profile_url") == claim_value
                and str(homepage.get("source_url") or source_url) == source_url
                and provenance.get("source_url") == source_url
                and provenance.get("content_sha256") == content_hash
                and bool(source_url)
                and len(content_hash) == 64
            )
            try:
                social_score = float(social.get("score") or 0)
            except (TypeError, ValueError):
                social_score = 0.0
            social_guard = (
                social_score >= 0.95
                and bool(str(social.get("method") or "").strip())
            )
            try:
                direct_score = float(direct.get("score") or 0)
            except (TypeError, ValueError):
                direct_score = 0.0
            direct_guard = (
                direct.get("profile_url") == claim_value
                and direct.get("source_url") == source_url
                and direct_score >= 0.95
                and str(direct.get("method") or "") in {
                    "deterministic_social_declaration_identity_v1",
                    "opaque_profile_identifier_on_exact_homepage_v1",
                }
                and str(direct.get("match_basis") or "") in {
                    "verified_site_brand",
                    "legal_name_tokens",
                    "opaque_platform_identifier",
                }
            )
            if declaration_bound and (social_guard or direct_guard):
                return True
    return False


def audit_new_publications(
    baseline_rows: list[dict[str, Any]],
    challenger_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    diff = publication_diff(baseline_rows, challenger_rows)
    manual_rows: list[dict[str, Any]] = []
    defects: list[dict[str, Any]] = []

    for item in diff["added"]:
        org = str(item.get("organisation_number") or "")
        field = str(item.get("field") or "")
        claim = item.get("claim") if isinstance(item.get("claim"), dict) else {}
        evidence_rows = [
            row for row in (item.get("evidence") or [])
            if isinstance(row, dict)
        ]

        checks = {
            "organisation_number_valid": len(org) == 9 and org.isdigit(),
            "claim_available": claim.get("availability") == "available",
            "claim_evidence_ids_present": bool(claim.get("evidence_ids")),
            "linked_evidence_present": bool(evidence_rows),
            "all_source_urls_present": bool(evidence_rows)
            and all(
                str(row.get("source_url") or "").startswith(("http://", "https://"))
                for row in evidence_rows
            ),
            "all_retrieved_at_present": bool(evidence_rows)
            and all(bool(str(row.get("retrieved_at") or "").strip()) for row in evidence_rows),
            "all_claim_spans_present": bool(evidence_rows)
            and all(bool(str(row.get("claim_span") or "").strip()) for row in evidence_rows),
            "all_content_hashes_present": bool(evidence_rows)
            and all(len(str(row.get("content_sha256") or "")) == 64 for row in evidence_rows),
            "identity_proof_present": bool(evidence_rows)
            and all(bool(row.get("identity_proof")) for row in evidence_rows),
            "exact_publishable_identity_present": any(
                _identity_publishable(row.get("identity_proof")) for row in evidence_rows
            ),
            "field_specific_identity_scope_proof": _supplemental_claim_precision(
                field, item.get("value"), evidence_rows
            ),
        }
        row = {
            "organisation_number": org,
            "field": field,
            "value": item.get("value"),
            "claim_scope": claim.get("claim_scope"),
            "platform": claim.get("platform"),
            "signal_type": claim.get("signal_type"),
            "checks": checks,
            "evidence": evidence_rows,
            "manual_exact_entity_review_required": True,
            "manual_semantic_scope_review_required": True,
        }
        manual_rows.append(row)
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            defects.append(
                {
                    "organisation_number": org,
                    "field": field,
                    "failed_checks": failed,
                }
            )

    report = {
        "screen_type": "v9_m10_new_publication_evidence_audit",
        "new_publications": len(diff["added"]),
        "lost_publications": len(diff["lost"]),
        "new_publication_companies": len(
            {str(item.get("organisation_number") or "") for item in diff["added"]}
        ),
        "evidence_defects": len(defects),
        "defects": defects,
        "all_new_publication_evidence_complete": not defects,
        "manual_review_rows": len(manual_rows),
        "manual_review_required_for_every_new_publication": True,
        "network_requests_added_by_audit": 0,
    }
    return report, manual_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--challenger", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manual-audit", type=Path, required=True)
    args = parser.parse_args()

    report, manual = audit_new_publications(
        read_jsonl(args.baseline),
        read_jsonl(args.challenger),
    )
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
    print("--- M10 manual audit rows ---")
    for row in manual:
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
