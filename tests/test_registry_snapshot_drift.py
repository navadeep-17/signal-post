from __future__ import annotations

import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import (  # noqa: E402
    profiles_from_bulk,
    terminal_envelope,
    validate_envelopes,
)
from norway_company_agent.evidence import evidence  # noqa: E402
from norway_company_agent.output_contract import (  # noqa: E402
    project_terminal_envelope,
    validate_contract_object,
)
from norway_company_agent.wikidata_discovery import discover_final_website_with_wikidata  # noqa: E402


PRESENT_ORG = "923609016"
MISSING_ORG = "928987728"


def _write_bulk(path: Path) -> None:
    header = ";".join(
        [
            "organisasjonsnummer",
            "navn",
            "organisasjonsform.kode",
            "antallAnsatte",
            "konkurs",
            "underAvvikling",
            "forretningsadresse.kommune",
            "forretningsadresse.kommunenummer",
            "naeringskode1.kode",
            "naeringskode1.beskrivelse",
            "hjemmeside",
            "sisteInnsendteAarsregnskap",
        ]
    )
    row = ";".join(
        [
            PRESENT_ORG,
            "Example AS",
            "AS",
            "4",
            "false",
            "false",
            "OSLO",
            "0301",
            "62.010",
            "Programmeringstjenester",
            "example.no",
            "2025",
        ]
    )
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write(header + "\n" + row + "\n")


def test_profiles_from_bulk_keeps_missing_snapshot_entity(tmp_path: Path) -> None:
    bulk = tmp_path / "brreg.csv.gz"
    _write_bulk(bulk)

    profiles, metadata = profiles_from_bulk(bulk, [PRESENT_ORG, MISSING_ORG])

    assert [row["organisation_number"] for row in profiles] == [PRESENT_ORG, MISSING_ORG]
    assert metadata["requested"] == 2
    assert metadata["selected"] == 1
    assert metadata["missing_count"] == 1
    assert metadata["missing_organisation_numbers"] == [MISSING_ORG]

    present, missing = profiles
    assert present["name"] == "Example AS"
    assert present["evidence"]["registry"]["status"] == "available"

    assert missing["registry_snapshot_missing"] is True
    assert set(missing) == {"organisation_number", "registry_snapshot_missing", "evidence"}
    assert missing["evidence"]["registry"]["status"] == "not_found"
    assert missing["evidence"]["accounting_obligation"]["status"] == "not_found"
    assert missing["evidence"]["registry"]["source_row_key"] == MISSING_ORG
    assert missing["evidence"]["registry"]["content_sha256"] == metadata["registry_snapshot_sha256"]


def test_snapshot_missing_profile_abstains_from_name_domain_discovery(tmp_path: Path) -> None:
    bulk = tmp_path / "brreg.csv.gz"
    _write_bulk(bulk)
    missing = profiles_from_bulk(bulk, [MISSING_ORG])[0][0]

    row, metrics = discover_final_website_with_wikidata(
        missing,
        wikidata_candidate=None,
        timeout=0.1,
    )

    assert metrics["requests"] == 0
    assert metrics["promoted"] is False
    assert row["evidence"]["website"]["status"] == "not_found"
    assert not row.get("website")


def test_snapshot_missing_entity_can_emit_completed_terminal_contract(tmp_path: Path) -> None:
    bulk = tmp_path / "brreg.csv.gz"
    _write_bulk(bulk)
    profile = profiles_from_bulk(bulk, [MISSING_ORG])[0][0]

    # The real final runner still attempts these official live modules. Model the case where
    # they also cannot resolve the organisation; every state is explicit rather than dropped.
    for module in ("registry_live", "financials", "roles", "group", "locations"):
        profile["evidence"][module] = evidence(
            module,
            "not_found",
            f"official_{module}",
            f"https://example.test/{MISSING_ORG}/{module}",
            note="fixture: absent from live official source",
            source_row_key=MISSING_ORG,
            retrieved_at="2026-09-15T00:00:00Z",
        )
    profile["evidence"]["website"] = evidence(
        "website",
        "not_found",
        "bounded_zero_cost_site_discovery",
        f"https://example.test/{MISSING_ORG}/website",
        note="No safe website candidate without legal-name evidence.",
        source_row_key=MISSING_ORG,
        retrieved_at="2026-09-15T00:00:00Z",
    )
    profile["run_metrics"] = {
        "logical_requests": 5,
        "requests": 10,
        "latencies_ms": [],
        "third_party_cost_usd": 0.0,
    }

    modules = [
        "registry",
        "accounting_obligation",
        "registry_live",
        "financials",
        "roles",
        "group",
        "locations",
        "website",
    ]
    envelope = terminal_envelope(
        profile,
        run_id="snapshot-drift-test",
        modules=modules,
        started_at="2026-09-15T00:00:00Z",
        completed_at="2026-09-15T00:00:01Z",
    )
    validation = validate_envelopes([envelope], 1)
    projected = project_terminal_envelope(envelope, third_party_cost_usd=0.0)

    assert envelope["state"] == "complete"
    assert envelope["modules"]["registry"]["state"] == "not_found"
    assert envelope["modules"]["accounting_obligation"]["state"] == "not_found"
    assert validation["passed"] is True
    assert projected["run"]["terminal_status"] == "completed"
    assert validate_contract_object(projected) == []
    assert not any(
        claim["field"] in {"legal_name", "legal_form", "municipality", "official_website"}
        and claim["availability"] == "available"
        for claim in projected["claims"]
    )
    accounting = next(claim for claim in projected["claims"] if claim["field"] == "accounting_obligation")
    assert accounting["availability"] == "not_available"
    assert accounting["value"] is None
