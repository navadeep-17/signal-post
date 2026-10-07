from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent import h1i_multitoken_compact_com as h1i  # noqa: E402


def _profile(name: str = "ALPINE DESIGN AS") -> dict:
    return {
        "organisation_number": "999096298",
        "name": name,
        "municipality": "OSLO",
        "website": "",
        "evidence": {"website": {"status": "not_found"}},
    }


def test_multitoken_name_gets_compact_com_candidate() -> None:
    assert h1i.multitoken_compact_com_candidate(_profile()) == {
        "domain": "alpinedesign.com",
        "url": "https://alpinedesign.com/",
        "strategy": "multi_token_legal_name_compact_com",
    }


def test_single_token_name_is_out_of_scope() -> None:
    assert h1i.multitoken_compact_com_candidate(_profile("PRIMO AS")) is None


def test_exact_org_number_can_authorize_independently_fetched_candidate(monkeypatch) -> None:
    website = {"status": "available", "source_url": "https://alpinedesign.com/", "value": {}}
    assessment = {
        "status": "exact",
        "score": 0.95,
        "publishable": True,
        "method": "fixture",
        "reasons": [],
    }
    monkeypatch.setattr(h1i, "_has_conflicting_explicit_org_number", lambda profile, site: False)
    monkeypatch.setattr(h1i, "_page_contains_org_number", lambda profile, site: True)
    q = h1i.qualify_multitoken_compact_com_identity(_profile(), website, assessment)
    assert q is not None
    assert q["publishable"] is True
    assert q["score"] == 1.0
    assert q["method"] == "h1i_multitoken_compact_com_identity_v1"


def test_conflicting_org_number_forces_abstention(monkeypatch) -> None:
    website = {"status": "available", "source_url": "https://alpinedesign.com/", "value": {}}
    assessment = {
        "status": "exact",
        "score": 1.0,
        "publishable": True,
        "method": "fixture",
        "reasons": [],
    }
    monkeypatch.setattr(h1i, "_has_conflicting_explicit_org_number", lambda profile, site: True)
    q = h1i.qualify_multitoken_compact_com_identity(_profile(), website, assessment)
    assert q is not None
    assert q["publishable"] is False
    assert q["status"] == "review"


def test_full_name_without_location_is_not_enough(monkeypatch) -> None:
    website = {"status": "available", "source_url": "https://alpinedesign.com/", "value": {}}
    assessment = {
        "status": "exact",
        "score": 0.95,
        "publishable": True,
        "method": "fixture",
        "reasons": [],
    }
    monkeypatch.setattr(h1i, "_has_conflicting_explicit_org_number", lambda profile, site: False)
    monkeypatch.setattr(h1i, "_page_contains_org_number", lambda profile, site: False)
    monkeypatch.setattr(h1i, "_page_contains_full_legal_name", lambda profile, site: True)
    monkeypatch.setattr(h1i, "_page_matches_registry_location", lambda profile, site: False)
    q = h1i.qualify_multitoken_compact_com_identity(_profile(), website, assessment)
    assert q is not None
    assert q["publishable"] is False
