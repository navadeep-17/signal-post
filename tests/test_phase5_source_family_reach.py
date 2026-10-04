import csv
import json
from pathlib import Path

from scripts.screen_phase5_source_family_reach import (
    candidate_org_columns,
    extract_org_numbers,
    load_targets,
    normalize_header,
    role_for_header,
    screen_csv,
    valid_org_number,
)


def write_cohort(path: Path) -> None:
    rows = [
        {"organisation_number": "974760673", "name": "BRØNNØYSUNDREGISTRENE"},
        {"organisation_number": "918065326", "name": "DUUS CONSULT AS"},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_mod11_and_extraction_reject_arbitrary_digits():
    assert valid_org_number("974760673")
    assert not valid_org_number("974760674")
    assert extract_org_numbers("Org.nr 974 760 673 / phone 123456789") == {"974760673"}


def test_normalize_header_preserves_norwegian_semantics():
    assert normalize_header("Organisasjonsnummer støttemottaker") == "organisasjonsnummer stottemottaker"
    assert normalize_header("Beløp / næring") == "belop naering"


def test_candidate_columns_require_org_semantics():
    headers = ["Mottaker organisasjonsnummer", "Telefon", "Beløp"]
    assert candidate_org_columns(headers, "stotteregisteret") == ["Mottaker organisasjonsnummer"]


def test_stotte_columns_exclude_granting_authority():
    headers = [
        "Organisasjonsnummer støttemottaker",
        "Organisasjonsnummer spesifisert støttemottaker",
        "Organisasjonsnummer støttegiver",
    ]
    assert candidate_org_columns(headers, "stotteregisteret") == headers[:2]
    assert role_for_header(headers[0]) == "recipient"
    assert role_for_header(headers[2]) == "granting_authority"


def test_stotte_screen_counts_exact_target_company(tmp_path: Path):
    cohort = tmp_path / "cohort.jsonl"
    write_cohort(cohort)
    csv_path = tmp_path / "stotte.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Organisasjonsnummer støttemottaker",
                "Organisasjonsnummer støttegiver",
                "Tildelingsdato",
                "Beløp",
            ],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerow(
            {
                "Organisasjonsnummer støttemottaker": "974 760 673",
                "Organisasjonsnummer støttegiver": "918065326",
                "Tildelingsdato": "2026-08-04",
                "Beløp": "264000",
            }
        )
    report = screen_csv(csv_path, "stotteregisteret", load_targets(cohort))
    assert report["status"] == "screened"
    assert report["matched_companies"] == 1
    assert report["matched_organisation_numbers"] == ["974760673"]
    assert report["detected_column_roles"] == {"recipient": 1}
    assert report["publication_enabled"] is False
    assert report["candidate_only"] is True


def test_doffin_screen_keeps_role_scoped_exact_identifier(tmp_path: Path):
    cohort = tmp_path / "cohort.jsonl"
    write_cohort(cohort)
    csv_path = tmp_path / "doffin.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["Winner organisation identifier", "Notice id", "Title"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "Winner organisation identifier": "NO-918065326",
                "Notice id": "x1",
                "Title": "Example award",
            }
        )
    report = screen_csv(csv_path, "doffin", load_targets(cohort))
    assert report["matched_companies"] == 1
    assert report["matched_organisation_numbers"] == ["918065326"]
    assert report["matched_row_roles"]["supplier_or_winner"] == 1
