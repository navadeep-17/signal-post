from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_brreg_historical_name_website_yield.py"
spec = importlib.util.spec_from_file_location("screen_brreg_historical_name_website_yield", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_labels_strip_legal_form_and_build_compact_then_hyphenated() -> None:
    assert module.labels("Gamle Navnet AS") == ["gamlenavnet.no", "gamle-navnet.no"]


def test_latest_historical_candidate_prefers_most_recent_and_compact() -> None:
    body = {
        "navn": "Nytt Navn AS",
        "historiskeNavn": [
            {"navn": "Eldst Navn AS", "tilDato": "2019-01-01 00:00:00"},
            {"navn": "Forrige Navn AS", "tilDato": "2025-04-03 11:22:33"},
        ],
    }
    candidate = module.latest_historical_candidate(body)
    assert candidate is not None
    assert candidate["domain"] == "forrigenavn.no"
    assert candidate["historical_name_end"] == "2025-04-03"
    assert candidate["strategy"] == "most_recent_historical_name_compact"


def test_latest_historical_candidate_excludes_current_name_equivalent() -> None:
    body = {
        "navn": "Samme Navn AS",
        "historiskeNavn": [
            {"navn": "SAMME NAVN ASA", "tilDato": "2025-01-01"},
            {"navn": "Tidligere Merke AS", "tilDato": "2024-01-01"},
        ],
    }
    candidate = module.latest_historical_candidate(body)
    assert candidate is not None
    assert candidate["domain"] == "tidligeremerke.no"


def test_latest_historical_candidate_abstains_without_distinct_name() -> None:
    body = {
        "navn": "Samme Navn AS",
        "historiskeNavn": [{"navn": "Samme Navn ASA", "tilDato": "2025-01-01"}],
    }
    assert module.latest_historical_candidate(body) is None
