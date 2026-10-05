from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mine_data_norge_exact_org_sources.py"
spec = importlib.util.spec_from_file_location("mine_data_norge_exact_org_sources", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _b(value: str) -> dict[str, str]:
    return {"type": "literal", "value": value}


def _u(value: str) -> dict[str, str]:
    return {"type": "uri", "value": value}


def test_parse_results_groups_distributions_and_ranks_open_bulk_candidate() -> None:
    payload = {
        "results": {
            "bindings": [
                {
                    "dataset": _u("https://example.test/dataset/1"),
                    "title": _b("Leverandørregister med organisasjonsnummer"),
                    "description": _b("Har leverandør, e-post, nettside og dato."),
                    "license": _u("https://data.norge.no/nlod/no/2.0"),
                    "distribution": _u("https://example.test/distribution/1"),
                    "downloadURL": _u("https://example.test/data.csv"),
                },
                {
                    "dataset": _u("https://example.test/dataset/1"),
                    "title": _b("Leverandørregister med organisasjonsnummer"),
                    "accessURL": _u("https://example.test/api"),
                },
                {
                    "dataset": _u("https://example.test/dataset/2"),
                    "title": _b("Organisasjonsnummerliste"),
                    "description": _b("Liste over orgnr."),
                },
            ]
        }
    }
    rows = module.parse_results(payload)
    assert len(rows) == 2
    assert rows[0]["dataset"] == "https://example.test/dataset/1"
    assert rows[0]["has_explicit_license_metadata"] is True
    assert rows[0]["has_download_url"] is True
    assert rows[0]["has_access_url"] is True
    assert "procurement" in rows[0]["semantic_categories"]
    assert "contact" in rows[0]["semantic_categories"]
    assert "website" in rows[0]["semantic_categories"]
    assert rows[0]["selection_score"] > rows[1]["selection_score"]


def test_rank_dataset_does_not_invent_license_or_download() -> None:
    row = module.rank_dataset(
        {
            "dataset": "x",
            "titles": ["Register over organisasjonsnummer"],
            "descriptions": [],
            "keywords": [],
            "licenses": [],
            "distributions": [],
            "access_urls": [],
            "download_urls": [],
            "modified": [],
        }
    )
    assert row["exact_org_metadata"] is True
    assert row["has_explicit_license_metadata"] is False
    assert row["has_download_url"] is False
