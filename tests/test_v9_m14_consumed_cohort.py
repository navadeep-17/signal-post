from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load():
    path = ROOT / "scripts" / "build_v9_m14_consumed_cohort.py"
    spec = importlib.util.spec_from_file_location("m14_builder", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load()


def _profile(org: str, name: str, *, website: str = "", email: str = "") -> dict:
    row = {
        "organisation_number": org,
        "name": name,
        "municipality": "OSLO",
        "website": website,
    }
    if email:
        row["email"] = email
    return row


def test_builder_separates_single_token_treatment_and_multi_token_controls(monkeypatch) -> None:
    monkeypatch.setattr(builder, "select_registry_email_domain_candidate", lambda profile: None)

    profiles = [
        _profile("800000001", "ALPHA AS"),
        _profile("800000002", "BETA ASA"),
        _profile("800000003", "GAMMA DELTA AS"),
        _profile("800000004", "OMEGA SIGMA AS"),
    ]
    manifest, audit, report = builder.build(
        profiles,
        prior_search_orgs=set(),
        treated_count=2,
        control_count=2,
    )
    assert [row["sample_slice"] for row in manifest] == [
        "m14_single_token_compact_com",
        "m14_single_token_compact_com",
        "m14_multi_token_control",
        "m14_multi_token_control",
    ]
    assert [row["organisation_number"] for row in manifest[:2]] == ["800000001", "800000002"]
    assert report["treated_companies"] == 2
    assert report["control_companies"] == 2
    assert all(not row["builderr_public_practice"] for row in audit)


def test_builder_excludes_public_practice_and_prior_research(monkeypatch) -> None:
    monkeypatch.setattr(builder, "select_registry_email_domain_candidate", lambda profile: None)

    prior = {"800000010"}
    profiles = [
        _profile("811413682", "ELOPAK ASA"),
        _profile("800000010", "PRIOR AS"),
        _profile("828829092", "EMILSEN AS"),
        _profile("927097532", "CANARY AS"),
        _profile("800000020", "CLEAN AS"),
        _profile("800000021", "OTHER AS"),
        _profile("800000030", "CONTROL ONE AS"),
    ]
    manifest, audit, _ = builder.build(
        profiles,
        prior_search_orgs=prior,
        treated_count=2,
        control_count=1,
    )
    selected = {row["organisation_number"] for row in manifest}
    assert "811413682" not in selected
    assert "800000010" not in selected
    assert "828829092" not in selected
    assert "927097532" not in selected
    assert selected == {"800000020", "800000021", "800000030"}
    assert not any(
        row["previous_search_development"]
        or row["m10_positive_canary"]
        or row["m12_researched"]
        or row["builderr_public_practice"]
        for row in audit
    )


def test_registry_website_and_email_candidate_are_not_treated(monkeypatch) -> None:
    def email_candidate(profile):
        if profile["organisation_number"] == "800000002":
            return {"domain": "maildomain.no", "url": "https://maildomain.no/"}
        return None

    monkeypatch.setattr(builder, "select_registry_email_domain_candidate", email_candidate)
    profiles = [
        _profile("800000001", "WEBSITE AS", website="https://website.no/"),
        _profile("800000002", "EMAIL AS"),
        _profile("800000003", "CLEAN AS"),
        _profile("800000004", "CONTROL ONE AS"),
    ]
    manifest, _, report = builder.build(
        profiles,
        prior_search_orgs=set(),
        treated_count=1,
        control_count=1,
    )
    assert [row["organisation_number"] for row in manifest] == ["800000003", "800000004"]
    assert report["eligible_treated_population"] == 1


def test_insufficient_treatment_pool_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(builder, "select_registry_email_domain_candidate", lambda profile: None)
    try:
        builder.build(
            [_profile("800000001", "ALPHA AS"), _profile("800000002", "CONTROL ONE AS")],
            prior_search_orgs=set(),
            treated_count=2,
            control_count=1,
        )
    except ValueError as exc:
        assert "single-token H1h candidates" in str(exc)
    else:
        raise AssertionError("insufficient treatment pool must fail")
