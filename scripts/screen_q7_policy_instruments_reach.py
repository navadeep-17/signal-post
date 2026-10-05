#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def target_orgs(profiles: list[dict[str, Any]]) -> set[str]:
    values: set[str] = set()
    for profile in profiles:
        org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
        if len(org) == 9:
            values.add(org)
    return values


def existing_support_orgs(contracts: list[dict[str, Any]]) -> set[str]:
    values: set[str] = set()
    for contract in contracts:
        org = re.sub(r"\D", "", str(contract.get("organisation_number") or ""))
        if len(org) != 9:
            continue
        if any(
            isinstance(claim, dict)
            and claim.get("availability") == "available"
            and claim.get("field") == "official.support_award"
            for claim in (contract.get("claims") or [])
        ):
            values.add(org)
    return values


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_csv(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode CSV")


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def choose_column(fieldnames: list[str], aliases: tuple[str, ...]) -> str | None:
    normalized = {norm(name): name for name in fieldnames}
    for alias in aliases:
        if norm(alias) in normalized:
            return normalized[norm(alias)]
    for alias in aliases:
        needle = norm(alias)
        for folded, original in normalized.items():
            if needle and needle in folded:
                return original
    return None


def parse_date(value: Any) -> date | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    compact = re.sub(r"\D", "", text)
    if len(compact) == 8 and compact[:4].isdigit():
        try:
            return date(int(compact[:4]), int(compact[4:6]), int(compact[6:8]))
        except ValueError:
            pass
    for candidate in (text, text[:10]):
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00")).date()
        except ValueError:
            pass
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def parse_float(value: Any) -> float | None:
    text = str(value or "").strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    text = re.sub(r"[^0-9.\-]", "", text)
    try:
        return float(text)
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Consumed-only exact-org reach screen for the open consolidated Norwegian policy-support dataset."
    )
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output-contract", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--as-of", default="2026-10-05")
    parser.add_argument("--recent-years", type=int, default=5)
    parser.add_argument("--sample-limit", type=int, default=12)
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of)
    cutoff = date(as_of.year - args.recent_years, as_of.month, as_of.day)
    profiles = read_jsonl(Path(args.profiles))
    contracts = read_jsonl(Path(args.output_contract))
    targets = target_orgs(profiles)
    incumbent_support = existing_support_orgs(contracts)
    if not targets:
        raise SystemExit("No valid target organisation numbers")

    dataset_path = Path(args.dataset)
    text, encoding = decode_csv(dataset_path)
    sample = text[:100_000]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    fields = list(reader.fieldnames or [])

    org_col = choose_column(fields, ("orgnr", "organisasjonsnummer"))
    actor_col = choose_column(fields, ("aktoer", "aktør"))
    instrument_col = choose_column(fields, ("virkemiddel",))
    contribution_col = choose_column(fields, ("bidragstype",))
    date_col = choose_column(fields, ("dato",))
    amount_col = choose_column(fields, ("Innvilget_beloep", "innvilget beløp", "innvilgetbeloep"))
    if org_col is None:
        raise SystemExit(f"No organisation-number column found. Fields: {fields}")

    rows_scanned = 0
    matched_rows = 0
    matched_orgs: set[str] = set()
    recent_orgs: set[str] = set()
    actors: Counter[str] = Counter()
    contribution_types: Counter[str] = Counter()
    instruments: Counter[str] = Counter()
    matched_years: Counter[str] = Counter()
    samples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in reader:
        rows_scanned += 1
        org = re.sub(r"\D", "", str(row.get(org_col) or ""))
        if org not in targets:
            continue
        matched_rows += 1
        matched_orgs.add(org)
        event_date = parse_date(row.get(date_col)) if date_col else None
        recent = bool(event_date and cutoff <= event_date <= as_of)
        if recent:
            recent_orgs.add(org)
        actor = " ".join(str(row.get(actor_col) or "").split()) if actor_col else ""
        contribution = " ".join(str(row.get(contribution_col) or "").split()) if contribution_col else ""
        instrument = " ".join(str(row.get(instrument_col) or "").split()) if instrument_col else ""
        if actor:
            actors[actor] += 1
        if contribution:
            contribution_types[contribution] += 1
        if instrument:
            instruments[instrument] += 1
        if event_date:
            matched_years[str(event_date.year)] += 1
        if len(samples[org]) < args.sample_limit:
            samples[org].append(
                {
                    "date": event_date.isoformat() if event_date else None,
                    "actor": actor or None,
                    "instrument": instrument or None,
                    "contribution_type": contribution or None,
                    "awarded_amount": parse_float(row.get(amount_col)) if amount_col else None,
                    "recent": recent,
                }
            )

    net_new = matched_orgs - incumbent_support
    recent_net_new = recent_orgs - incumbent_support
    overlap = matched_orgs & incumbent_support
    total = len(targets)

    def coverage(values: set[str]) -> dict[str, Any]:
        return {
            "companies": len(values),
            "total_companies": total,
            "coverage_pct": round(100.0 * len(values) / total, 1) if total else 0.0,
            "organisation_numbers": sorted(values),
        }

    report = {
        "source": {
            "publisher": "Innovation Norway / Ministry of Trade and Industry consolidated policy-support reporting",
            "repository": "innovationnorway/analysis-innovation-policy-data",
            "dataset": "InnovationPolicyData.csv",
            "dataset_sha256": sha256_file(dataset_path),
            "dataset_bytes": dataset_path.stat().st_size,
            "encoding": encoding,
            "delimiter": delimiter,
            "license": "NLOD 2.0",
            "identity_join": "exact nine-digit organisation number",
            "data_collection_through": "2023-07",
        },
        "schema": {
            "fieldnames": fields,
            "organisation_number_column": org_col,
            "actor_column": actor_col,
            "instrument_column": instrument_col,
            "contribution_type_column": contribution_col,
            "date_column": date_col,
            "amount_column": amount_col,
        },
        "audit": {
            "as_of": as_of.isoformat(),
            "recent_cutoff": cutoff.isoformat(),
            "target_companies": total,
            "rows_scanned": rows_scanned,
            "matched_rows": matched_rows,
            "incumbent_support_award_companies": len(incumbent_support),
        },
        "coverage": {
            "any_policy_support": coverage(matched_orgs),
            "recent_policy_support": coverage(recent_orgs),
            "overlap_with_existing_support_award": coverage(overlap),
            "net_new_over_existing_support_award": coverage(net_new),
            "recent_net_new_over_existing_support_award": coverage(recent_net_new),
        },
        "matched_actor_counts": dict(actors.most_common()),
        "matched_contribution_type_counts": dict(contribution_types.most_common()),
        "matched_instrument_counts": dict(instruments.most_common(50)),
        "matched_year_counts": dict(sorted(matched_years.items())),
        "matches_by_organisation_number": dict(sorted(samples.items())),
        "publication_enabled": False,
        "fresh_cohort_consumed": False,
        "policy": (
            "Source-selection only. Historical policy-support rows remain typed government support activity. "
            "They must not be relabelled as company-authored news, social buzz, hiring, reviews, or sentiment. "
            "Promotion depends on net-new company coverage beyond the existing support-award family."
        ),
    }

    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
