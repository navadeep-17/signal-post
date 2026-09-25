from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.output_contract import project_terminal_envelope  # noqa: E402
from norway_company_agent.sampling import normalize_row  # noqa: E402


def test_normalize_row_preserves_structured_industry_without_changing_stratum_keys() -> None:
    row = {
        "organisasjonsnummer": "923609016",
        "navn": "ACME NORGE AS",
        "organisasjonsform.kode": "AS",
        "antallAnsatte": "3",
        "forretningsadresse.kommune": "OSLO",
        "forretningsadresse.kommunenummer": "0301",
        "naeringskode1.kode": "62.010",
        "naeringskode1.beskrivelse": "Programmeringstjenester",
        "sisteInnsendteAarsregnskap": "2025",
    }
    profile = normalize_row(row)

    assert profile["industry_code"] == "62.010"
    assert profile["industry_label"] == "Programmeringstjenester"
    assert profile["industry"] == {"code": "62.010", "label": "Programmeringstjenester"}


def test_bulk_industry_is_projected_as_an_official_claim() -> None:
    row = {
        "organisasjonsnummer": "923609016",
        "navn": "ACME NORGE AS",
        "organisasjonsform.kode": "AS",
        "antallAnsatte": "3",
        "forretningsadresse.kommune": "OSLO",
        "forretningsadresse.kommunenummer": "0301",
        "naeringskode1.kode": "62.010",
        "naeringskode1.beskrivelse": "Programmeringstjenester",
        "sisteInnsendteAarsregnskap": "2025",
    }
    profile = normalize_row(row)
    profile["run_metrics"] = {"requests": 0, "latencies_ms": []}
    profile["evidence"] = {
        "registry": {
            "status": "available",
            "source_type": "official_registry_bulk",
            "source_class": "official_registry_bulk",
            "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
            "retrieved_at": "2026-09-25T00:00:00Z",
            "content_sha256": "bulkhash",
            "source_row_key": "923609016",
            "value": row,
        }
    }
    envelope = {
        "run_id": "v2-bulk-test",
        "organisation_number": "923609016",
        "state": "complete",
        "started_at": "2026-09-25T00:00:00Z",
        "completed_at": "2026-09-25T00:00:01Z",
        "modules": {},
        "profile": profile,
    }

    output = project_terminal_envelope(envelope)
    industry = next(claim for claim in output["claims"] if claim["field"] == "industry")
    assert industry["availability"] == "available"
    assert industry["value"] == {"code": "62.010", "label": "Programmeringstjenester"}
    evidence = {entry["id"]: entry for entry in output["evidence"]}
    assert industry["evidence_ids"][0] in evidence
    assert evidence[industry["evidence_ids"][0]]["source_class"] == "official"
