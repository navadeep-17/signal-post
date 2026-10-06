from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_phone import (
    PHONE_STRATEGY,
    attach_company_site_contact_phone_observations,
    company_site_contact_phone_observations,
    normalize_norwegian_contact_phone,
)
from norway_company_agent.external_footprint import validate_observation


ORG = "912345678"


def _profile(node: dict) -> dict:
    return {
        "organisation_number": ORG,
        "name": "Example AS",
        "external_observations": [],
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no/",
                "retrieved_at": "2026-10-01T10:00:00Z",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": "https://example.no/",
                    "content_sha256": "a" * 64,
                    "identity_assessment": {
                        "status": "exact",
                        "score": 1.0,
                        "publishable": True,
                        "method": "test",
                    },
                    "structured_organisations": [node],
                },
            }
        },
    }


def test_normalizes_conservative_norwegian_numbers() -> None:
    assert normalize_norwegian_contact_phone("+47 98 76 54 32") == "+4798765432"
    assert normalize_norwegian_contact_phone("0047 22 33 44 55") == "+4722334455"
    assert normalize_norwegian_contact_phone("98765432") == "+4798765432"
    assert normalize_norwegian_contact_phone("+46 98765432") is None
    assert normalize_norwegian_contact_phone("12345678") is None


def test_named_node_recovers_contactpoint_phone() -> None:
    observations = company_site_contact_phone_observations(
        _profile(
            {
                "@type": "Organization",
                "name": "Example AS",
                "contactPoint": {"@type": "ContactPoint", "telephone": "+47 98 76 54 32"},
            }
        )
    )
    assert len(observations) == 1
    assert observations[0]["contact_phone"] == "+4798765432"
    assert observations[0]["strategy"] == PHONE_STRATEGY
    assert validate_observation(observations[0]) == []


def test_exact_org_identifier_recovers_phone() -> None:
    observations = company_site_contact_phone_observations(
        _profile(
            {
                "@type": "Organization",
                "name": "Brand",
                "identifier": {"value": ORG},
                "telephone": "22334455",
            }
        )
    )
    assert len(observations) == 1
    gate = next(
        item for item in observations[0]["identity_proof"]
        if item["type"] == "structured_organization_identity_gate"
    )
    assert gate["method"] == "structured_exact_organisation_number"


def test_explicit_wrong_org_vetoes_phone() -> None:
    observations = company_site_contact_phone_observations(
        _profile(
            {
                "@type": "Organization",
                "name": "Example AS",
                "taxID": "987654321",
                "telephone": "98765432",
            }
        )
    )
    assert observations == []


def test_free_text_phone_is_not_scanned() -> None:
    observations = company_site_contact_phone_observations(
        _profile(
            {
                "@type": "Organization",
                "name": "Example AS",
                "description": "Call 98765432",
            }
        )
    )
    assert observations == []


def test_attachment_is_idempotent() -> None:
    profile = _profile({"@type": "Organization", "name": "Example AS", "telephone": "98765432"})
    profile["external_observations"] = [
        {
            "id": "existing",
            "organisation_number": ORG,
            "platform": "instagram",
            "signal_type": "profile_handle",
        }
    ]
    first = attach_company_site_contact_phone_observations(profile)
    second = attach_company_site_contact_phone_observations(deepcopy(first))
    assert [x["id"] for x in first["external_observations"]] == [
        x["id"] for x in second["external_observations"]
    ]
