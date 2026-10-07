from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load():
    path = ROOT / "scripts" / "build_v9_m13_consumed_search_cohort.py"
    spec = importlib.util.spec_from_file_location("m13_builder", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load()


def _profile(org: str, *, name: str | None = None, website: str = "") -> dict:
    return {
        "organisation_number": org,
        "name": name or f"COMPANY {org} AS",
        "municipality": "OSLO",
        "website": website,
    }


def test_builder_excludes_all_researched_sets_and_pre_registers_targets() -> None:
    prior = {f"{700000000+i:09d}" for i in range(20)}
    profiles = [_profile(org) for org in sorted(prior)]
    profiles += [_profile(org) for org in sorted(builder.M10_POSITIVE_CANARIES)]
    profiles += [_profile(org) for org in sorted(builder.M12_RESEARCHED_ORGS)]
    profiles += [_profile(f"{800000000+i:09d}") for i in range(12)]

    manifest, audit, report = builder.build(
        profiles,
        prior_search_orgs=prior,
        target_count=10,
        search_count=3,
    )
    selected = {row["organisation_number"] for row in manifest}
    assert not selected & prior
    assert not selected & builder.M10_POSITIVE_CANARIES
    assert not selected & builder.M12_RESEARCHED_ORGS
    assert [row["sample_slice"] for row in manifest[:3]] == ["m13_search_holdout"] * 3
    assert [row["sample_slice"] for row in manifest[3:]] == ["m13_control_unsearched"] * 7
    assert report["search_holdout_companies"] == 3
    assert report["control_companies"] == 7
    assert report["fresh_companies_used"] == 0
    assert all(
        not row["previous_search_development"]
        and not row["m10_positive_canary"]
        and not row["m12_researched"]
        for row in audit
    )


def test_registry_website_or_missing_h1g_slot_cannot_enter_search_population() -> None:
    prior: set[str] = set()
    profiles = [
        _profile("800000001", website="https://already.no/"),
        _profile("800000002", name="SINGLETOKEN AS"),
        _profile("800000003", name="ALPHA BETA AS"),
        _profile("800000004", name="GAMMA DELTA AS"),
    ]
    manifest, _, report = builder.build(
        profiles,
        prior_search_orgs=prior,
        target_count=2,
        search_count=1,
    )
    orgs = [row["organisation_number"] for row in manifest]
    assert "800000001" not in orgs
    assert "800000002" not in orgs
    assert report["eligible_unresearched_population"] == 2


def test_insufficient_clean_consumed_population_fails_closed() -> None:
    try:
        builder.build(
            [_profile("800000001", name="ALPHA BETA AS")],
            prior_search_orgs=set(),
            target_count=2,
            search_count=1,
        )
    except ValueError as exc:
        assert "clean consumed H1g-eligible companies" in str(exc)
    else:
        raise AssertionError("insufficient holdout/control population must fail")
