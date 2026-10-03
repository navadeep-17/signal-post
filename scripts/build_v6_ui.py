#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_v2_product import read_jsonl  # noqa: E402
from v6_payload_adapter import compact_company_v6  # noqa: E402

V6_UI_SCHEMA = "signalpost-ui-v6"
V6_PAYLOAD_FORMAT = "signalpost-ui-v6-pooled-evidence"
ASSET_DIR = ROOT / "scripts" / "ui_v6"


def _evidence_key(item: dict[str, Any]) -> str:
    explicit = item.get("id")
    if explicit:
        return str(explicit)
    material = json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "ui-ev-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _pool_evidence_payload(companies: list[dict[str, Any]]) -> dict[str, Any]:
    packed = copy.deepcopy(companies)
    pool: dict[str, dict[str, Any]] = {}

    def refs(rows: list[dict[str, Any]] | None) -> list[str]:
        output: list[str] = []
        for item in rows or []:
            if not isinstance(item, dict):
                continue
            key = _evidence_key(item)
            pool.setdefault(key, item)
            if key not in output:
                output.append(key)
        return output

    for company in packed:
        for facts in (company.get("areas") or {}).values():
            for fact in facts or []:
                if not isinstance(fact, dict):
                    continue
                fact["evidenceRefs"] = refs(fact.pop("evidence", None))
        for section in ((company.get("synthesis") or {}).get("sections") or []):
            if not isinstance(section, dict):
                continue
            section["sourceRefs"] = refs(section.pop("sources", None))

    return {
        "format": V6_PAYLOAD_FORMAT,
        "companies": packed,
        "evidence": pool,
    }


def build_v6_html(rows: list[dict[str, Any]], title: str = "Signalpost — evidence workspace") -> str:
    companies = [compact_company_v6(row) for row in rows]
    payload_object = _pool_evidence_payload(companies)
    payload = json.dumps(payload_object, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    template = (ASSET_DIR / "template.html").read_text(encoding="utf-8")
    css = "\n".join(
        (ASSET_DIR / filename).read_text(encoding="utf-8")
        for filename in ("styles.css", "polish.css", "polish_final.css")
    )
    js = "\n".join(
        (ASSET_DIR / filename).read_text(encoding="utf-8")
        for filename in ("payload_hydrate.js", "app_core.js", "app_views.js", "app_polish.js")
    )
    js = js.replace("const DATA=__PAYLOAD__;", "const DATA=hydrateSignalpostPayload(__PAYLOAD__);")
    return (
        template.replace("__TITLE__", html.escape(title))
        .replace("__CSS__", css)
        .replace("__JS__", js)
        .replace("__PAYLOAD__", payload)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Signalpost V6 evidence workspace from final canonical JSONL.")
    parser.add_argument("--input", required=True, help="Current final output JSONL")
    parser.add_argument("--output", required=True, help="HTML workspace output")
    parser.add_argument("--title", default="Signalpost — evidence workspace")
    parser.add_argument("--expect-count", type=int)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input))
    if args.expect_count is not None and len(rows) != args.expect_count:
        raise SystemExit(f"expected {args.expect_count} rows, got {len(rows)}")
    body = build_v6_html(rows, title=args.title)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body, encoding="utf-8")
    body_bytes = len(body.encode("utf-8"))
    print(json.dumps({
        "schema_version": V6_UI_SCHEMA,
        "payload_format": V6_PAYLOAD_FORMAT,
        "companies": len(rows),
        "output": str(output),
        "bytes": body_bytes,
        "bytes_per_company": round(body_bytes / max(1, len(rows)), 1),
        "pooled_evidence": True,
        "data_linked": True,
        "search_discovery": True,
        "exact_match_search_priority": True,
        "global_company_finder": True,
        "inline_provenance": True,
        "url_state": True,
        "evidence_drawer": True,
        "verify_all_evidence": True,
        "compare_enabled": True,
        "compare_differences_filter": True,
        "changes_timeline": True,
        "grounded_ask": True,
        "responsive": True,
    }, indent=2))


if __name__ == "__main__":
    main()
