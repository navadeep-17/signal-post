from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_v3_annual_report_descriptions",
    ROOT / "scripts" / "audit_v3_annual_report_descriptions.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _description_observation(org: str = "123456789") -> dict:
    return {
        "id": "annual-description-1",
        "organisation_number": org,
        "platform": "brreg",
        "signal_type": "company_profile",
        "source_class": "official_annual_account_copy",
        "source_url": f"https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/{org}/2025",
        "retrieved_at": "2026-10-01T00:00:00Z",
        "content_sha256": "a" * 64,
        "evidence_span": "Selskapet utvikler programvare for energibransjen.",
        "company_description": "Selskapet utvikler programvare for energibransjen.",
    }


def _workforce_observation(org: str = "123456789") -> dict:
    return {
        "id": "annual-workforce-1",
        "organisation_number": org,
        "platform": "brreg",
        "signal_type": "workforce_snapshot",
        "source_class": "official_annual_account_copy",
        "source_url": f"https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/{org}/2025",
        "content_sha256": "a" * 64,
    }


def test_audit_detects_shared_report_and_complete_publication() -> None:
    org = "123456789"
    profiles = [
        {
            "organisation_number": org,
            "external_observations": [_description_observation(org), _workforce_observation(org)],
        }
    ]
    outputs = [
        {
            "organisation_number": org,
            "claims": [
                {
                    "field": "company_description",
                    "availability": "available",
                    "platform": "brreg",
                    "signal_type": "company_profile",
                    "evidence_ids": ["ev-description"],
                }
            ],
            "evidence": [
                {
                    "id": "ev-description",
                    "source_url": _description_observation(org)["source_url"],
                    "retrieved_at": "2026-10-01T00:00:00Z",
                    "content_sha256": "a" * 64,
                    "claim_span": "Selskapet utvikler programvare for energibransjen.",
                }
            ],
        }
    ]

    report = MODULE.audit(profiles, outputs)

    assert report["passed"] is True
    assert report["companies_with_annual_description_observation"] == 1
    assert report["published_annual_description_claims"] == 1
    assert report["companies_reusing_same_report_as_workforce"] == 1
    assert report["companies_suppressed_by_stronger_existing_description"] == 0


def test_audit_counts_precedence_suppression() -> None:
    profiles = [{"organisation_number": "123456789", "external_observations": [_description_observation()]}]
    outputs = [
        {
            "organisation_number": "123456789",
            "claims": [
                {
                    "field": "company_description",
                    "availability": "available",
                    "value": "Company-owned description wins.",
                    "evidence_ids": ["ev-site"],
                }
            ],
            "evidence": [
                {
                    "id": "ev-site",
                    "source_url": "https://example.no/",
                    "retrieved_at": "2026-10-01T00:00:00Z",
                    "content_sha256": "b" * 64,
                    "claim_span": "Company-owned description wins.",
                }
            ],
        }
    ]

    report = MODULE.audit(profiles, outputs)

    assert report["passed"] is True
    assert report["published_annual_description_claims"] == 0
    assert report["companies_suppressed_by_stronger_existing_description"] == 1


def test_audit_fails_orphan_publication() -> None:
    outputs = [
        {
            "organisation_number": "123456789",
            "claims": [
                {
                    "field": "company_description",
                    "availability": "available",
                    "platform": "brreg",
                    "signal_type": "company_profile",
                    "evidence_ids": ["ev-description"],
                }
            ],
            "evidence": [
                {
                    "id": "ev-description",
                    "source_url": "https://example.invalid/report",
                    "retrieved_at": "2026-10-01T00:00:00Z",
                    "content_sha256": "a" * 64,
                    "claim_span": "Description",
                }
            ],
        }
    ]

    report = MODULE.audit([], outputs)

    assert report["passed"] is False
    assert report["orphan_published_organisation_numbers"] == ["123456789"]
