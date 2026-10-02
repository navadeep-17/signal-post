#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_v2_product import compact_company, read_jsonl  # noqa: E402

V6_UI_SCHEMA = "signalpost-ui-v6"
ASSET_DIR = ROOT / "scripts" / "ui_v6"


def build_v6_html(rows: list[dict[str, Any]], title: str = "Signalpost — evidence workspace") -> str:
    companies = [compact_company(row) for row in rows]
    payload = json.dumps(companies, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    template = (ASSET_DIR / "template.html").read_text(encoding="utf-8")
    css = "\n".join(
        (ASSET_DIR / filename).read_text(encoding="utf-8")
        for filename in ("styles.css", "polish.css")
    )
    js = "\n".join(
        (ASSET_DIR / filename).read_text(encoding="utf-8")
        for filename in ("app_core.js", "app_views.js", "app_polish.js")
    )
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
    print(json.dumps({
        "schema_version": V6_UI_SCHEMA,
        "companies": len(rows),
        "output": str(output),
        "bytes": len(body.encode("utf-8")),
        "data_linked": True,
        "search_discovery": True,
        "global_company_finder": True,
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
