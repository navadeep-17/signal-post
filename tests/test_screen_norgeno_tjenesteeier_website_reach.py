from __future__ import annotations

import csv
import gzip
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_norgeno_tjenesteeier_website_reach.py"
spec = importlib.util.spec_from_file_location("screen_norgeno_tjenesteeier_website_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_identify_columns_accepts_norwegian_headers() -> None:
    assert module.identify_columns(["navn", "organisasjonsnummer", "url", "kommunenummer"]) == (
        "organisasjonsnummer",
        "url",
    )


def test_scan_counts_exact_net_new_candidates_only(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["navn", "organisasjonsnummer", "url"], delimiter=";")
        writer.writeheader()
        writer.writerow({"navn": "A", "organisasjonsnummer": "111111111", "url": "https://a.example"})
        writer.writerow({"navn": "B", "organisasjonsnummer": "222222222", "url": "https://b.example"})
        writer.writerow({"navn": "X", "organisasjonsnummer": "999999999", "url": "https://x.example"})

    result = module.scan(
        source,
        {"111111111", "222222222", "333333333"},
        {"111111111"},
    )
    assert result["exact_company_hits"] == 2
    assert result["website_candidate_companies"] == 2
    assert result["website_overlap_current_verified"] == 1
    assert result["website_net_new_candidates"] == 1
    assert result["post_candidate_upper_bound_website_companies"] == 2
    encoded = repr(result)
    assert "https://b.example" not in encoded
    assert "222222222" not in encoded
