#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from norway_company_agent.evidence_visibility import audit_contract_rows
from norway_company_agent.first_party_activity_provenance import (
    project_first_party_activity_provenance,
)


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--expected-changed-evidence", type=int, default=None)
    args = parser.parse_args()

    source = _rows(Path(args.input))
    projected = [project_first_party_activity_provenance(row) for row in source]
    if len(source) != len(projected):
        raise SystemExit("row count changed")

    changed: list[dict[str, Any]] = []
    for before, after in zip(source, projected, strict=True):
        org = str(before.get("organisation_number") or "")
        if before.get("claims") != after.get("claims"):
            raise SystemExit(f"claims changed for {org}")
        before_evidence = {
            str(item.get("id")): item
            for item in (before.get("evidence") or [])
            if isinstance(item, dict) and item.get("id")
        }
        after_evidence = {
            str(item.get("id")): item
            for item in (after.get("evidence") or [])
            if isinstance(item, dict) and item.get("id")
        }
        if set(before_evidence) != set(after_evidence):
            raise SystemExit(f"evidence ids changed for {org}")
        for evidence_id in sorted(before_evidence):
            old = before_evidence[evidence_id]
            new = after_evidence[evidence_id]
            if old == new:
                continue
            old_without = copy.deepcopy(old)
            new_without = copy.deepcopy(new)
            identity = new_without.pop("identity_proof", None)
            method = new_without.pop("extraction_method", None)
            old_without.pop("identity_proof", None)
            old_without.pop("extraction_method", None)
            if old_without != new_without:
                raise SystemExit(f"non-provenance evidence fields changed for {org} {evidence_id}")
            if old.get("identity_proof") not in (None, "") or old.get("extraction_method") not in (None, ""):
                raise SystemExit(f"existing provenance unexpectedly changed for {org} {evidence_id}")
            if identity in (None, "") or method in (None, ""):
                raise SystemExit(f"incomplete provenance repair for {org} {evidence_id}")
            changed.append(
                {
                    "organisation_number": org,
                    "evidence_id": evidence_id,
                    "identity_proof": identity,
                    "extraction_method": method,
                }
            )

    if args.expected_changed_evidence is not None and len(changed) != args.expected_changed_evidence:
        raise SystemExit(
            f"expected {args.expected_changed_evidence} changed evidence rows, observed {len(changed)}"
        )

    visibility = audit_contract_rows(projected)
    report = {
        "schema_version": "signalpost-q8-first-party-activity-provenance-replay-v1",
        "companies": len(projected),
        "claims_unchanged": True,
        "evidence_ids_unchanged": True,
        "changed_evidence_rows": len(changed),
        "changes": changed,
        "visibility": visibility,
        "network_requests_added": 0,
    }
    _write_jsonl(Path(args.output), projected)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
