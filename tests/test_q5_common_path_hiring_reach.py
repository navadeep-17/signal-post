from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from screen_q5_common_path_hiring_reach import (  # noqa: E402
    _surface_signal,
    candidate_urls,
    screen_profiles,
)


def _profile(org: str = "900000001") -> dict:
    return {
        "organisation_number": org,
        "name": "EXAMPLE AS",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no/",
                "value": {
                    "final_url": "https://example.no/",
                    "identity_assessment": {"publishable": True},
                },
            }
        },
    }


def _record(final_url: str, text: str = "", *, jobs: list[dict] | None = None) -> dict:
    return {
        "status": "available",
        "source_url": final_url,
        "content_sha256": "a" * 64,
        "value": {
            "final_url": final_url,
            "title": text,
            "description": "",
            "identity_text_excerpt": "",
            "main_text_excerpt": text,
            "job_listing_candidates": jobs or [],
            "active_hiring_signal": {"active_vacancy_count": 0},
        },
    }


def test_candidate_urls_are_same_origin_and_deterministic() -> None:
    rows = candidate_urls("https://www.example.no/about")
    assert rows == [
        ("karriere", "https://www.example.no/karriere/"),
        ("jobb", "https://www.example.no/jobb/"),
        ("ledige-stillinger", "https://www.example.no/ledige-stillinger/"),
        ("careers", "https://www.example.no/careers/"),
        ("jobs", "https://www.example.no/jobs/"),
    ]


def test_surface_requires_strong_hiring_evidence_and_rejects_homepage_redirect() -> None:
    qualified = _surface_signal(
        _record("https://example.no/karriere/", "Karriere - jobb hos oss"),
        "https://example.no/",
    )
    assert qualified["qualified"] is True
    assert "karriere" in qualified["markers"]

    generic = _surface_signal(
        _record("https://example.no/jobb/", "Vi leverer rådgivning og tjenester"),
        "https://example.no/",
    )
    assert generic["qualified"] is False
    assert generic["reason"] == "no_strong_hiring_evidence"

    redirected = _surface_signal(
        _record("https://example.no/", "Karriere"),
        "https://example.no/",
    )
    assert redirected == {"qualified": False, "reason": "redirected_to_verified_homepage"}


def test_surface_accepts_existing_job_candidate_without_keyword() -> None:
    result = _surface_signal(
        _record(
            "https://example.no/jobs/",
            "Muligheter",
            jobs=[{"title": "Senior Engineer", "role_url": "https://example.no/jobs/senior-engineer"}],
        ),
        "https://example.no/",
    )
    assert result["qualified"] is True
    assert result["job_listing_candidates"] == 1


def test_screen_counts_path_yield_and_network_without_publishing() -> None:
    def fake_fetch(url: str, *, source_type: str, timeout: float):
        assert source_type == "q5_common_path_hiring_screen"
        assert timeout == 3.0
        if url.endswith("/karriere/"):
            return _record(url, "Karriere - jobb hos oss"), {"requests": 2, "bytes": 100}
        return {"status": "not_found", "source_url": url}, {"requests": 2, "bytes": 0}

    report = screen_profiles([_profile()], timeout=3.0, fetcher=fake_fetch)
    assert report["fresh_qualification"] is False
    assert report["verified_sites"] == 1
    assert report["network_requests"] == 10
    assert report["qualified_companies_any_path"] == 1
    assert report["path_results"]["karriere"]["qualified_companies"] == 1
    assert report["ranked_paths"][0] == "karriere"
    assert report["production_decision"] == "UNDECIDED_SCREEN_ONLY"
