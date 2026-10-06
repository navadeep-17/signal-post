#!/usr/bin/env python3
"""Screen the legacy Norge.no service-owner dataset for exact-org website candidates.

Research-only source selection. The source is NLOD/open but stale and public-sector
focused, so URLs are candidates only and never publication proof.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any

ORG_HEADER_ALIASES = {
    "organisasjonsnummer",
    "organisasjonsnr",
    "organisasjonsnummeret",
    "orgnr",
    "orgnummer",
}
URL_HEADER_ALIASES = {
    "url",
    "nettadresse",
    "nettsted",
    "nettside",
    "website",
    "web",
}


def norm_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold().replace("æ", "ae").replace("ø", "o").replace("å", "a"))


def norm_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if len(digits) == 9 else None


def read_targets(path: Path) -> set[str]:
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = norm_org(row.get("organisation_number") or row.get("organization_number") or row.get("orgnr"))
        if not org:
            raise ValueError(f"invalid target organisation number: {row!r}")
        if org in out:
            raise ValueError(f"duplicate target organisation number: {org}")
        out.add(org)
    if not out:
        raise ValueError("empty target set")
    return out


def current_verified_websites(path: Path, targets: set[str]) -> set[str]:
    found: set[str] = set()
    seen: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            org = norm_org(row.get("organisation_number"))
            if not org or org not in targets:
                continue
            if org in seen:
                raise ValueError(f"duplicate production organisation number: {org}")
            seen.add(org)
            if any(
                isinstance(claim, dict)
                and claim.get("field") == "official_website"
                and claim.get("availability") == "available"
                and claim.get("value")
                for claim in (row.get("claims") or [])
            ):
                found.add(org)
    if seen != targets:
        raise ValueError(f"production output does not cover all targets: missing={len(targets-seen)}")
    return found


def decode_csv(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "iso-8859-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("unable to decode source CSV")


def identify_columns(fieldnames: list[str]) -> tuple[str, str]:
    normalized = {name: norm_header(name) for name in fieldnames}

    def choose(aliases: set[str], *, contains: tuple[str, ...] = ()) -> str | None:
        for name, key in normalized.items():
            if key in aliases:
                return name
        for name, key in normalized.items():
            if any(token in key for token in contains):
                return name
        return None

    org_col = choose(ORG_HEADER_ALIASES, contains=("organisasjon", "orgnr", "orgnummer"))
    url_col = choose(URL_HEADER_ALIASES, contains=("nettadresse", "nettside", "nettsted", "website"))
    if not org_col or not url_col:
        raise ValueError(f"could not identify org/url columns: {fieldnames!r}")
    return org_col, url_col


def scan(source: Path, targets: set[str], current_web: set[str]) -> dict[str, Any]:
    text, encoding = decode_csv(source)
    sample = text[:65536]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ";"
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    fieldnames = list(reader.fieldnames or [])
    org_col, url_col = identify_columns(fieldnames)

    source_rows = 0
    valid_org_rows = 0
    malformed_org_rows = 0
    exact_hits: set[str] = set()
    website_hits: set[str] = set()
    for row in reader:
        source_rows += 1
        org = norm_org(row.get(org_col))
        if not org:
            malformed_org_rows += 1
            continue
        valid_org_rows += 1
        if org not in targets:
            continue
        exact_hits.add(org)
        if str(row.get(url_col) or "").strip():
            website_hits.add(org)

    overlap = website_hits & current_web
    net_new = website_hits - current_web
    return {
        "source_rows": source_rows,
        "valid_org_rows": valid_org_rows,
        "malformed_org_rows": malformed_org_rows,
        "encoding": encoding,
        "delimiter": delimiter,
        "organisation_column": org_col,
        "website_column": url_col,
        "exact_company_hits": len(exact_hits),
        "website_candidate_companies": len(website_hits),
        "website_overlap_current_verified": len(overlap),
        "website_net_new_candidates": len(net_new),
        "post_candidate_upper_bound_website_companies": len(current_web | website_hits),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--companies", type=Path, required=True)
    ap.add_argument("--production-output-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    targets = read_targets(args.companies)
    current_web = current_verified_websites(args.production_output_gz, targets)
    result = scan(args.source, targets, current_web)
    n = len(targets)

    report = {
        "source": "Norge.no tjenesteeiere",
        "screen_type": "legacy_nlod_exact_org_website_candidate_overlap",
        "cohort_companies": n,
        "source_bytes": args.source.stat().st_size,
        "source_sha256": sha256_file(args.source),
        "current_verified_website_companies": len(current_web),
        "current_verified_website_reach": round(len(current_web) / n, 6),
        **result,
        "exact_company_reach": round(result["exact_company_hits"] / n, 6),
        "website_candidate_reach": round(result["website_candidate_companies"] / n, 6),
        "website_net_new_candidate_reach": round(result["website_net_new_candidates"] / n, 6),
        "post_candidate_upper_bound_website_reach": round(result["post_candidate_upper_bound_website_companies"] / n, 6),
        "external_requests": 1,
        "reuse_rights_status": "NLOD_OPEN",
        "production_publication_enabled": False,
        "freshness_status": "STALE_SOURCE_LAST_DATA_UPDATE_2020_TEMPORAL_SCOPE_ENDED_2018",
        "notes": [
            "Exact nine-digit organisation number is the only company join.",
            "The dataset is public-sector focused and stale; source URLs are discovery candidates only.",
            "A candidate would still require a fresh independent exact-company website verification before publication.",
            "No source URL values or matched organisation-number lists are persisted in the report.",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
