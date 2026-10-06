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
    if isinstance(value, dict):
        if value.get("publishable") is True and str(value.get("status") or "") == "exact":
            return True
        return any(_identity_publishable(child) for child in value.values())
    if isinstance(value, list):
        return any(_identity_publishable(child) for child in value)
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
