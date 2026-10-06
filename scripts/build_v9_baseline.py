#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

TARGET_FIELDS = {
    "verified_website_companies": "official_website",
    "social_profile_companies": "external.profile_handle",
    "contact_email_companies": "external.contact_email",
    "careers_surface_companies": "external.careers_page",
    "specific_job_companies": "external.job_posting",
    "dated_activity_companies": "external.company_update",
}


def _open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with _open_text(path) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    path.write_text(rendered, encoding="utf-8")
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _claims(row: dict[str, Any], field: str) -> list[dict[str, Any]]:
    return [
        claim
        for claim in row.get("claims") or []
        if isinstance(claim, dict)
        and claim.get("field") == field
        and claim.get("availability") == "available"
        and claim.get("value") is not None
    ]


def _company_has(row: dict[str, Any], field: str) -> bool:
    return bool(_claims(row, field))


def _family_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {"companies": len(rows)}
    for metric_name, field in TARGET_FIELDS.items():
        metrics[metric_name] = sum(_company_has(row, field) for row in rows)

    metrics["social_link_aggregate_companies"] = sum(
        _company_has(row, "social_links") for row in rows
    )
    metrics["target_family_available_claims"] = {
        field: sum(len(_claims(row, field)) for row in rows)
        for field in TARGET_FIELDS.values()
    }

    website_states = {
        "available": 0,
        "ambiguous": 0,
        "blocked": 0,
        "not_available": 0,
        "failed": 0,
        "missing_claim": 0,
    }
    for row in rows:
        claims = [
            claim
            for claim in row.get("claims") or []
            if isinstance(claim, dict) and claim.get("field") == "official_website"
        ]
        if not claims:
            website_states["missing_claim"] += 1
            continue
        states = {str(claim.get("availability") or "") for claim in claims}
        if "available" in states and any(claim.get("value") is not None for claim in claims):
            website_states["available"] += 1
            continue
        preferred = next(
            (
                state
                for state in ("ambiguous", "blocked", "not_available", "failed")
                if state in states
            ),
            "failed",
        )
        website_states[preferred] += 1
    metrics["website_resolution_states"] = website_states
    return metrics


def _run_metrics(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {
            "observed_conservative_requests": None,
            "theoretical_conservative_request_ceiling": None,
            "wall_runtime_seconds": None,
            "third_party_api_cost_usd": None,
            "search_api_requests": None,
        }

    request_budget = report.get("request_budget") or {}
    runtime = report.get("runtime") or {}
    source_policy = report.get("source_policy") or {}
    operations = report.get("operations") or {}

    return {
        "observed_conservative_requests": request_budget.get(
            "observed_conservative_challenge_request_charge",
            operations.get("observed_conservative_request_charge"),
        ),
        "theoretical_conservative_request_ceiling": request_budget.get(
            "theoretical_challenge_request_charge_ceiling",
            operations.get("theoretical_conservative_request_ceiling"),
        ),
        "wall_runtime_seconds": runtime.get(
            "wall_runtime_seconds",
            operations.get("wall_runtime_seconds"),
        ),
        "third_party_api_cost_usd": source_policy.get(
            "third_party_cost_usd",
            operations.get("third_party_api_cost_usd"),
        ),
        "search_api_requests": source_policy.get(
            "search_api_requests",
            operations.get("search_api_requests"),
        ),
    }


def _stable_rank(seed: str, organisation_number: str) -> str:
    return hashlib.sha256(f"{seed}|{organisation_number}".encode("utf-8")).hexdigest()


def _manifest_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        org = str(row.get("organisation_number") or "").strip()
        if not org:
            raise ValueError("manifest row missing organisation_number")
        if org in index:
            raise ValueError(f"duplicate organisation_number in manifest: {org}")
        index[org] = row
    return index


def _output_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        org = str(row.get("organisation_number") or "").strip()
        if not org:
            raise ValueError("output row missing organisation_number")
        if org in index:
            raise ValueError(f"duplicate organisation_number in output: {org}")
        index[org] = row
    return index


def _selected_manifest_rows(
    *,
    manifest_index: dict[str, dict[str, Any]],
    organisations: list[str],
) -> list[dict[str, Any]]:
    missing = [org for org in organisations if org not in manifest_index]
    if missing:
        raise ValueError(f"selected organisations missing from manifest: {missing[:5]}")
    return [manifest_index[org] for org in organisations]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build the Signalpost V9 consumed/dev website-recall baseline and deterministic "
            "unresolved-site Gate A cohort without consuming fresh companies."
        )
    )
    parser.add_argument("--output-contract", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--run-report")
    parser.add_argument("--unresolved-manifest", required=True)
    parser.add_argument("--gate-a-manifest", required=True)
    parser.add_argument("--seed", default="v9-baseline-20261006")
    parser.add_argument("--gate-a-size", type=int, default=20)
    parser.add_argument("--expected-companies", type=int, default=None)
    args = parser.parse_args()

    if args.gate_a_size < 1:
        raise SystemExit("--gate-a-size must be positive")

    outputs = _read_jsonl(Path(args.output_contract))
    manifest = _read_jsonl(Path(args.manifest))
    if args.expected_companies is not None and len(outputs) != args.expected_companies:
        raise SystemExit(
            f"expected {args.expected_companies} output companies, observed {len(outputs)}"
        )

    outputs_by_org = _output_index(outputs)
    manifest_by_org = _manifest_index(manifest)
    if set(outputs_by_org) != set(manifest_by_org):
        only_output = sorted(set(outputs_by_org) - set(manifest_by_org))
        only_manifest = sorted(set(manifest_by_org) - set(outputs_by_org))
        raise SystemExit(
            "output/manifest company sets differ: "
            f"only_output={only_output[:5]} only_manifest={only_manifest[:5]}"
        )

    unresolved = [
        org
        for org, row in outputs_by_org.items()
        if not _company_has(row, "official_website")
    ]
    unresolved.sort(key=lambda org: (_stable_rank(args.seed, org), org))
    if len(unresolved) < args.gate_a_size:
        raise SystemExit(
            f"need at least {args.gate_a_size} unresolved companies, observed {len(unresolved)}"
        )

    gate_a_orgs = unresolved[: args.gate_a_size]
    unresolved_rows = _selected_manifest_rows(
        manifest_index=manifest_by_org,
        organisations=unresolved,
    )
    gate_a_rows = _selected_manifest_rows(
        manifest_index=manifest_by_org,
        organisations=gate_a_orgs,
    )

    unresolved_sha = _write_jsonl(Path(args.unresolved_manifest), unresolved_rows)
    gate_a_sha = _write_jsonl(Path(args.gate_a_manifest), gate_a_rows)

    run_report = (
        json.loads(Path(args.run_report).read_text(encoding="utf-8"))
        if args.run_report
        else None
    )
    gate_a_outputs = [outputs_by_org[org] for org in gate_a_orgs]
    baseline = {
        "schema_version": "signalpost-v9-baseline-v1",
        "corpus_policy": {
            "kind": "consumed_dev",
            "fresh_qualification_credit": False,
            "selection_seed": args.seed,
            "source_company_count": len(outputs),
            "unresolved_company_count": len(unresolved),
            "gate_a_company_count": len(gate_a_orgs),
            "unresolved_manifest_sha256": unresolved_sha,
            "gate_a_manifest_sha256": gate_a_sha,
        },
        "source_100_metrics": _family_metrics(outputs),
        "gate_a_unresolved_metrics": _family_metrics(gate_a_outputs),
        "operations": _run_metrics(run_report),
        "manual_precision": {
            "wrong_company_publications": None,
            "evidence_defects": None,
            "status": "not_audited_by_this_offline_harness",
            "note": (
                "The harness measures published-family coverage and machine states only. "
                "Wrong-company and evidence-defect counts require the existing manual/evidence audit gates."
            ),
        },
        "gate_a_organisations": gate_a_orgs,
    }

    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(baseline, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
