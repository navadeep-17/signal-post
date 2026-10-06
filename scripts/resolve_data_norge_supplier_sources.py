#!/usr/bin/env python3
"""Discover and resolve Data.norge supplier-payment dataset metadata.

Research-only metadata discovery:
- bounded Search API queries discover candidate datasets;
- Data.norge Resource Service resolves full dataset metadata/distributions;
- no supplier/payment source dataset is downloaded;
- no company fact is published.

The purpose is to identify broad, rights-clean exact-org sources before spending
source-data requests.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

SEARCH_ENDPOINT = "https://search.api.fellesdatakatalog.digdir.no/search/datasets"
RESOURCE_BASE = "https://resource.api.fellesdatakatalog.digdir.no/v1/datasets"
QUERIES = (
    "leverandørregnskap",
    "leverandørreskontro",
    "utbetaling leverandør organisasjonsnummer",
    "faktura leverandør organisasjonsnummer",
)
ORG_TERMS = (
    "organisasjonsnummer",
    "organisasjonsnr",
    "orgnr",
    "organisation number",
    "organization number",
)
SUPPLIER_TERMS = (
    "leverandør",
    "leverandor",
    "supplier",
    "faktura",
    "invoice",
    "utbetaling",
    "betaling",
    "payment",
)
OPEN_LICENSE_HINTS = (
    "nlod",
    "norsk lisens for offentlige data",
    "creative commons",
    "cc by",
    "creativecommons.org",
)


def iter_scalars(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for child in value.values():
            yield from iter_scalars(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_scalars(child)
    elif value is not None:
        yield str(value)


def localized(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        for key in ("nb", "no", "nn", "en"):
            child = value.get(key)
            if isinstance(child, str) and child.strip():
                return child.strip()
        for child in value.values():
            if isinstance(child, str) and child.strip():
                return child.strip()
    return None


def fetch_json(
    url: str,
    *,
    body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    raw_body = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "Signalpost-research-source-miner/1.0",
    }
    method = "GET"
    if body is not None:
        raw_body = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    req = urllib.request.Request(url, data=raw_body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError(f"non-object JSON from {url}")
    return value


def search(query: str, *, size: int, timeout: float) -> list[dict[str, Any]]:
    payload = fetch_json(
        SEARCH_ENDPOINT,
        body={"query": query, "pagination": {"size": size, "page": 1}},
        timeout=timeout,
    )
    hits = payload.get("hits")
    if isinstance(hits, list):
        return [x for x in hits if isinstance(x, dict)]
    for key in ("results", "data"):
        wrapped = payload.get(key)
        if isinstance(wrapped, dict) and isinstance(wrapped.get("hits"), list):
            return [x for x in wrapped["hits"] if isinstance(x, dict)]
    return []


def hit_id(hit: dict[str, Any]) -> str | None:
    for key in ("id", "datasetId", "identifier"):
        value = hit.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def hit_text(hit: dict[str, Any]) -> str:
    return " ".join(iter_scalars(hit)).casefold()


def candidate_hit(hit: dict[str, Any]) -> bool:
    text = hit_text(hit)
    return any(term in text for term in SUPPLIER_TERMS)


def collect_key_values(value: Any, key_terms: tuple[str, ...]) -> list[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            kl = str(key).casefold()
            if any(term in kl for term in key_terms):
                found.update(s.strip() for s in iter_scalars(child) if s.strip())
            found.update(collect_key_values(child, key_terms))
    elif isinstance(value, list):
        for child in value:
            found.update(collect_key_values(child, key_terms))
    return sorted(found)


def infer_formats(metadata: dict[str, Any]) -> list[str]:
    values = collect_key_values(metadata, ("format", "mediatype", "media_type"))
    return sorted(set(values))


def infer_license(metadata: dict[str, Any]) -> list[str]:
    return collect_key_values(metadata, ("license", "licence"))


def infer_downloads(metadata: dict[str, Any]) -> list[str]:
    vals = collect_key_values(
        metadata,
        ("downloadurl", "download_url", "accessurl", "access_url", "endpointurl", "endpoint_url"),
    )
    return sorted({v for v in vals if v.startswith(("http://", "https://"))})


def infer_dates(metadata: dict[str, Any]) -> list[str]:
    return collect_key_values(
        metadata,
        (
            "modified",
            "issued",
            "temporal",
            "startdate",
            "enddate",
            "lastupdated",
            "updated",
        ),
    )


def summarize(dataset_id: str, metadata: dict[str, Any], matched_queries: list[str]) -> dict[str, Any]:
    text = " ".join(iter_scalars(metadata)).casefold()
    licenses = infer_license(metadata)
    downloads = infer_downloads(metadata)
    formats = infer_formats(metadata)
    dates = infer_dates(metadata)
    title = localized(metadata.get("title"))
    description = localized(metadata.get("description"))

    explicit_org = any(term in text for term in ORG_TERMS)
    supplier_semantics = any(term in text for term in SUPPLIER_TERMS)
    open_license = any(
        hint in " ".join(licenses).casefold()
        for hint in OPEN_LICENSE_HINTS
    )
    machine_readable = any(
        token in " ".join(formats).casefold()
        for token in ("csv", "json", "xml", "parquet", "xlsx", "excel")
    )

    score = 0
    score += 6 if explicit_org else 0
    score += 4 if supplier_semantics else 0
    score += 5 if open_license else 0
    score += 4 if downloads else 0
    score += 3 if machine_readable else 0

    return {
        "dataset_id": dataset_id,
        "title": title,
        "description": description,
        "matched_queries": sorted(set(matched_queries)),
        "explicit_org_metadata": explicit_org,
        "supplier_semantics": supplier_semantics,
        "open_license_detected": open_license,
        "license_metadata": licenses[:20],
        "download_access_urls": downloads[:30],
        "formats": formats[:30],
        "date_metadata": dates[:30],
        "selection_score": score,
    }


def discover(
    *,
    size: int,
    max_resolve: int,
    timeout: float,
    sleep_seconds: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    discovered: dict[str, dict[str, Any]] = {}
    matched_queries: dict[str, set[str]] = {}

    search_requests = 0
    for query in QUERIES:
        hits = search(query, size=size, timeout=timeout)
        search_requests += 1
        for hit in hits:
            if not candidate_hit(hit):
                continue
            dataset_id = hit_id(hit)
            if not dataset_id:
                continue
            discovered.setdefault(dataset_id, hit)
            matched_queries.setdefault(dataset_id, set()).add(query)

    # Resolve strongest search hits deterministically. Search ranking is preserved by
    # insertion order; this remains metadata-only and bounded.
    ids = list(discovered)[:max_resolve]
    rows: list[dict[str, Any]] = []
    resolve_errors: list[dict[str, str]] = []
    for index, dataset_id in enumerate(ids):
        url = RESOURCE_BASE + "/" + urllib.parse.quote(dataset_id, safe="")
        try:
            metadata = fetch_json(url, timeout=timeout)
            rows.append(summarize(dataset_id, metadata, sorted(matched_queries[dataset_id])))
        except Exception as exc:
            resolve_errors.append(
                {
                    "dataset_id": dataset_id,
                    "error": f"{type(exc).__name__}: {str(exc)[:240]}",
                }
            )
        if index + 1 < len(ids):
            time.sleep(sleep_seconds)

    rows.sort(
        key=lambda row: (
            -int(row["selection_score"]),
            str(row.get("title") or row["dataset_id"]),
        )
    )
    report = {
        "screen_type": "data_norge_supplier_dataset_metadata_resolution",
        "queries": list(QUERIES),
        "search_requests": search_requests,
        "candidate_search_hits": len(discovered),
        "resource_requests": len(ids),
        "resolved_datasets": len(rows),
        "resolve_errors": resolve_errors,
        "open_licensed_exact_org_supplier_datasets": sum(
            bool(
                row["explicit_org_metadata"]
                and row["supplier_semantics"]
                and row["open_license_detected"]
                and row["download_access_urls"]
            )
            for row in rows
        ),
        "source_data_requests": 0,
        "production_publication_enabled": False,
        "notes": [
            "Search API is discovery only; Resource Service supplies complete dataset metadata.",
            "No supplier/payment source dataset is downloaded in this stage.",
            "A candidate still needs source-schema, freshness, exact-org reach and rights validation.",
        ],
    }
    return rows, report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--size", type=int, default=30)
    ap.add_argument("--max-resolve", type=int, default=20)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--sleep-seconds", type=float, default=0.25)
    args = ap.parse_args()

    if args.size < 1 or args.size > 100:
        ap.error("--size must be 1..100")
    if args.max_resolve < 1 or args.max_resolve > 40:
        ap.error("--max-resolve must be 1..40")
    if args.sleep_seconds < 0.2:
        ap.error("--sleep-seconds must be at least 0.2")

    rows, report = discover(
        size=args.size,
        max_resolve=args.max_resolve,
        timeout=args.timeout,
        sleep_seconds=args.sleep_seconds,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "candidates.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    report["top_candidates"] = rows[:20]
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
