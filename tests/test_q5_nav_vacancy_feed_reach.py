from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from screen_q5_nav_vacancy_feed_reach import (  # noqa: E402
    _extract_public_token,
    detail_is_current,
    normalize_company_name,
    screen_nav_feed,
)


def _profile(org: str = "900000001", name: str = "EXAMPLE AS") -> dict:
    return {"organisation_number": org, "name": name}


def _feed_item(
    *,
    uuid: str,
    business_name: str,
    status: str = "ACTIVE",
    modified: str = "2026-10-01T10:00:00Z",
) -> dict:
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


def _detail(
    *,
    uuid: str,
    org: str,
    employer_name: str = "Example",
    status: str = "ACTIVE",
    expires: str = "2026-11-01T00:00:00Z",
) -> dict:
    return {
        "uuid": uuid,
        "status": status,
        "ad_content": {
            "uuid": uuid,
            "published": "2026-09-20T00:00:00Z",
            "expires": expires,
            "updated": "2026-10-01T10:00:00Z",
            "title": "Senior Engineer",
            "jobtitle": "Engineer",
            "link": f"https://arbeidsplassen.nav.no/stillinger/stilling/{uuid}",
            "applicationUrl": "https://example.no/apply",
            "applicationDue": "2026-10-30",
            "source": "DIR",
            "employer": {
                "name": employer_name,
                "orgnr": org,
                "homepage": "https://example.no/",
            },
        },
    }


def test_company_name_normalization_removes_common_legal_suffix_only() -> None:
    assert normalize_company_name("  Eksempel-Teknologi AS ") == "eksempel teknologi"
    assert normalize_company_name("SA ASKER AS") == "sa asker"
    assert normalize_company_name("Fosen Skjønnhet ENK") == "fosen skjønnhet"


def test_public_token_parser_accepts_plain_or_json_jwt() -> None:
    token = "aaa.bbb.ccc"
    assert _extract_public_token(token.encode()) == token
    assert _extract_public_token(f'{{"token":"{token}"}}'.encode()) == token


def test_detail_currentness_requires_active_and_nonexpired() -> None:
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    assert detail_is_current(_detail(uuid="u1", org="900000001"), now=now) is True
    assert detail_is_current(_detail(uuid="u1", org="900000001", status="INACTIVE"), now=now) is False
    assert detail_is_current(
        _detail(uuid="u1", org="900000001", expires="2026-10-01T00:00:00Z"),
        now=now,
    ) is False


def test_screen_counts_only_exact_target_org_from_active_shortlist() -> None:
    token = b"aaa.bbb.ccc"

    def token_fetcher(url: str, *, timeout: float):
        assert url.endswith("/api/publicToken")
        return token, {}

    def json_fetcher(url: str, *, token: str, if_modified_since=None, timeout: float):
        assert token == "aaa.bbb.ccc"
        if "/feedentry/" not in url:
            return {
                "items": [
                    _feed_item(uuid="u1", business_name="Example AS"),
                    _feed_item(uuid="u2", business_name="Other Company AS"),
                ],
                "next_url": None,
                "next_id": None,
            }, 100
        assert url.endswith("/u1")
        return _detail(uuid="u1", org="900000001"), 200

    report = screen_nav_feed(
        [_profile()],
        now=datetime(2026, 10, 5, tzinfo=timezone.utc),
        max_feed_pages=2,
        max_detail_requests=10,
        token_fetcher=token_fetcher,
        json_fetcher=json_fetcher,
    )

    assert report["reached_feed_end"] is True
    assert report["headers_scanned"] == 2
    assert report["name_shortlisted_events"] == 1
    assert report["detail_requests"] == 1
    assert report["logical_network_requests_including_public_token"] == 3
    assert report["companies_with_exact_active_vacancies"] == 1
    assert report["exact_active_vacancies"] == 1
    assert report["organisation_numbers_with_exact_active_vacancies"] == ["900000001"]
    match = report["exact_matches"][0]
    assert match["identity_method"] == "nav_feed_employer_orgnr_exact_target_v1"
    assert match["employer_orgnr"] == "900000001"
    assert report["public_token_retained"] is False


def test_screen_does_not_promote_name_match_when_nav_org_is_subunit_or_other_org() -> None:
    def token_fetcher(url: str, *, timeout: float):
        return b"aaa.bbb.ccc", {}

    def json_fetcher(url: str, *, token: str, if_modified_since=None, timeout: float):
        if "/feedentry/" not in url:
            return {
                "items": [_feed_item(uuid="u1", business_name="Example AS")],
                "next_url": None,
                "next_id": None,
            }, 100
        return _detail(uuid="u1", org="999999999", employer_name="Example Oslo"), 200

    report = screen_nav_feed(
        [_profile()],
        now=datetime(2026, 10, 5, tzinfo=timezone.utc),
        token_fetcher=token_fetcher,
        json_fetcher=json_fetcher,
    )
    assert report["companies_with_exact_active_vacancies"] == 0
    assert report["exact_matches"] == []
    assert report["nonmatching_name_shortlist_details"][0]["employer_orgnr"] == "999999999"


def test_latest_feed_state_controls_whether_detail_is_fetched() -> None:
    def token_fetcher(url: str, *, timeout: float):
        return b"aaa.bbb.ccc", {}

    detail_called = False

    def json_fetcher(url: str, *, token: str, if_modified_since=None, timeout: float):
        nonlocal detail_called
        if "/feedentry/" in url:
            detail_called = True
            raise AssertionError("inactive latest state must not trigger detail fetch")
        return {
            "items": [
                _feed_item(uuid="u1", business_name="Example AS", status="ACTIVE", modified="2026-09-01T00:00:00Z"),
                _feed_item(uuid="u1", business_name="Example AS", status="INACTIVE", modified="2026-10-01T00:00:00Z"),
            ],
            "next_url": None,
            "next_id": None,
        }, 100

    report = screen_nav_feed(
        [_profile()],
        now=datetime(2026, 10, 5, tzinfo=timezone.utc),
        token_fetcher=token_fetcher,
        json_fetcher=json_fetcher,
    )
    assert detail_called is False
    assert report["latest_name_candidates"] == 1
    assert report["active_name_candidates"] == 0
    assert report["detail_requests"] == 0
