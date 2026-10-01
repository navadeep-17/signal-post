#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from build_v6_ui import build_v6_html, main as v6_main


# Retain the public schema identifier used by the evaluator-facing entry point.
# V6 changes only the presentation layer; the canonical payload/data contract is unchanged.
CURRENT_PRODUCT_SCHEMA = "signalpost-product-current-v1"


def build_current_html(rows: list[dict[str, Any]], title: str = "Signalpost — company intelligence") -> str:
    return build_v6_html(rows, title=title)


def main() -> None:
    v6_main()


if __name__ == "__main__":
    main()
