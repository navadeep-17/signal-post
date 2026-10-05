from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mine_data_norge_exact_org_sources.py"
spec = importlib.util.spec_from_file_location("mine_data_norge_exact_org_sources", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_extract_hits_accepts_direct_and_wrapped_shapes() -> None:
    assert module.extract_hits({"hits": [{"id": "a"}]}) == [{"id": "a"}]
    assert module.extract_hits({"results": {"hits": [{"id": "b"}]}}) == [{"id": "b"}]
    assert module.extract_hits({"data": {"hits": [{"id": "c"}]}}) == [{"id": "c"}]


def test_mine_payloads_merges_same_dataset_across_queries_and_ranks_metadata() -> None:
    strong = {
        "id": "dataset-1",
        "title": "Leverandørregister med organisasjonsnummer",
        "description": "Inneholder nettside, e-post, leverandør og dato",
        "license": "https://data.norge.no/nlod/no/2.0",
        "distribution": {
            "downloadURL": "https://example.test/data.csv",
            "accessURL": "https://example.test/api",
        },
    }
    weak = {
        "id": "dataset-2",
        "title": "Liste med organisasjonsnummer",
        "description": "Bare identifikatorer",
    }
    rows = module.mine_payloads(
        [
            ("organisasjonsnummer nettside", {"hits": [strong, weak]}),
            ("organisasjonsnummer leverandør", {"hits": [strong]}),
        ]
    )
    assert len(rows) == 2
    assert rows[0]["dataset"] == "dataset-1"
    assert rows[0]["matched_queries"] == [
        "organisasjonsnummer leverandør",
        "organisasjonsnummer nettside",
    ]
    assert "website" in rows[0]["semantic_categories"]
    assert "contact" in rows[0]["semantic_categories"]
    assert "procurement" in rows[0]["semantic_categories"]
    assert rows[0]["license_metadata"]
    assert rows[0]["download_metadata"]
    assert rows[0]["selection_score"] > rows[1]["selection_score"]


def test_canonical_hit_id_is_deterministic_without_explicit_id() -> None:
    a = {"title": "A", "nested": {"x": 1}}
    b = {"nested": {"x": 1}, "title": "A"}
    assert module.canonical_hit_id(a) == module.canonical_hit_id(b)
    assert module.canonical_hit_id(a).startswith("sha256:")
