#!/usr/bin/env python3
"""Mine Data.norge metadata for bulk/exact-org Signalpost source candidates.

Research-only. One SPARQL metadata query is used to discover datasets whose
catalog metadata mentions Norwegian organisation-number semantics. Results are
ranked for source-selection value; no source data is fetched and no company
facts are published.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

SPARQL_ENDPOINT = "https://sparql.fellesdatakatalog.digdir.no"
ORG_TERMS = (
    "organisasjonsnummer",
    "organisasjonsnr",
    "orgnr",
    "organization number",
    "organisation number",
    "organization identifier",
    "organisation identifier",
)
VALUE_TERMS = {
    "website": ("nettside", "website", "webside", "hjemmeside", "url"),
    "contact": ("e-post", "epost", "email", "contact", "kontakt"),
    "procurement": ("leverandør", "supplier", "anskaff", "contract", "kontrakt", "tildeling"),
    "support": ("støtte", "tilskudd", "grant", "subsid", "finansiering"),
    "approval": ("godkjen", "approval", "lisens", "license", "tillat", "permit"),
    "activity": ("hendelse", "event", "status", "dato", "date", "oppdatert", "updated"),
    "employment": ("arbeidsgiver", "employer", "jobb", "job", "stilling", "vacancy"),
}

SPARQL_QUERY = r'''
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
SELECT DISTINCT ?dataset ?title ?description ?keyword ?license ?distributionLicense
                ?distribution ?accessURL ?downloadURL ?modified
WHERE {
  ?dataset a dcat:Dataset ; dct:title ?title .
  OPTIONAL { ?dataset dct:description ?description . }
  OPTIONAL { ?dataset dcat:keyword ?keyword . }
  OPTIONAL { ?dataset dct:license ?license . }
  OPTIONAL { ?dataset dct:modified ?modified . }
  OPTIONAL {
    ?dataset dcat:distribution ?distribution .
    OPTIONAL { ?distribution dcat:accessURL ?accessURL . }
    OPTIONAL { ?distribution dcat:downloadURL ?downloadURL . }
    OPTIONAL { ?distribution dct:license ?distributionLicense . }
  }
  FILTER (
    CONTAINS(LCASE(STR(?title)), "organisasjonsnummer") ||
    CONTAINS(LCASE(COALESCE(STR(?description), "")), "organisasjonsnummer") ||
    CONTAINS(LCASE(COALESCE(STR(?keyword), "")), "organisasjonsnummer") ||
    CONTAINS(LCASE(STR(?title)), "orgnr") ||
    CONTAINS(LCASE(COALESCE(STR(?description), "")), "orgnr") ||
    CONTAINS(LCASE(COALESCE(STR(?keyword), "")), "orgnr") ||
    CONTAINS(LCASE(COALESCE(STR(?description), "")), "organisation number") ||
    CONTAINS(LCASE(COALESCE(STR(?description), "")), "organization number")
  )
}
LIMIT 2000
'''.strip()


def fetch_sparql(timeout: float = 45.0) -> tuple[bytes, dict[str, Any]]:
    request = urllib.request.Request(
        SPARQL_ENDPOINT,
        data=SPARQL_QUERY.encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/sparql-results+json, application/json",
            "Content-Type": "application/sparql-query; charset=utf-8",
            "User-Agent": "Signalpost-research-source-miner/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise RuntimeError("Data.norge SPARQL response is not an object")
    return body, payload


def binding_value(binding: dict[str, Any], key: str) -> str | None:
    entry = binding.get(key)
    if not isinstance(entry, dict):
        return None
    value = entry.get("value")
    return str(value).strip() if value is not None and str(value).strip() else None


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def rank_dataset(row: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        str(value)
        for key in ("titles", "descriptions", "keywords")
        for value in row.get(key, [])
    ).lower()
    categories = [name for name, terms in VALUE_TERMS.items() if _contains_any(text, terms)]
    has_license = bool(row.get("licenses"))
    has_download = bool(row.get("download_urls"))
    has_access = bool(row.get("access_urls"))
    exact_org_metadata = _contains_any(text, ORG_TERMS)

    score = 0
    score += 4 if exact_org_metadata else 0
    score += 3 if has_license else 0
    score += 3 if has_download else 0
    score += 1 if has_access else 0
    score += min(4, len(categories))

    return {
        **row,
        "semantic_categories": sorted(categories),
        "has_explicit_license_metadata": has_license,
        "has_download_url": has_download,
        "has_access_url": has_access,
        "exact_org_metadata": exact_org_metadata,
        "selection_score": score,
    }


def parse_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    bindings = payload.get("results", {}).get("bindings", [])
    if not isinstance(bindings, list):
        raise ValueError("invalid SPARQL results.bindings")

    grouped: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {
            "titles": set(),
            "descriptions": set(),
            "keywords": set(),
            "licenses": set(),
            "distributions": set(),
            "access_urls": set(),
            "download_urls": set(),
            "modified": set(),
        }
    )
    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        dataset = binding_value(binding, "dataset")
        if not dataset:
            continue
        row = grouped[dataset]
        for key, target_key in (
            ("title", "titles"),
            ("description", "descriptions"),
            ("keyword", "keywords"),
            ("distribution", "distributions"),
            ("accessURL", "access_urls"),
            ("downloadURL", "download_urls"),
            ("modified", "modified"),
        ):
            value = binding_value(binding, key)
            if value:
                row[target_key].add(value)
        for license_key in ("license", "distributionLicense"):
            value = binding_value(binding, license_key)
            if value:
                row["licenses"].add(value)

    ranked: list[dict[str, Any]] = []
    for dataset, values in grouped.items():
        row: dict[str, Any] = {"dataset": dataset}
        row.update({key: sorted(value) for key, value in values.items()})
        ranked.append(rank_dataset(row))
    ranked.sort(key=lambda x: (-int(x["selection_score"]), x["dataset"]))
    return ranked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()

    if args.fixture:
        body = args.fixture.read_bytes()
        payload = json.loads(body)
        source = str(args.fixture)
        request_count = 0
    else:
        body, payload = fetch_sparql()
        source = SPARQL_ENDPOINT
        request_count = 1

    rows = parse_results(payload)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    with (output / "candidates.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    report = {
        "source": source,
        "screen_type": "catalog_metadata_exact_org_candidate_mining",
        "requests": request_count,
        "datasets_found": len(rows),
        "datasets_with_explicit_license_metadata": sum(bool(r["has_explicit_license_metadata"]) for r in rows),
        "datasets_with_download_url": sum(bool(r["has_download_url"]) for r in rows),
        "datasets_with_value_categories": sum(bool(r["semantic_categories"]) for r in rows),
        "response_sha256": hashlib.sha256(body).hexdigest(),
        "top_candidates": [
            {
                "dataset": row["dataset"],
                "titles": row["titles"][:3],
                "score": row["selection_score"],
                "categories": row["semantic_categories"],
                "licenses": row["licenses"][:3],
                "download_urls": row["download_urls"][:3],
                "access_urls": row["access_urls"][:3],
            }
            for row in rows[:30]
        ],
        "production_publication_enabled": False,
        "notes": [
            "This is metadata discovery only; candidate source schemas and rights still require source-specific validation.",
            "No company facts or production claims are emitted.",
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
