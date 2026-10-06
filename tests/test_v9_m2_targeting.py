from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_m2_targeting import (  # noqa: E402
    build_targeted_m2_cohort,
    classify_m2_candidate_slot,
)


def profile(org: str, name: str, email: str = "", website: str = "") -> dict:
    return {
        "organisation_number": org,
        "name": name,
        "website": website,
        "evidence": {
            "registry": {
                "status": "available",
                "value": {"epostadresse": email},
            }
        },
    }


def test_classify_weak_email_candidate_as_m2_delta() -> None:
    item = classify_m2_candidate_slot(
        profile("111111111", "ACME NORD AS", "post@accountingpartner.no")
    )
    assert item["bucket"] == "m2_delta"
    assert item["baseline_candidate_domain"] == "accountingpartner.no"
    assert item["challenger_candidate_domain"] is None


def test_classify_strong_email_candidate_as_control() -> None:
    item = classify_m2_candidate_slot(
        profile("111111111", "ACME NORD AS", "post@acmenord.no")
    )
    assert item["bucket"] == "strong_email_control"
    assert item["baseline_candidate_domain"] == "acmenord.no"
    assert item["challenger_candidate_domain"] == "acmenord.no"


def test_registry_website_never_enters_target_population() -> None:
    profiles = [
        profile("111111111", "ACME NORD AS", "post@accountingpartner.no", "https://acme.no/"),
        profile("222222222", "BETA AS", "post@beta.no"),
        profile("333333333", "GAMMA AS"),
    ]
    orgs, audit, report = build_targeted_m2_cohort(profiles, target_count=2)
    assert "111111111" not in orgs
    assert len(audit) == 2
    assert report["selected_companies"] == 2


def test_targeting_includes_all_delta_before_controls() -> None:
    profiles = [
        profile("111111111", "ACME NORD AS", "post@accountingpartner.no"),
        profile("222222222", "BETA AS", "post@beta.no"),
        profile("333333333", "GAMMA AS"),
        profile("444444444", "DELTA AS"),
    ]
    orgs, audit, report = build_targeted_m2_cohort(profiles, target_count=3)
    assert orgs[0] == "111111111"
    assert report["selected_bucket_counts"]["m2_delta"] == 1
    assert report["selected_bucket_counts"]["strong_email_control"] == 1
    assert report["selected_bucket_counts"]["no_email_control"] == 1
    assert [row["bucket"] for row in audit] == [
        "m2_delta",
        "strong_email_control",
        "no_email_control",
    ]


def test_never_silently_drops_delta_population() -> None:
    profiles = [
        profile("111111111", "ACME AS", "post@partner.no"),
        profile("222222222", "BETA AS", "post@partner.no"),
    ]
    try:
        build_targeted_m2_cohort(profiles, target_count=1)
    except ValueError as exc:
        assert "do not silently drop" in str(exc)
    else:
        raise AssertionError("expected ValueError")
