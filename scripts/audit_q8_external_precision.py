#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection
from norway_company_agent.evidence_visibility import audit_contract_rows
from norway_company_agent.external_precision_guard import project_external_precision_guard
from norway_company_agent.output_contract import validate_contract_object
from norway_company_agent.synthesis import build_company_synthesis, validate_company_synthesis


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _claim_key(claim: dict[str, Any]) -> str:
    return json.dumps(claim, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--expected-removed-claims", type=int, default=None)
    args = parser.parse_args()

    source = _rows(Path(args.input))
    projected: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    removed_evidence: list[dict[str, str]] = []

    for before in source:
        org = str(before.get("organisation_number") or "")
        guarded = project_external_precision_guard(before)

        before_claims = {_claim_key(item): item for item in (before.get("claims") or []) if isinstance(item, dict)}
        after_claims = {_claim_key(item): item for item in (guarded.get("claims") or []) if isinstance(item, dict)}
        added_claims = set(after_claims) - set(before_claims)
        if added_claims:
            raise SystemExit(f"precision guard added claims for {org}")
        for key in sorted(set(before_claims) - set(after_claims)):
            claim = before_claims[key]
            value = claim.get("value")
            removed.append(
                {
                    "organisation_number": org,
                    "field": str(claim.get("field") or ""),
                    "url": str(value.get("url") or "") if isinstance(value, dict) else "",
                    "title": str(value.get("title") or "") if isinstance(value, dict) else "",
                    "anchor_text": str(value.get("anchor_text") or "") if isinstance(value, dict) else "",
                }
            )

        before_evidence = {
            str(item.get("id")): item
            for item in (before.get("evidence") or [])
            if isinstance(item, dict) and item.get("id")
        }
        after_evidence = {
            str(item.get("id")): item
            for item in (guarded.get("evidence") or [])
            if isinstance(item, dict) and item.get("id")
        }
        added_evidence = set(after_evidence) - set(before_evidence)
        if added_evidence:
            raise SystemExit(f"precision guard added evidence for {org}: {sorted(added_evidence)}")
        for evidence_id in sorted(set(after_evidence)):
            if before_evidence[evidence_id] != after_evidence[evidence_id]:
                raise SystemExit(f"precision guard mutated retained evidence for {org} {evidence_id}")
        for evidence_id in sorted(set(before_evidence) - set(after_evidence)):
            removed_evidence.append({"organisation_number": org, "evidence_id": evidence_id})

        item = project_canonical_profile(guarded)
        item["synthesis"] = build_company_synthesis(item)
        contract_errors = validate_contract_object(item)
        canonical_errors = validate_canonical_projection(item)
        synthesis_errors = validate_company_synthesis(item)
        if contract_errors or canonical_errors or synthesis_errors:
            raise SystemExit(
                f"validation failure for {org}: contract={contract_errors[:3]} "
                f"canonical={canonical_errors[:3]} synthesis={synthesis_errors[:3]}"
            )
        projected.append(item)

    if args.expected_removed_claims is not None and len(removed) != args.expected_removed_claims:
        raise SystemExit(
            f"expected {args.expected_removed_claims} removed claims, observed {len(removed)}"
        )

    visibility = audit_contract_rows(projected)
    report = {
        "schema_version": "signalpost-q8-external-precision-consumed-replay-v1",
        "companies": len(projected),
        "network_requests_added": 0,
        "removed_claims": removed,
        "removed_claim_count": len(removed),
        "removed_evidence": removed_evidence,
        "removed_evidence_count": len(removed_evidence),
        "visibility": visibility,
    }
    _write_jsonl(Path(args.output), projected)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
