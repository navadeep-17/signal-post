from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_wikidata_social_candidates.py"
spec = importlib.util.spec_from_file_location("screen_wikidata_social_candidates", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_sparql_reuses_exact_org_and_social_properties() -> None:
    query = module.sparql(["123456789"])
    assert "wdt:P2333" in query
    for prop in ("P2002", "P2003", "P2013", "P2397", "P4264"):
        assert f"wdt:{prop}" in query


def test_baseline_social_orgs(tmp_path: Path) -> None:
    p = tmp_path / "out.jsonl.gz"
    rows = [
        {
            "organisation_number": "123456789",
            "canonical_facts": [
                {"type": "social_profile", "availability": "available", "value": "x"}
            ],
        },
        {
            "organisation_number": "987654321",
            "canonical_facts": [{"type": "website", "availability": "available"}],
        },
    ]
    with gzip.open(p, "wt", encoding="utf-8") as h:
        for row in rows:
            h.write(json.dumps(row) + "\n")
    assert module.baseline_social_orgs(p) == {"123456789"}
