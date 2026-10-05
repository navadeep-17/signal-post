from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection
from norway_company_agent.external_footprint import publishable_observation, validate_observation
from norway_company_agent.support_contract import project_support_award_observations
from norway_company_agent.support_registry import parse_support_award_snapshot


HEADERS = [
    "Støttetiltaksnummer",
    "Status",
    "Støttetiltakstype",
    "Organisasjonsnummer støttemottaker",
    "Spesifisert mottaker - Organisasjonsnummer",
    "Navn støttemottaker",
    "Organisasjonsnummer støttegiver",
    "Navn støttegiver",
    "Tildelingsdato",
    "Tildelt beløp",
    "Tildelt beløp valuta",
    "Beløpsintervall fra beløp",
    "Beløpsintervall til beløp",
    "Beløpsintervall valuta",
]


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def _write_snapshot(path: Path) -> None:
    _write_rows(
        path,
        [
            {
                "Støttetiltaksnummer": "1000295424",
                "Status": "Registrert",
                "Støttetiltakstype": "Støttetildeling med statsstøtte",
                "Organisasjonsnummer støttemottaker": "917 403 376",
                "Spesifisert mottaker - Organisasjonsnummer": "",
                "Navn støttemottaker": "HOV AS",
                "Organisasjonsnummer støttegiver": "970187715",
                "Navn støttegiver": "MIDTRE GAULDAL KOMMUNE",
                "Tildelingsdato": "16.09.2026",
                "Tildelt beløp": "42 500,00",
                "Tildelt beløp valuta": "NOK",
            },
            {
                "Støttetiltaksnummer": "old",
                "Status": "Registrert",
                "Støttetiltakstype": "Tilskudd",
                "Organisasjonsnummer støttemottaker": "917403376",
                "Spesifisert mottaker - Organisasjonsnummer": "",
                "Navn støttemottaker": "HOV AS",
                "Organisasjonsnummer støttegiver": "970187715",
                "Navn støttegiver": "MIDTRE GAULDAL KOMMUNE",
                "Tildelingsdato": "01.01.2024",
                "Tildelt beløp": "1",
                "Tildelt beløp valuta": "NOK",
            },
            {
                "Støttetiltaksnummer": "giver-only",
                "Status": "Registrert",
                "Støttetiltakstype": "Tilskudd",
                "Organisasjonsnummer støttemottaker": "811934232",
                "Spesifisert mottaker - Organisasjonsnummer": "",
                "Navn støttemottaker": "OTHER",
                "Organisasjonsnummer støttegiver": "917403376",
                "Navn støttegiver": "HOV AS",
                "Tildelingsdato": "20.09.2026",
                "Tildelt beløp": "99",
                "Tildelt beløp valuta": "NOK",
            },
            {
                "Støttetiltaksnummer": "specified-only",
                "Status": "Registrert",
                "Støttetiltakstype": "Tilskudd",
                "Organisasjonsnummer støttemottaker": "811934232",
                "Spesifisert mottaker - Organisasjonsnummer": "917403376",
                "Navn støttemottaker": "DIRECT OTHER",
                "Organisasjonsnummer støttegiver": "970187715",
                "Navn støttegiver": "MIDTRE GAULDAL KOMMUNE",
                "Tildelingsdato": "21.09.2026",
                "Tildelt beløp": "123",
                "Tildelt beløp valuta": "NOK",
            },
        ],
    )


def test_recent_exact_recipient_award_is_publishable_and_giver_is_not_identity(tmp_path: Path):
    snapshot = tmp_path / "stotte.csv"
    _write_snapshot(snapshot)
    rows, report = parse_support_award_snapshot(
        snapshot,
        {"917403376"},
        snapshot_sha256="a" * 64,
        retrieved_at="2026-10-04T00:00:00Z",
        as_of=date(2026, 10, 4),
    )

    assert report["companies_with_recent_awards"] == 1
    assert len(rows["917403376"]) == 1
    observation = rows["917403376"][0]
    assert observation["event"]["amount"] == "42500.00"
    assert observation["event"]["currency"] == "NOK"
    assert observation["event"]["amount_interval_from"] is None
    assert observation["event"]["amount_interval_to"] is None
    assert observation["event"]["amount_interval_currency"] is None
    assert observation["event"]["support_measure_number"] == "1000295424"
    assert observation["effective_at"] == "2026-09-16"
    assert observation["content_sha256"] != observation["source_snapshot_sha256"]
    assert "primary recipient organisation number" in observation["identity_proof"]
    assert observation["event"]["specified_recipient_organisation_number"] is None
    assert validate_observation(observation) == []
    assert publishable_observation(observation)


def test_specified_recipient_only_never_upgrades_company_identity(tmp_path: Path):
    snapshot = tmp_path / "stotte.csv"
    _write_snapshot(snapshot)
    rows, report = parse_support_award_snapshot(
        snapshot,
        {"917403376"},
        snapshot_sha256="a" * 64,
        retrieved_at="2026-10-04T00:00:00Z",
        as_of=date(2026, 10, 4),
    )

    assert report["companies_with_recent_awards"] == 1
    assert [item["event"]["support_measure_number"] for item in rows["917403376"]] == ["1000295424"]


def test_interval_currency_is_preserved_without_inventing_nok(tmp_path: Path):
    snapshot = tmp_path / "stotte-interval.csv"
    _write_rows(
        snapshot,
        [
            {
                "Støttetiltaksnummer": "interval",
                "Status": "Registrert",
                "Støttetiltakstype": "Tilskudd",
                "Organisasjonsnummer støttemottaker": "917403376",
                "Navn støttemottaker": "HOV AS",
                "Organisasjonsnummer støttegiver": "970187715",
                "Navn støttegiver": "MIDTRE GAULDAL KOMMUNE",
                "Tildelingsdato": "16.09.2026",
                "Tildelt beløp": "",
                "Tildelt beløp valuta": "",
                "Beløpsintervall fra beløp": "1 000,50",
                "Beløpsintervall til beløp": "5 000,00",
                "Beløpsintervall valuta": "EUR",
            }
        ],
    )
    rows, report = parse_support_award_snapshot(
        snapshot,
        {"917403376"},
        snapshot_sha256="a" * 64,
        retrieved_at="2026-10-04T00:00:00Z",
        as_of=date(2026, 10, 4),
    )

    assert report["companies_with_recent_awards"] == 1
    event = rows["917403376"][0]["event"]
    assert event["amount"] is None
    assert event["currency"] is None
    assert event["amount_interval_from"] == "1000.50"
    assert event["amount_interval_to"] == "5000.00"
    assert event["amount_interval_currency"] == "EUR"
    assert "EUR" in rows["917403376"][0]["evidence_span"]


def test_support_projection_is_explicit_idempotent_and_canonical_public_activity(tmp_path: Path):
    snapshot = tmp_path / "stotte.csv"
    _write_snapshot(snapshot)
    rows, _ = parse_support_award_snapshot(
        snapshot,
        {"917403376"},
        snapshot_sha256="a" * 64,
        retrieved_at="2026-10-04T00:00:00Z",
        as_of=date(2026, 10, 4),
    )
    profile = {
        "organisation_number": "917403376",
        "external_observations": rows["917403376"],
    }
    contract = {"organisation_number": "917403376", "claims": [], "evidence": []}

    projected = project_support_award_observations(contract, profile)
    projected = project_support_award_observations(projected, profile)
    claims = [claim for claim in projected["claims"] if claim["field"] == "official.support_award"]
    assert len(claims) == 1
    assert claims[0]["value"]["kind"] == "support_award"
    assert claims[0]["signal_type"] == "official_support_award"
    assert len(projected["evidence"]) == 1
    assert projected["evidence"][0]["effective_at"] == "2026-09-16"

    canonical = project_canonical_profile(projected)
    support = [fact for fact in canonical["canonical_facts"] if fact["type"] == "support_award"]
    assert len(support) == 1
    assert support[0]["canonical_field"] == "public.official_support_award"
    assert support[0] in canonical["canonical_profile"]["public_activity"]
    assert validate_canonical_projection(canonical) == []
