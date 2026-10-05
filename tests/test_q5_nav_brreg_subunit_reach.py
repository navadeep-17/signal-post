from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from screen_q5_nav_brreg_subunit_reach import (  # noqa: E402
    embedded_subunits,
    extract_nav_token,
    fetch_official_identity_aliases,
    normalize_name,
    screen,
)


def _profile(org="900000001", name="EXAMPLE AS"):
    return {"organisation_number": org, "name": name, "legal_name": name}


def _brreg_body(main="900000001", child="900000010", name="EXAMPLE OSLO"):
    return {
        "_embedded": {
            "underenheter": [
                {
                    "organisasjonsnummer": child,
                    "overordnetEnhet": main,
                    "navn": name,
                }
            ]
        },
        "page": {"totalPages": 1, "number": 0},
    }


def _feed_item(uuid, business_name, status="ACTIVE", modified="2026-10-01T10:00:00Z"):
    return {
        "id": uuid,
        "url": f"/api/v1/feedentry/{uuid}",
        "date_modified": modified,
        "_feed_entry": {
            "uuid": uuid,
            "status": status,
            "businessName": business_name,
            "sistEndret": modified,
        },
    }


def _detail(uuid, employer_org, employer_name="EXAMPLE OSLO", status="ACTIVE"):
    return {
        "uuid": uuid,
        "status": status,
        "ad_content": {
            "uuid": uuid,
            "title": "Software Engineer",
            "published": "2026-09-20T00:00:00Z",
            "expires": "2026-11-01T00:00:00Z",
            "link": f"https://arbeidsplassen.nav.no/stillinger/stilling/{uuid}",
            "applicationUrl": "https://example.no/apply",
            "employer": {"name": employer_name, "orgnr": employer_org},
        },
    }


def test_helpers_parse_hal_and_prefixed_token() -> None:
    assert embedded_subunits(_brreg_body()) == _brreg_body()["_embedded"]["underenheter"]
    assert extract_nav_token(b"Public token:\naaa.bbb.ccc\n") == "aaa.bbb.ccc"
    assert normalize_name("Example Oslo AS") == "example oslo"


def test_brreg_aliases_accept_only_exact_children_of_target_and_skip_deleted() -> None:
    def fetcher(url, *, headers, timeout):
        return {
            "_embedded": {
                "underenheter": [
                    {"organisasjonsnummer": "900000010", "overordnetEnhet": "900000001", "navn": "Example Oslo"},
                    {"organisasjonsnummer": "900000011", "overordnetEnhet": "999999999", "navn": "Wrong Parent"},
                    {"organisasjonsnummer": "900000012", "overordnetEnhet": "900000001", "navn": "Closed Shop", "slettedato": "2026-01-01"},
                ]
            },
            "page": {"totalPages": 1},
        }, 100

    aliases, accepted, metrics = fetch_official_identity_aliases([_profile()], timeout=1, brreg_fetcher=fetcher)
    assert ("900000001", "900000001") in aliases["example"]
    assert aliases["example oslo"] == {("900000001", "900000010")}
    assert "wrong parent" not in aliases
    assert "closed shop" not in aliases
    assert accepted == {"900000001": "900000001", "900000010": "900000001"}
    assert metrics["active_subunits"] == 1


def test_screen_promotes_exact_official_subunit_vacancy() -> None:
    def brreg_fetcher(url, *, headers, timeout):
        return _brreg_body(), 100

    def token_fetcher(url, *, timeout):
        return b"public token:\naaa.bbb.ccc", {}

    def nav_fetcher(url, *, token, if_modified_since, timeout):
        assert token == "aaa.bbb.ccc"
        if "/feedentry/" not in url:
            return {
                "items": [_feed_item("u1", "Example Oslo")],
                "next_url": None,
                "next_id": None,
            }, 100
        return _detail("u1", "900000010"), 200

    report = screen(
        [_profile()],
        now=datetime(2026, 10, 5, tzinfo=timezone.utc),
        brreg_fetcher=brreg_fetcher,
        token_fetcher=token_fetcher,
        nav_fetcher=nav_fetcher,
    )
    assert report["companies_with_exact_active_vacancies"] == 1
    assert report["exact_active_vacancies"] == 1
    hit = report["exact_hits"][0]
    assert hit["main_target_org"] == "900000001"
    assert hit["employing_org"] == "900000010"
    assert hit["relationship"] == "official_brreg_subunit"
    assert hit["identity_method"] == "nav_employer_orgnr_exact_brreg_main_or_subunit_v1"


def test_recruiter_business_name_with_unrelated_client_employer_is_rejected() -> None:
    def brreg_fetcher(url, *, headers, timeout):
        return _brreg_body(name="EXAMPLE BRANCH"), 100

    def token_fetcher(url, *, timeout):
        return b"aaa.bbb.ccc", {}

    def nav_fetcher(url, *, token, if_modified_since, timeout):
        if "/feedentry/" not in url:
            return {
                "items": [_feed_item("u1", "Example AS")],
                "next_url": None,
                "next_id": None,
            }, 100
        return _detail("u1", "888888888", employer_name="Client Company"), 200

    report = screen(
        [_profile()],
        now=datetime(2026, 10, 5, tzinfo=timezone.utc),
        brreg_fetcher=brreg_fetcher,
        token_fetcher=token_fetcher,
        nav_fetcher=nav_fetcher,
    )
    assert report["exact_hits"] == []
    assert report["companies_with_exact_active_vacancies"] == 0
    assert report["rejected_active_shortlist_details"][0]["employer_org"] == "888888888"


def test_same_subunit_name_for_multiple_targets_still_requires_exact_employer_org() -> None:
    profiles = [_profile("900000001", "ALPHA AS"), _profile("900000002", "BETA AS")]

    def brreg_fetcher(url, *, headers, timeout):
        if "900000001" in url:
            return _brreg_body("900000001", "900000010", "Shared Shop"), 100
        return _brreg_body("900000002", "900000020", "Shared Shop"), 100

    def token_fetcher(url, *, timeout):
        return b"aaa.bbb.ccc", {}

    def nav_fetcher(url, *, token, if_modified_since, timeout):
        if "/feedentry/" not in url:
            return {"items": [_feed_item("u1", "Shared Shop")], "next_url": None, "next_id": None}, 100
        return _detail("u1", "900000020", employer_name="Shared Shop"), 200

    report = screen(
        profiles,
        now=datetime(2026, 10, 5, tzinfo=timezone.utc),
        brreg_fetcher=brreg_fetcher,
        token_fetcher=token_fetcher,
        nav_fetcher=nav_fetcher,
    )
    assert report["organisation_numbers_with_exact_active_vacancies"] == ["900000002"]
    assert report["exact_hits"][0]["employing_org"] == "900000020"
