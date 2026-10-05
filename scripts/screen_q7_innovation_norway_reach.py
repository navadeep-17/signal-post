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


def read_target_orgs(path: Path) -> set[str]:
    orgs: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = re.sub(r"\D", "", str(row.get("organisation_number") or ""))
        if len(org) == 9:
            orgs.add(org)
    return orgs


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_csv(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode CSV")


def clean_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def choose_column(fieldnames: list[str], *, required_tokens: tuple[str, ...], preferred_tokens: tuple[str, ...] = ()) -> str | None:
    scored: list[tuple[int, int, str]] = []
    for name in fieldnames:
        folded = clean_header(name)
        if not all(token in folded for token in required_tokens):
            continue
        preference = sum(int(token in folded) for token in preferred_tokens)
        scored.append((-preference, len(name), name))
    if not scored:
        return None
    scored.sort()
    return scored[0][2]


def parse_date(value: Any) -> date | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    candidates = [text, text[:10]]
    for candidate in candidates:
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
    normalized = text
    if "," in normalized and "." in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    normalized = re.sub(r"[^0-9.\-]", "", normalized)
    try:
        return float(normalized)
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research-only exact-org reach screen over Innovasjon Norge published financing decisions."
    )
    parser.add_argument("--targets", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--as-of", default="2026-10-05")
    parser.add_argument("--recent-years", type=int, default=5)
    parser.add_argument("--sample-limit", type=int, default=10)
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of)
    cutoff = date(as_of.year - args.recent_years, as_of.month, as_of.day)
    targets = read_target_orgs(Path(args.targets))
    if not targets:
        raise SystemExit("No valid target organisation numbers")

    dataset = Path(args.dataset)
    text, encoding = decode_csv(dataset)
    sample = text[:100_000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ";" if sample.count(";") > sample.count(",") else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    fieldnames = list(reader.fieldnames or [])
    org_column = choose_column(
        fieldnames,
        required_tokens=("organisasjons",),
        preferred_tokens=("nummer", "mottaker", "kunde", "bedrift"),
    )
    if org_column is None:
        org_column = choose_column(fieldnames, required_tokens=("org",), preferred_tokens=("nr", "nummer"))
    if org_column is None:
        raise SystemExit(f"No organisation-number-like column found. Fields: {fieldnames}")

    date_column = (
        choose_column(fieldnames, required_tokens=("dato",), preferred_tokens=("tilsagn", "vedtak", "tildeling"))
        or choose_column(fieldnames, required_tokens=("år",), preferred_tokens=("tilsagn", "vedtak", "tildeling"))
    )
    amount_column = (
        choose_column(fieldnames, required_tokens=("beløp",), preferred_tokens=("tilsagn", "finans", "tildelt"))
        or choose_column(fieldnames, required_tokens=("belop",), preferred_tokens=("tilsagn", "finans", "tildelt"))
    )
    name_column = choose_column(fieldnames, required_tokens=("navn",), preferred_tokens=("kunde", "bedrift", "mottaker"))
    instrument_column = (
        choose_column(fieldnames, required_tokens=("virkemiddel",))
        or choose_column(fieldnames, required_tokens=("finansiering",), preferred_tokens=("type",))
    )

    matched_orgs: set[str] = set()
    recent_orgs: set[str] = set()
    rows_scanned = 0
    matched_rows = 0
    year_counts: Counter[str] = Counter()
    matches: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in reader:
        rows_scanned += 1
        org = re.sub(r"\D", "", str(row.get(org_column) or ""))
        if org not in targets:
            continue
        matched_rows += 1
        matched_orgs.add(org)
        event_date = parse_date(row.get(date_column)) if date_column else None
        recent = bool(event_date and cutoff <= event_date <= as_of)
        if recent:
            recent_orgs.add(org)
        if event_date:
            year_counts[str(event_date.year)] += 1
        if len(matches[org]) < args.sample_limit:
            matches[org].append(
                {
                    "organisation_number": org,
                    "name": str(row.get(name_column) or "")[:300] if name_column else None,
                    "event_date": event_date.isoformat() if event_date else None,
                    "amount": parse_float(row.get(amount_column)) if amount_column else None,
                    "instrument": str(row.get(instrument_column) or "")[:300] if instrument_column else None,
                    "recent": recent,
                }
            )

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
            "publisher": "Innovasjon Norge",
            "dataset": "Tilsagn om finansiering fra Innovasjon Norge",
            "dataset_sha256": sha256_file(dataset),
            "dataset_bytes": dataset.stat().st_size,
            "encoding": encoding,
            "delimiter": delimiter,
            "license_status": "unspecified_in_data_norge_metadata_as_of_2026-10-05",
            "production_rights_qualified": False,
        },
        "schema": {
            "fieldnames": fieldnames,
            "organisation_number_column": org_column,
            "date_column": date_column,
            "amount_column": amount_column,
            "name_column": name_column,
            "instrument_column": instrument_column,
        },
        "audit": {
            "as_of": as_of.isoformat(),
            "recent_cutoff": cutoff.isoformat(),
            "target_companies": total,
            "rows_scanned": rows_scanned,
            "matched_rows": matched_rows,
        },
        "coverage": {
            "any_financing_decision": coverage(matched_orgs),
            "recent_financing_decision": coverage(recent_orgs),
        },
        "matched_year_counts": dict(sorted(year_counts.items())),
        "matches_by_organisation_number": dict(sorted(matches.items())),
        "publication_enabled": False,
        "fresh_cohort_consumed": False,
        "policy": (
            "Reach probe only. Exact organisation-number overlap does not qualify production use while the source license/right-to-republish metadata remains unspecified."
        ),
    }
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
