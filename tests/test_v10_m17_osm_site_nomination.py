from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent import osm_site_nomination as osm  # noqa: E402


def _profile() -> dict:
    return {
        "organisation_number": "999096298",
        "name": "DEN GLADE GRIS AS",
        "municipality": "OSLO",
        "business_address": {
            "adresse": ["St. Olavs gate 33"],
            "postnummer": "0166",
            "kommune": "OSLO",
        },
        "website": "",
        "evidence": {"website": {"status": "not_found"}},
    }


class _Response:
    def __init__(self, payload: list[dict]):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, *_args, **_kwargs):
        return json.dumps(self.payload).encode("utf-8")


def test_name_plus_postcode_can_nominate_website(monkeypatch) -> None:
    payload = [{
        "osm_type": "node",
        "osm_id": 123,
        "display_name": "Den Glade Gris, St. Olavs gate 33, Oslo, Norway",
        "namedetails": {"name": "Den Glade Gris"},
        "address": {"postcode": "0166", "city": "Oslo"},
        "extratags": {"website": "https://www.dengladegris.no/"},
    }]
    monkeypatch.setattr(osm.urllib.request, "urlopen", lambda *a, **k: _Response(payload))
    sleeps: list[float] = []
    candidate, audit = osm.nominate_osm_website(
        _profile(),
        sleeper=sleeps.append,
        min_interval_seconds=1.05,
    )
    assert candidate is not None
    assert candidate["url"] == "https://dengladegris.no/"
    assert candidate["location_basis"] == "postcode"
    assert audit["requests"] == 1
    assert sleeps == [1.05]


def test_wrong_location_never_nominates(monkeypatch) -> None:
    payload = [{
        "osm_type": "node",
        "osm_id": 123,
        "display_name": "Den Glade Gris, Bergen, Norway",
        "namedetails": {"name": "Den Glade Gris"},
        "address": {"postcode": "5003", "city": "Bergen"},
        "extratags": {"website": "https://www.dengladegris.no/"},
    }]
    monkeypatch.setattr(osm.urllib.request, "urlopen", lambda *a, **k: _Response(payload))
    candidate, audit = osm.nominate_osm_website(_profile(), sleeper=lambda _: None)
    assert candidate is None
    assert audit["reviewed_results"][0]["name_match"] is True
    assert audit["reviewed_results"][0]["location_match"] is False


def test_wrong_name_never_nominates(monkeypatch) -> None:
    payload = [{
        "osm_type": "node",
        "osm_id": 123,
        "display_name": "Completely Different Restaurant, Oslo, Norway",
        "namedetails": {"name": "Completely Different Restaurant"},
        "address": {"postcode": "0166", "city": "Oslo"},
        "extratags": {"website": "https://www.dengladegris.no/"},
    }]
    monkeypatch.setattr(osm.urllib.request, "urlopen", lambda *a, **k: _Response(payload))
    candidate, audit = osm.nominate_osm_website(_profile(), sleeper=lambda _: None)
    assert candidate is None
    assert audit["reviewed_results"][0]["name_match"] is False
    assert audit["reviewed_results"][0]["location_match"] is True


def test_social_profile_url_is_not_a_company_website_candidate(monkeypatch) -> None:
    payload = [{
        "osm_type": "node",
        "osm_id": 123,
        "display_name": "Den Glade Gris, Oslo, Norway",
        "namedetails": {"name": "Den Glade Gris"},
        "address": {"postcode": "0166", "city": "Oslo"},
        "extratags": {"website": "https://facebook.com/dengladegrisen"},
    }]
    monkeypatch.setattr(osm.urllib.request, "urlopen", lambda *a, **k: _Response(payload))
    candidate, audit = osm.nominate_osm_website(_profile(), sleeper=lambda _: None)
    assert candidate is None
    assert audit["reviewed_results"][0]["candidate_url"] is None


def test_conflicting_org_number_forces_abstention(monkeypatch) -> None:
    website = {
        "status": "available",
        "source_url": "https://dengladegris.no/",
        "value": {},
    }
    assessment = {
        "status": "exact",
        "score": 1.0,
        "publishable": True,
        "method": "fixture",
        "reasons": [],
    }
    monkeypatch.setattr(osm, "_has_conflicting_explicit_org_number", lambda p, w: True)
    q = osm.qualify_osm_candidate_identity(_profile(), website, assessment)
    assert q is not None
    assert q["publishable"] is False
    assert q["status"] == "review"


def test_name_only_page_without_registry_location_never_authorizes(monkeypatch) -> None:
    website = {
        "status": "available",
        "source_url": "https://dengladegris.no/",
        "value": {},
    }
    assessment = {
        "status": "exact",
        "score": 0.95,
        "publishable": True,
        "method": "fixture",
        "reasons": [],
    }
    monkeypatch.setattr(osm, "_has_conflicting_explicit_org_number", lambda p, w: False)
    monkeypatch.setattr(osm, "_page_contains_org_number", lambda p, w: False)
    monkeypatch.setattr(osm, "_page_contains_full_legal_name", lambda p, w: True)
    monkeypatch.setattr(osm, "_page_matches_registry_location", lambda p, w: False)
    q = osm.qualify_osm_candidate_identity(_profile(), website, assessment)
    assert q is not None
    assert q["publishable"] is False


def test_flattened_bulk_registry_address_is_supported() -> None:
    profile = {
        "organisation_number": "999096298",
        "name": "DEN GLADE GRIS AS",
        "municipality": "OSLO",
        "evidence": {
            "registry": {
                "status": "available",
                "value": {
                    "forretningsadresse.kommune": "OSLO",
                    "forretningsadresse.postnummer": "0166",
                    "forretningsadresse.adresse": "St. Olavs gate 33",
                },
            },
            "website": {"status": "not_found"},
        },
    }
    query = osm._address_query(profile)
    assert "St. Olavs gate 33" in query
    assert "0166" in query
    assert "OSLO" in query
