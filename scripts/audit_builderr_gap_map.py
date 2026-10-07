#!/usr/bin/env python3
"""Read-only gap map for Builderr-scored Signalpost coverage.

This script never performs network access. It inspects a frozen evaluator artifact and
reports company-level coverage, fact counts and evidence completeness for the material
external families Builderr has called out: website, social, hiring/jobs and dated activity.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


EXTERNAL_GROUPS: dict[str, frozenset[str]] = {
    "verified_website": frozenset({"official_website"}),
    "social_profile": frozenset({"external.profile_handle"}),
    "careers_surface": frozenset({"external.careers_page"}),
    "hiring_intent": frozenset({"external.hiring_intent"}),
    "job_posting": frozenset({"external.job_posting"}),
    "dated_company_update": frozenset({"external.company_update"}),
    "external_contact": frozenset({"external.contact_email", "external.contact_phone"}),
}

ALL_MATERIAL_FIELDS = frozenset().union(*EXTERNAL_GROUPS.values())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{lineno}: JSON object expected")
        rows.append(item)
    return rows


def _looks_like_contract_rows(rows: list[dict[str, Any]]) -> bool:
    return (
        len(rows) == 100
        and all(
            isinstance(row.get("organisation_number"), (str, int))
            and isinstance(row.get("claims"), list)
            and isinstance(row.get("evidence"), list)
            for row in rows
        )
    )


def find_contract_file(root: Path) -> tuple[Path, list[dict[str, Any]]]:
    candidates: list[tuple[int, str, Path, list[dict[str, Any]]]] = []
    for path in sorted(root.rglob("*.jsonl")):
        try:
            rows = _read_jsonl(path)
        except Exception:
            continue
        if not _looks_like_contract_rows(rows):
            continue
        claim_count = sum(len(row.get("claims") or []) for row in rows)
        candidates.append((claim_count, str(path), path, rows))
    if not candidates:
        raise ValueError(f"no 100-row evaluator contract JSONL found under {root}")
    candidates.sort(key=lambda item: (-item[0], item[1]))
    _, _, path, rows = candidates[0]
    return path, rows


def _available_claims(row: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for claim in row.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        if claim.get("availability") != "available":
            continue
        if claim.get("value") in (None, ""):
            continue
        yield claim


def _evidence_index(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in (row.get("evidence") or [])
        if isinstance(item, dict) and item.get("id")
    }


def _external_evidence_complete(
    claim: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    ids = [str(x) for x in (claim.get("evidence_ids") or []) if str(x)]
    if not ids:
        return False, ["missing_evidence_ids"]
    for evidence_id in ids:
        ev = evidence_by_id.get(evidence_id)
        if ev is None:
            reasons.append(f"missing_evidence:{evidence_id}")
            continue
        for key in ("source_url", "retrieved_at", "claim_span"):
            if not str(ev.get(key) or "").strip():
                reasons.append(f"{evidence_id}:missing_{key}")
        digest = str(ev.get("content_sha256") or "").strip()
        if len(digest) != 64:
            reasons.append(f"{evidence_id}:missing_or_invalid_content_sha256")
        if claim.get("field") in ALL_MATERIAL_FIELDS:
            if not ev.get("identity_proof"):
                reasons.append(f"{evidence_id}:missing_identity_proof")
            if not str(ev.get("extraction_method") or "").strip():
                reasons.append(f"{evidence_id}:missing_extraction_method")
    return not reasons, reasons


def audit(rows: list[dict[str, Any]], *, source_file: str) -> dict[str, Any]:
    if len(rows) != 100:
        raise ValueError(f"expected exactly 100 rows, got {len(rows)}")

    orgs = [str(row.get("organisation_number") or "") for row in rows]
    if any(len(org) != 9 or not org.isdigit() for org in orgs):
        raise ValueError("all organisation numbers must be nine digits")
    if len(set(orgs)) != 100:
        raise ValueError("organisation numbers must be unique")

    field_fact_counts: Counter[str] = Counter()
    field_company_sets: dict[str, set[str]] = defaultdict(set)
    group_company_sets: dict[str, set[str]] = {name: set() for name in EXTERNAL_GROUPS}
    group_fact_counts: Counter[str] = Counter()
    evidence_issues: list[dict[str, Any]] = []
    careers_only_companies: list[str] = []
    careers_only_synthesis_evidence_missing: list[str] = []

    total_available_claims = 0
    material_external_claims = 0
    material_external_complete = 0

    for row in rows:
        org = str(row["organisation_number"])
        evidence_by_id = _evidence_index(row)
        fields_for_org: set[str] = set()

        for claim in _available_claims(row):
            total_available_claims += 1
            field = str(claim.get("field") or "")
            fields_for_org.add(field)
            field_fact_counts[field] += 1
            field_company_sets[field].add(org)

            for group, group_fields in EXTERNAL_GROUPS.items():
                if field in group_fields:
                    group_company_sets[group].add(org)
                    group_fact_counts[group] += 1

            if field in ALL_MATERIAL_FIELDS:
                material_external_claims += 1
                complete, reasons = _external_evidence_complete(claim, evidence_by_id)
                if complete:
                    material_external_complete += 1
                else:
                    evidence_issues.append(
                        {
                            "organisation_number": org,
                            "field": field,
                            "value": claim.get("value"),
                            "reasons": reasons,
                        }
                    )

        has_careers = "external.careers_page" in fields_for_org
        has_stricter_hiring = bool(
            fields_for_org.intersection({"external.hiring_intent", "external.job_posting"})
        )
        if has_careers and not has_stricter_hiring:
            careers_only_companies.append(org)
            hiring_item = (
                (((row.get("synthesis") or {}).get("decision_brief") or {}).get("hiring") or {})
            )
            if not (hiring_item.get("evidence") or []):
                careers_only_synthesis_evidence_missing.append(org)

    coverage = {
        group: {
            "companies": len(group_company_sets[group]),
            "company_rate": round(len(group_company_sets[group]) / len(rows), 4),
            "facts": int(group_fact_counts[group]),
            "organisation_numbers": sorted(group_company_sets[group]),
        }
        for group in EXTERNAL_GROUPS
    }

    return {
        "audit": "builderr_gap_map_v1",
        "source_file": source_file,
        "companies": len(rows),
        "total_available_claims": total_available_claims,
        "material_external_claims": material_external_claims,
        "material_external_evidence_complete": material_external_complete,
        "material_external_evidence_completeness_rate": (
            round(material_external_complete / material_external_claims, 6)
            if material_external_claims
            else 1.0
        ),
        "material_external_evidence_issues": len(evidence_issues),
        "coverage": coverage,
        "careers_only": {
            "companies": len(careers_only_companies),
            "organisation_numbers": sorted(careers_only_companies),
            "decision_brief_without_careers_evidence": len(
                careers_only_synthesis_evidence_missing
            ),
            "decision_brief_without_careers_evidence_orgs": sorted(
                careers_only_synthesis_evidence_missing
            ),
        },
        "top_available_fields": [
            {
                "field": field,
                "facts": int(count),
                "companies": len(field_company_sets[field]),
            }
            for field, count in field_fact_counts.most_common(40)
        ],
        "evidence_issues": evidence_issues,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--artifact-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()

    source_file, rows = find_contract_file(args.artifact_dir)
    report = audit(rows, source_file=str(source_file))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
