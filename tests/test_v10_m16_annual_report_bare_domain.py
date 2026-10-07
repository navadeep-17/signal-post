from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.annual_report_site_nomination import (
    extract_annual_report_bare_no_candidates,
)


def _profile(*, registry_email: str = "") -> dict:
    return {
        "organisation_number": "999096298",
        "name": "DEN GLADE GRIS NORGE AS",
        "municipality": "OSLO",
        "website": "",
        "evidence": {
            "registry": {
                "status": "available",
                "value": {"epostadresse": registry_email},
            }
        },
    }


def test_bare_multi_token_domain_can_be_nominated() -> None:
    text = """
    DEN GLADE GRIS NORGE AS
    Organisasjonsnummer 999 096 298
    Kontakt oss på booking@dengladegris.no for reservasjoner.
    """
    rows = extract_annual_report_bare_no_candidates(_profile(), text)
    assert rows
    assert rows[0]["domain"] == "dengladegris.no"
    assert rows[0]["method"] == "annual_report_email_domain"
    assert rows[0]["identity_strength"] == "multi"


def test_explicit_url_is_left_to_m15_not_m16() -> None:
    text = """
    DEN GLADE GRIS NORGE AS org.nr. 999096298
    https://dengladegris.no/kontakt
    """
    assert extract_annual_report_bare_no_candidates(_profile(), text) == []


def test_registry_email_domain_duplicate_is_excluded() -> None:
    text = """
    DEN GLADE GRIS NORGE AS org.nr. 999096298
    Kontakt booking@dengladegris.no
    """
    rows = extract_annual_report_bare_no_candidates(
        _profile(registry_email="post@dengladegris.no"),
        text,
    )
    assert rows == []


def test_deterministic_compact_and_hyphenated_domains_are_excluded() -> None:
    text = """
    DEN GLADE GRIS NORGE AS org.nr. 999096298
    dengladegrisnorge.no
    den-glade-gris-norge.no
    """
    assert extract_annual_report_bare_no_candidates(_profile(), text) == []


def test_unrelated_service_domain_is_not_admitted() -> None:
    text = """
    DEN GLADE GRIS NORGE AS org.nr. 999096298
    Revisor: post@regnskapspartner.no
    """
    assert extract_annual_report_bare_no_candidates(_profile(), text) == []


def test_exact_org_number_is_required() -> None:
    text = """
    DEN GLADE GRIS NORGE AS
    booking@dengladegris.no
    """
    assert extract_annual_report_bare_no_candidates(_profile(), text) == []
