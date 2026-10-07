from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


def _load():
    path = ROOT / "scripts" / "research_v10_report_domain_diagnostics.py"
    spec = importlib.util.spec_from_file_location("report_domain_diag", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


diag = _load()


def _profile(*, email: str = "") -> dict:
    return {
        "organisation_number": "999096298",
        "name": "DEN GLADE GRIS NORGE AS",
        "municipality": "OSLO",
        "website": "",
        "evidence": {
            "registry": {
                "status": "available",
                "value": {"epostadresse": email},
            }
        },
    }


def _by_domain(rows):
    return {row["domain"]: row for row in rows}


def test_contact_brand_email_domain_can_rank_without_legal_name_similarity() -> None:
    text = """
    DEN GLADE GRIS NORGE AS
    Organisasjonsnummer 999 096 298
    Kontakt / e-post: post@grisrestauranten.no
    """
    rows = _by_domain(diag.domain_mentions(_profile(), text))
    row = rows["grisrestauranten.no"]
    assert row["method"] == "email_domain"
    assert row["email_local"] == "post"
    assert row["identity_strength"] == "none"
    assert row["already_tried"] is False
    assert row["explicit_m15_form"] is False
    assert row["generic_or_service"] is False
    assert row["score"] >= 2


def test_explicit_url_is_marked_as_m15_already_tried() -> None:
    text = """
    DEN GLADE GRIS NORGE AS org.nr. 999096298
    Nettside https://www.grisrestauranten.no/kontakt
    """
    rows = _by_domain(diag.domain_mentions(_profile(), text))
    row = rows["grisrestauranten.no"]
    assert row["explicit_m15_form"] is True
    assert row["already_tried"] is True


def test_registry_email_domain_is_marked_already_tried() -> None:
    text = """
    DEN GLADE GRIS NORGE AS org.nr. 999096298
    Kontakt post@grisrestauranten.no
    """
    rows = _by_domain(
        diag.domain_mentions(
            _profile(email="booking@grisrestauranten.no"),
            text,
        )
    )
    assert rows["grisrestauranten.no"]["already_tried"] is True


def test_deterministic_compact_domain_is_marked_already_tried() -> None:
    text = """
    DEN GLADE GRIS NORGE AS org.nr. 999096298
    Kontakt post@dengladegrisnorge.no
    """
    rows = _by_domain(diag.domain_mentions(_profile(), text))
    assert rows["dengladegrisnorge.no"]["already_tried"] is True


def test_auditor_service_domain_is_flagged_and_penalized() -> None:
    text = """
    DEN GLADE GRIS NORGE AS org.nr. 999096298
    Revisor / audit contact: post@bdo.no
    """
    rows = _by_domain(diag.domain_mentions(_profile(), text))
    row = rows["bdo.no"]
    assert row["generic_or_service"] is True
    assert row["negative_context_hits"]
    assert row["score"] < 2


def test_unrelated_accountant_domain_gets_negative_context_penalty() -> None:
    text = """
    DEN GLADE GRIS NORGE AS org.nr. 999096298
    Regnskapsfører: info@lokalregnskap.no
    """
    rows = _by_domain(diag.domain_mentions(_profile(), text))
    row = rows["lokalregnskap.no"]
    assert "regnskapsfører" in row["negative_context_hits"]
    assert row["score"] < 2


def test_exact_org_number_is_required() -> None:
    text = """
    DEN GLADE GRIS NORGE AS
    Kontakt / e-post: post@grisrestauranten.no
    """
    assert diag.domain_mentions(_profile(), text) == []
