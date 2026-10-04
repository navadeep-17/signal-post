#!/usr/bin/env python3
"""Normalize an official source CSV to UTF-8 for research-only Phase-5 screening."""

from __future__ import annotations

import argparse
from pathlib import Path


def detect_encoding(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return "utf-16"
    sample = raw[:4096]
    if sample and sample.count(b"\x00") > max(4, len(sample) // 10):
        # The Støtteregisteret export observed on 2026-10-04 is UTF-16LE without a
        # reliably handled text/content-type boundary. This heuristic remains
        # deliberately local to the research normalizer rather than production.
        even_nuls = sample[0::2].count(0)
        odd_nuls = sample[1::2].count(0)
        return "utf-16-le" if odd_nuls >= even_nuls else "utf-16-be"
    return "utf-8-sig"


def normalize_csv(source: Path, target: Path) -> str:
    raw = source.read_bytes()
    encoding = detect_encoding(raw)
    text = raw.decode(encoding)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="")
    return encoding


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    encoding = normalize_csv(args.input, args.output)
    print(f"normalized {args.input} from {encoding} to UTF-8 at {args.output}")


if __name__ == "__main__":
    main()
