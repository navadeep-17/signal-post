from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.annual_report_site_nomination import (
    extract_annual_report_site_candidates,
)


def _profile() -> dict:
    return {
        "organisation_number": "999096298",
        "name": "DEN GLADE GRIS AS",
        "municipality": "OSLO",
    }


def test_exact_org_report_can_nominate_explicit_company_url() -> None:
    text = """
    DEN GLADE GRIS AS
    Organisasjonsnummer 999 096 298
    Kontakt og informasjon: https://www.dengladegris.no/kontakt
    """
    rows = extract_annual_report_site_candidates(_profile(), text)
    assert rows
    assert rows[0]["domain"] == "dengladegris.no"
    assert rows[0]["url"] == "https://dengladegris.no/"
    assert "999 096 298" in rows[0]["evidence_span"]


def test_report_without_exact_org_number_cannot_nominate() -> None:
    text = """
    DEN GLADE GRIS AS
    Se www.dengladegris.no for mer informasjon.
    """
    assert extract_annual_report_site_candidates(_profile(), text) == []


def test_social_and_official_domains_are_filtered() -> None:
    text = """
    DEN GLADE GRIS AS org.nr. 999096298
    https://www.facebook.com/dengladegrisen
    https://www.brreg.no/
    https://www.dengladegris.no/
    """
    rows = extract_annual_report_site_candidates(_profile(), text)
    assert [row["domain"] for row in rows] == ["dengladegris.no"]


def test_duplicate_domain_is_deduplicated() -> None:
    text = """
    Organisasjonsnummer 999096298
    https://dengladegris.no/
    www.dengladegris.no
    https://www.dengladegris.no/kontakt
    """
    rows = extract_annual_report_site_candidates(_profile(), text)
    assert len(rows) == 1
    assert rows[0]["domain"] == "dengladegris.no"
