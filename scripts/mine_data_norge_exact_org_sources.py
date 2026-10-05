#!/usr/bin/env python3
"""Mine Data.norge metadata for bulk/exact-org Signalpost source candidates.

Research-only. Uses a bounded set of public Data.norge Search API queries.
No candidate source data is fetched and no company facts are published.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

SEARCH_ENDPOINT = "https://search.api.fellesdatakatalog.digdir.no/search/datasets"
SEARCH_QUERIES = (
    "organisasjonsnummer nettside",
    "organisasjonsnummer e-post",
    "organisasjonsnummer leverandør",
    "organisasjonsnummer tildeling",
    "organisasjonsnummer godkjenning",
    "organisasjonsnummer status",
    "organisasjonsnummer tilskudd",
)
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


def iter_scalars(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for child in value.values():
            yield from iter_scalars(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_scalars(child)
    elif value is not None:
        yield str(value)


def _find_first(value: Any, keys: set[str]) -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in keys and not isinstance(child, (dict, list)) and str(child).strip():
                return str(child).strip()
        for child in value.values():
            found = _find_first(child, keys)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_first(child, keys)
            if found:
                return found
    return None


def _collect_by_key_fragment(value: Any, fragments: tuple[str, ...]) -> list[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if any(fragment in key.lower() for fragment in fragments):
                found.update(s.strip() for s in iter_scalars(child) if s.strip())
            found.update(_collect_by_key_fragment(child, fragments))
    elif isinstance(value, list):
        for child in value:
            found.update(_collect_by_key_fragment(child, fragments))
    return sorted(found)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def canonical_hit_id(hit: dict[str, Any]) -> str:
    explicit = _find_first(hit, {"id", "uri", "identifier", "datasetid"})
    if explicit:
        return explicit
    canonical = json.dumps(hit, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def fetch_search(query: str, *, size: int = 50, timeout: float = 25.0) -> tuple[bytes, dict[str, Any]]:
    body = json.dumps(
        {"query": query, "pagination": {"size": size, "page": 1}},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        SEARCH_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Signalpost-research-source-miner/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RuntimeError("Data.norge Search API response is not an object")
    return raw, payload


def extract_hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    hits = payload.get("hits")
    if isinstance(hits, list):
        return [hit for hit in hits if isinstance(hit, dict)]
    # tolerate wrappers used by search backends
    for container_key in ("results", "data"):
        container = payload.get(container_key)
        if isinstance(container, dict) and isinstance(container.get("hits"), list):
            return [hit for hit in container["hits"] if isinstance(hit, dict)]
    return []


def summarize_hit(hit: dict[str, Any], matched_queries: set[str]) -> dict[str, Any]:
    text = " ".join(iter_scalars(hit)).lower()
    categories = sorted(name for name, terms in VALUE_TERMS.items() if _contains_any(text, terms))
    license_values = _collect_by_key_fragment(hit, ("license", "licence", "rights"))
    download_values = _collect_by_key_fragment(hit, ("downloadurl", "download_url", "download"))
    access_values = _collect_by_key_fragment(hit, ("accessurl", "access_url", "endpoint", "access"))
    title = _find_first(hit, {"title", "name", "label", "preflabel"})
    score = 0
    score += 4 if _contains_any(text, ORG_TERMS) else 0
    score += min(4, len(matched_queries))
    score += 3 if license_values else 0
    score += 3 if download_values else 0
    score += 1 if access_values else 0
    score += min(4, len(categories))
    return {
        "dataset": canonical_hit_id(hit),
        "title": title,
        "matched_queries": sorted(matched_queries),
        "semantic_categories": categories,
        "license_metadata": license_values[:10],
        "download_metadata": download_values[:10],
        "access_metadata": access_values[:10],
        "exact_org_metadata": _contains_any(text, ORG_TERMS),
        "selection_score": score,
        "raw_hit": hit,
    }


def mine_payloads(payloads: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    grouped_hits: dict[str, dict[str, Any]] = {}
    matched: dict[str, set[str]] = defaultdict(set)
    for query, payload in payloads:
        for hit in extract_hits(payload):
            hit_id = canonical_hit_id(hit)
            grouped_hits.setdefault(hit_id, hit)
            matched[hit_id].add(query)
    rows = [summarize_hit(hit, matched[hit_id]) for hit_id, hit in grouped_hits.items()]
    rows.sort(key=lambda row: (-int(row["selection_score"]), str(row.get("title") or row["dataset"])))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--size", type=int, default=50)
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()

    raw_hashes: list[dict[str, str]] = []
    if args.fixture:
        fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
        payloads = [(str(item["query"]), item["payload"]) for item in fixture]
        request_count = 0
        source = str(args.fixture)
    else:
        payloads: list[tuple[str, dict[str, Any]]] = []
        for index, query in enumerate(SEARCH_QUERIES):
            raw, payload = fetch_search(query, size=args.size)
            payloads.append((query, payload))
            raw_hashes.append({"query": query, "sha256": hashlib.sha256(raw).hexdigest()})
            if index + 1 < len(SEARCH_QUERIES):
                time.sleep(0.25)
        request_count = len(SEARCH_QUERIES)
        source = SEARCH_ENDPOINT

    rows = mine_payloads(payloads)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    with (output / "candidates.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    report = {
        "source": source,
        "screen_type": "catalog_metadata_targeted_search_mining",
        "requests": request_count,
        "queries": list(SEARCH_QUERIES) if not args.fixture else [q for q, _ in payloads],
        "datasets_found": len(rows),
        "datasets_with_explicit_license_metadata": sum(bool(r["license_metadata"]) for r in rows),
        "datasets_with_download_metadata": sum(bool(r["download_metadata"]) for r in rows),
        "datasets_with_value_categories": sum(bool(r["semantic_categories"]) for r in rows),
        "raw_response_hashes": raw_hashes,
        "top_candidates": [
            {key: row[key] for key in (
                "dataset",
                "title",
                "selection_score",
                "matched_queries",
                "semantic_categories",
                "license_metadata",
                "download_metadata",
                "access_metadata",
            )}
            for row in rows[:30]
        ],
        "production_publication_enabled": False,
        "notes": [
            "This is metadata discovery only; every candidate still needs source-specific schema, rights, reach and exact-org validation.",
            "The Data.norge Search API is used only for research discovery because its public documentation warns that the API may change over time.",
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
