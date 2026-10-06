from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_retained_structured_phone_recovery.py"
spec = importlib.util.spec_from_file_location("audit_retained_structured_phone_recovery", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def profile(node: dict) -> dict:
    return {
        "organisation_number": "123456789",
        "name": "Example AS",
        "evidence": {
            "website": {
                "status": "available",
                "value": {
                    "identity_assessment": {"publishable": True},
                    "structured_organisations": [node],
                },
            }
        },
    }


def test_normalizes_only_conservative_norwegian_telephone_shapes() -> None:
    assert module._normalize_norwegian_phone("+47 22 33 44 55") == "22334455"
    assert module._normalize_norwegian_phone("0047 987 65 432") == "98765432"
    assert module._normalize_norwegian_phone("47 987 65 432") == "98765432"
    assert module._normalize_norwegian_phone("98765432") == "98765432"
    assert module._normalize_norwegian_phone("+46 98765432") is None
    assert module._normalize_norwegian_phone("12345678") is None
    assert module._normalize_norwegian_phone("98765432 ext 4") is None


def test_extracts_only_explicit_telephone_fields() -> None:
    node = {
        "name": "Example AS",
        "description": "Call 98765432",
        "contactPoint": {"telephone": "+47 98 76 54 32"},
    }
    assert module._structured_telephone_values(node) == {"98765432"}


def test_matching_named_node_can_supply_phone_candidate() -> None:
    node = {
        "@type": "Organization",
        "name": "Example AS",
        "contactPoint": {"@type": "ContactPoint", "telephone": "+47 98 76 54 32"},
    }
    report, rows = module.audit([profile(node)], {"123456789": {"claims": []}})
    assert report["structured_phone_candidate_companies"] == 1
    assert report["net_new_contact_phone_companies"] == 1
    assert rows[0]["structured_identity_methods"] == ["structured_legal_name_token_match"]


def test_explicit_wrong_org_vetoes_phone_even_with_matching_name() -> None:
    node = {
        "@type": "Organization",
        "name": "Example AS",
        "taxID": "987654321",
        "telephone": "98765432",
    }
    report, rows = module.audit([profile(node)], {"123456789": {"claims": []}})
    assert report["structured_phone_candidate_companies"] == 0
    assert rows == []


def test_telephone_never_becomes_org_identity() -> None:
    p = profile({
        "@type": "Organization",
        "name": "Other Company AS",
        "telephone": "123456789",
    })
    report, rows = module.audit([p], {"123456789": {"claims": []}})
    assert report["companies_with_matching_structured_organization_node"] == 0
    assert report["structured_phone_candidate_companies"] == 0
    assert rows == []


def test_registered_phone_makes_candidate_overlap_not_net_new() -> None:
    node = {
        "@type": "Organization",
        "identifier": {"value": "123 456 789"},
        "telephone": "98765432",
    }
    output = {
        "123456789": {
            "claims": [
                {"field": "registered_phone", "availability": "available", "value": "22334455"}
            ]
        }
    }
    report, rows = module.audit([profile(node)], output)
    assert report["structured_phone_candidate_companies"] == 1
    assert report["structured_phone_overlap_registered_contact"] == 1
    assert report["net_new_contact_phone_companies"] == 0
    assert rows[0]["already_has_registered_phone_or_mobile"] is True
