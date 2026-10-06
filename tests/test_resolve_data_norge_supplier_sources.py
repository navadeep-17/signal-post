from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resolve_data_norge_supplier_sources.py"
spec = importlib.util.spec_from_file_location("resolve_data_norge_supplier_sources", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_candidate_hit_requires_supplier_semantics() -> None:
    assert module.candidate_hit(
        {"title": {"nb": "Leverandørregnskap kommune"}}
    )
    assert not module.candidate_hit(
        {"title": {"nb": "Vanlig organisasjonsregister"}}
    )


def test_summary_detects_exact_org_open_license_and_distribution() -> None:
    metadata = {
        "title": {"nb": "Leverandørbetalinger"},
        "description": {
            "nb": "Utbetalinger til leverandører med organisasjonsnummer."
        },
        "distribution": [
            {
                "license": "https://data.norge.no/nlod/no/2.0",
                "downloadURL": "https://example.test/payments.csv",
                "format": "text/csv",
            }
        ],
        "modified": "2026-10-01",
    }
    row = module.summarize("abc", metadata, ["leverandørregnskap"])
    assert row["explicit_org_metadata"] is True
    assert row["supplier_semantics"] is True
    assert row["open_license_detected"] is True
    assert row["download_access_urls"] == ["https://example.test/payments.csv"]
    assert row["selection_score"] >= 22


def test_public_access_without_license_is_not_open_license() -> None:
    metadata = {
        "title": {"nb": "Leverandørregister"},
        "description": {"nb": "Organisasjonsnummer"},
        "accessRights": "PUBLIC",
        "distribution": [{"accessURL": "https://example.test/data"}],
    }
    row = module.summarize("abc", metadata, ["leverandørregnskap"])
    assert row["open_license_detected"] is False
