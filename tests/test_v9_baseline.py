from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_v9_baseline",
    ROOT / "scripts" / "build_v9_baseline.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _row(org: str, fields: list[str]) -> dict:
    return {
        "organisation_number": org,
        "claims": [
            {
                "field": field,
                "value": f"value-{field}",
                "availability": "available",
                "evidence_ids": [f"ev-{field}"],
            }
            for field in fields
        ],
    }


def test_family_metrics_count_companies_not_raw_claims() -> None:
    rows = [
        _row(
            "111111111",
            [
                "official_website",
                "external.profile_handle",
                "external.contact_email",
                "external.company_update",
            ],
        ),
        _row("222222222", ["official_website", "external.profile_handle"]),
        _row("333333333", []),
    ]

    metrics = MODULE._family_metrics(rows)

    assert metrics["companies"] == 3
    assert metrics["verified_website_companies"] == 2
    assert metrics["social_profile_companies"] == 2
    assert metrics["contact_email_companies"] == 1
    assert metrics["careers_surface_companies"] == 0
    assert metrics["specific_job_companies"] == 0
    assert metrics["dated_activity_companies"] == 1
    assert metrics["website_resolution_states"]["available"] == 2
    assert metrics["website_resolution_states"]["missing_claim"] == 1


def test_unavailable_website_is_not_counted_as_verified() -> None:
    row = {
        "organisation_number": "111111111",
        "claims": [
            {
                "field": "official_website",
                "value": None,
                "availability": "ambiguous",
                "evidence_ids": ["ev-site"],
            }
        ],
    }

    metrics = MODULE._family_metrics([row])

    assert metrics["verified_website_companies"] == 0
    assert metrics["website_resolution_states"]["ambiguous"] == 1


def test_stable_rank_is_deterministic_and_seeded() -> None:
    first = MODULE._stable_rank("seed-a", "123456789")
    second = MODULE._stable_rank("seed-a", "123456789")
    different = MODULE._stable_rank("seed-b", "123456789")

    assert first == second
    assert first != different
    assert len(first) == 64
