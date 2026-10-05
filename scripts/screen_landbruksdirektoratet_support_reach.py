#!/usr/bin/env python3
"""Screen Landbruksdirektoratet's open agricultural-support CSV by exact orgnr.

Research-only source qualification. The source row's organisation-number column
is the sole identity join. No Signalpost production claim is emitted.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable, TextIO

ORG_RE = re.compile(r"^\d{9}$")
ORG_HEADER_TOKENS = ("organisasjonsnummer", "organisasjonsnr", "orgnr")


def normalize_org(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) != 9:
        raise ValueError(f"invalid Norwegian organisation number: {value!r}")
    return digits


def company_org(row: dict[str, Any]) -> str:
    for key in ("organisation_number", "organization_number", "orgnr", "org_number"):
        if row.get(key) is not None:
            return normalize_org(row[key])
    raise ValueError(f"company row has no organisation number: {row!r}")


def read_companies(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("company JSONL rows must be objects")
        org = company_org(row)
        if org in result:
            raise ValueError(f"duplicate target organisation number: {org}")
        result[org] = row
    if not result:
        raise ValueError("empty company cohort")
    return result


def normalize_header(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return "".join(ch.lower() for ch in asciiish if ch.isalnum())


def detect_encoding_and_dialect(path: Path) -> tuple[str, csv.Dialect]:
    raw = path.read_bytes()[:131072]
    chosen_encoding: str | None = None
    sample: str | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "iso-8859-1"):
        try:
            sample = raw.decode(encoding)
            chosen_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    if chosen_encoding is None or sample is None:
        raise ValueError("could not decode CSV sample")
    dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
    return chosen_encoding, dialect


def find_org_column(fieldnames: list[str]) -> str:
    normalized = {name: normalize_header(name) for name in fieldnames}
    exact = [name for name, value in normalized.items() if value in ORG_HEADER_TOKENS]
    if len(exact) == 1:
        return exact[0]
    contains = [name for name, value in normalized.items() if any(token in value for token in ORG_HEADER_TOKENS)]
    if len(contains) == 1:
        return contains[0]
    raise ValueError(f"could not uniquely identify organisation-number column: {fieldnames!r}")


def support_columns(fieldnames: list[str]) -> list[str]:
    return [name for name in fieldnames if "tilskudd" in normalize_header(name)]


def parse_number(value: str) -> float | None:
    text = str(value or "").strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        return None
    # Norwegian CSVs commonly use comma decimals. If both separators appear,
    # treat the last one as decimal and the other as thousands punctuation.
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    text = re.sub(r"[^0-9+\-.]", "", text)
    if not text or text in {"-", "+", "."}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def scan(csv_path: Path, cohorts: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    all_targets: set[str] = set()
    for cohort in cohorts.values():
        all_targets.update(cohort)

    encoding, dialect = detect_encoding_and_dialect(csv_path)
    matches: dict[str, dict[str, Any]] = {
        org: {
            "organisation_number": org,
            "rows": 0,
            "support_cells_present": 0,
            "positive_support_cells": 0,
            "sample_rows": [],
        }
        for org in all_targets
    }

    source_rows = 0
    malformed_org_rows = 0
    target_rows = 0
    with csv_path.open("r", encoding=encoding, newline="", errors="strict") as handle:
        reader = csv.DictReader(handle, dialect=dialect)
        fieldnames = list(reader.fieldnames or [])
        if not fieldnames:
            raise ValueError("source CSV has no header")
        org_column = find_org_column(fieldnames)
        support_like = support_columns(fieldnames)

        for row in reader:
            source_rows += 1
            raw_org = str(row.get(org_column) or "").strip()
            digits = "".join(ch for ch in raw_org if ch.isdigit())
            if not ORG_RE.fullmatch(digits):
                malformed_org_rows += 1
                continue
            if digits not in all_targets:
                continue
            target_rows += 1
            hit = matches[digits]
            hit["rows"] += 1
            present = 0
            positive = 0
            for column in support_like:
                raw = str(row.get(column) or "").strip()
                if raw:
                    present += 1
                    number = parse_number(raw)
                    if number is not None and number > 0:
                        positive += 1
            hit["support_cells_present"] += present
            hit["positive_support_cells"] += positive
            if len(hit["sample_rows"]) < 2:
                hit["sample_rows"].append(
                    {
                        "organisation_number": digits,
                        "support_cells_present": present,
                        "positive_support_cells": positive,
                    }
                )

    cohort_reports: dict[str, Any] = {}
    for cohort_name, companies in cohorts.items():
        rows = [matches[org] for org in companies]
        hits = [row for row in rows if row["rows"] > 0]
        positive_hits = [row for row in rows if row["positive_support_cells"] > 0]
        cohort_reports[cohort_name] = {
            "companies": len(rows),
            "matched_companies": len(hits),
            "match_reach": round(len(hits) / len(rows), 6),
            "companies_with_positive_support_cell": len(positive_hits),
            "positive_support_reach": round(len(positive_hits) / len(rows), 6),
        }

    return {
        "encoding": encoding,
        "delimiter": dialect.delimiter,
        "fieldnames": fieldnames,
        "org_column": org_column,
        "support_columns": support_like,
        "source_rows": source_rows,
        "malformed_org_rows": malformed_org_rows,
        "target_rows": target_rows,
        "matches": matches,
        "cohorts": cohort_reports,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", required=True, type=Path)
    parser.add_argument("--companies-100", required=True, type=Path)
    parser.add_argument("--companies-1000", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    cohorts = {
        "consumed_100": read_companies(args.companies_100),
        "consumed_1000": read_companies(args.companies_1000),
    }
    if not set(cohorts["consumed_100"]).issubset(cohorts["consumed_1000"]):
        raise SystemExit("consumed 100 must be a subset of consumed 1000")

    result = scan(args.source_csv, cohorts)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)

    with (output / "matched-companies.jsonl").open("w", encoding="utf-8") as handle:
        for org in sorted(result["matches"]):
            row = result["matches"][org]
            if row["rows"]:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    report = {
        "source": "Landbruksdirektoratet production/agricultural subsidy 2025 CSV",
        "screen_type": "exact_org_bulk_support_reach",
        "source_bytes": args.source_csv.stat().st_size,
        "source_sha256": sha256_file(args.source_csv),
        "source_rows": result["source_rows"],
        "encoding": result["encoding"],
        "delimiter": result["delimiter"],
        "org_column": result["org_column"],
        "support_columns": result["support_columns"],
        "malformed_org_rows": result["malformed_org_rows"],
        "cohorts": result["cohorts"],
        "external_requests": 1,
        "reuse_license": "NLOD (verified in Data.norge distribution metadata before screen)",
        "production_publication_enabled": False,
        "notes": [
            "Only the source organisation-number column establishes a company match.",
            "Positive-support counts are a source-selection diagnostic, not publication semantics.",
            "No production claims are emitted by this screen.",
        ],
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
