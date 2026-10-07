from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent import h1h_single_token_compact_com as h1h  # noqa: E402


def _profile(*, name: str = "ELOPAK ASA") -> dict:
    return {
        "organisation_number": "811413682",
        "name": name,
        "municipality": "SPIKKESTAD",
        "website": "",
        "evidence": {
            "website": {"status": "not_found"},
            "registry": {
                "status": "available",
                "value": {"forretningsadresse.kommune": "SPIKKESTAD"},
            },
        },
    }


def test_single_token_candidate_is_compact_com() -> None:
    c = h1h.single_token_compact_com_candidate(_profile())
    assert c == {
        "domain": "elopak.com",
        "url": "https://elopak.com/",
        "strategy": "single_token_legal_name_compact_com",
    }


def test_multi_token_name_has_no_h1h_candidate() -> None:
    assert h1h.single_token_compact_com_candidate(
        _profile(name="ALPINE DESIGN AS")
    ) is None


def test_h1h_never_runs_when_final_site_slot_is_consumed(monkeypatch) -> None:
    calls = {"fetch": 0}

    def fetch(*args, **kwargs):
        calls["fetch"] += 1
        raise AssertionError("fetch must not run when site slot is consumed")

    monkeypatch.setattr(h1h, "fetch_bounded_homepage", fetch)
    _, result = h1h.evaluate_single_token_compact_com_fallback(
        _profile(),
        base_site_logical_requests=4,
    )
    assert calls["fetch"] == 0
    assert result["attempted"] is False
    assert result["skipped_reason"] == "site_request_budget_consumed"


def test_exact_org_candidate_can_publish_inside_idle_two_request_slot(monkeypatch) -> None:
    def fetch(url, *, source_type, timeout):
        assert url == "https://elopak.com/"
        assert source_type == "deterministic_single_token_compact_com_fallback"
        return (
            {
                "status": "available",
                "source_url": url,
                "source_type": source_type,
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": url,
                    "registered_domain": "elopak.com",
                    "content_sha256": "a" * 64,
                    "title": "Elopak ASA",
                    "identity_text_excerpt": "Organisasjonsnummer 811 413 682",
                    "main_text_excerpt": "Elopak ASA",
                    "structured_organisations": [],
                    "pages": [],
                },
            },
            {"requests": 2, "bytes": 100, "latencies_ms": [1]},
        )

    monkeypatch.setattr(h1h, "fetch_bounded_homepage", fetch)
    monkeypatch.setattr(
        h1h,
        "apply_website_identity_gate",
        lambda profile, website: {
            "website": website,
            "assessment": {
                "status": "exact",
                "score": 1.0,
                "publishable": True,
                "method": "fixture_identity",
                "reasons": [],
            },
        },
    )
    monkeypatch.setattr(h1h, "_page_contains_org_number", lambda profile, website: True)
    monkeypatch.setattr(h1h, "_has_conflicting_explicit_org_number", lambda profile, website: False)
    monkeypatch.setattr(h1h, "apply_registry_risk_guard", lambda profile: (profile, []))

    row, result = h1h.evaluate_single_token_compact_com_fallback(
        _profile(),
        base_site_logical_requests=2,
    )
    assert result["attempted"] is True
    assert result["requests_added"] == 2
    assert result["post_site_logical_requests"] == 4
    assert result["verified"] is True
    assert result["selected_url"] == "https://elopak.com/"
    assert row["website"] == "https://elopak.com/"
    proof = row["evidence"]["website"]["value"]["identity_assessment"]
    assert proof["method"] == "h1h_single_token_compact_com_identity_v1"
    assert proof["publishable"] is True


def test_conflicting_org_number_forces_abstention(monkeypatch) -> None:
    website = {
        "status": "available",
        "source_url": "https://elopak.com/",
        "value": {},
    }
    assessment = {
        "status": "exact",
        "score": 1.0,
        "publishable": True,
        "method": "fixture",
        "reasons": [],
    }
    monkeypatch.setattr(h1h, "_has_conflicting_explicit_org_number", lambda profile, website: True)
    q = h1h.qualify_single_token_compact_com_identity(_profile(), website, assessment)
    assert q is not None
    assert q["publishable"] is False
    assert q["status"] == "review"


def test_name_only_without_location_never_authorizes_single_token_com(monkeypatch) -> None:
    website = {
        "status": "available",
        "source_url": "https://elopak.com/",
        "value": {},
    }
    assessment = {
        "status": "exact",
        "score": 0.95,
        "publishable": True,
        "method": "fixture",
        "reasons": [],
    }
    monkeypatch.setattr(h1h, "_has_conflicting_explicit_org_number", lambda profile, website: False)
    monkeypatch.setattr(h1h, "_page_contains_org_number", lambda profile, website: False)
    monkeypatch.setattr(h1h, "_page_contains_full_legal_name", lambda profile, website: True)
    monkeypatch.setattr(h1h, "_page_matches_registry_location", lambda profile, website: False)
    q = h1h.qualify_single_token_compact_com_identity(_profile(), website, assessment)
    assert q is not None
    assert q["publishable"] is False
    assert q["status"] == "review"
