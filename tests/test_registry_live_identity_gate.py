from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.registry_live_contract import project_registry_live_claims  # noqa: E402


def test_live_registry_projection_rejects_mismatched_org_number() -> None:
    contract = {
        "organisation_number": "123456789",
        "claims": [],
        "evidence": [],
    }
    profile = {
        "organisation_number": "123456789",
        "evidence": {
            "registry_live": {
                "status": "available",
                "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/123456789",
                "retrieved_at": "2026-09-25T00:00:00Z",
                "content_sha256": "a" * 64,
                "value": {
                    "organisation_number": "998877665",
                    "name": "WRONG COMPANY AS",
                    "industry": {"kode": "62.010", "beskrivelse": "Programmeringstjenester"},
                },
            }
        },
    }

    projected = project_registry_live_claims(contract, profile)
    assert projected == contract
    assert projected["claims"] == []
    assert projected["evidence"] == []
