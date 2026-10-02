from datetime import datetime, timezone

from norway_company_agent.nav_exact_jobs import (
    build_target_index,
    extract_exact_active_job,
    nominate_targets,
    normalize_name,
)


def profiles():
    return [
        {
            "organisation_number": "123456789",
            "name": "FJORD DATA SERVICE AS",
            "evidence": {
                "locations": {
                    "status": "available",
                    "value": {
                        "locations": [
                            {
                                "organisation_number": "987654321",
                                "name": "FJORD DATA SERVICE AS AVD OSLO",
                                "address": {"kommune": "OSLO"},
                            }
                        ]
                    },
                }
            },
        },
        {
            "organisation_number": "111222333",
            "name": "NORDLYS TEKNOLOGI AS",
            "evidence": {"locations": {"status": "available", "value": {"locations": []}}},
        },
    ]


def test_target_index_reuses_retained_brreg_subunits_without_network():
    index = build_target_index(profiles())
    assert index["org_to_target"]["123456789"] == "123456789"
    assert index["org_to_target"]["987654321"] == "123456789"
    assert "FJORD DATA SERVICE AVD OSLO" in index["name_to_targets"]


def test_nomination_can_be_broad_but_is_not_acceptance():
    index = build_target_index(profiles())
    assert nominate_targets("Fjord Data Service", index) == ["123456789"]
    assert nominate_targets("Fjord Data Service Norway", index) == ["123456789"]
    assert nominate_targets("Data", index) == []


def test_exact_main_org_accepts_current_job():
    index = build_target_index(profiles())
    detail = {
        "status": "ACTIVE",
        "ad_content": {
            "uuid": "job-1",
            "title": "Senior Software Engineer",
            "published": "2026-09-25T10:00:00Z",
            "expires": "2026-11-01T23:59:59Z",
            "employer": {"name": "Fjord Data Service AS", "orgnr": "123456789"},
            "workLocations": [{"city": "Oslo", "municipal": "OSLO"}],
            "engagementtype": "FAST",
        },
    }
    job = extract_exact_active_job(
        detail,
        index,
        nominated_targets=["123456789"],
        now=datetime(2026, 10, 2, tzinfo=timezone.utc),
    )
    assert job is not None
    assert job["target_org"] == "123456789"
    assert job["employer_org"] == "123456789"
    assert job["identity"].startswith("exact_nav_employer")


def test_exact_retained_subunit_org_maps_to_parent_target():
    index = build_target_index(profiles())
    detail = {
        "status": "ACTIVE",
        "ad_content": {
            "uuid": "job-2",
            "title": "Support Engineer",
            "expires": "2026-12-01T00:00:00Z",
            "employer": {"name": "Fjord Data Service AS avd Oslo", "orgnr": "987654321"},
        },
    }
    job = extract_exact_active_job(detail, index, nominated_targets=["123456789"], now=datetime(2026, 10, 2, tzinfo=timezone.utc))
    assert job is not None
    assert job["target_org"] == "123456789"
    assert job["employer_org"] == "987654321"


def test_same_name_wrong_org_is_rejected():
    index = build_target_index(profiles())
    detail = {
        "status": "ACTIVE",
        "ad_content": {
            "title": "Senior Software Engineer",
            "expires": "2026-11-01T00:00:00Z",
            "employer": {"name": "Fjord Data Service AS", "orgnr": "555666777"},
        },
    }
    assert extract_exact_active_job(detail, index, nominated_targets=["123456789"], now=datetime(2026, 10, 2, tzinfo=timezone.utc)) is None


def test_inactive_or_expired_job_is_rejected():
    index = build_target_index(profiles())
    inactive = {
        "status": "INACTIVE",
        "ad_content": {"title": "Engineer", "employer": {"orgnr": "123456789"}},
    }
    assert extract_exact_active_job(inactive, index, nominated_targets=["123456789"], now=datetime(2026, 10, 2, tzinfo=timezone.utc)) is None

    expired = {
        "status": "ACTIVE",
        "ad_content": {
            "title": "Engineer",
            "expires": "2026-09-01T00:00:00Z",
            "employer": {"orgnr": "123456789"},
        },
    }
    assert extract_exact_active_job(expired, index, nominated_targets=["123456789"], now=datetime(2026, 10, 2, tzinfo=timezone.utc)) is None


def test_normalized_name_removes_only_legal_suffixes():
    assert normalize_name("Fjord Data Service AS") == "FJORD DATA SERVICE"
    assert normalize_name("ASIA SYSTEMS AS") == "ASIA SYSTEMS"
