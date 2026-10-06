from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gate_zero_network_enrichment_bundle.py"
spec = importlib.util.spec_from_file_location("gate_zero_network_enrichment_bundle", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_managed_fields_are_narrow() -> None:
    assert module.MANAGED_FIELDS == {
        "social_links",
        "external.profile_handle",
        "external.contact_email",
    }


def test_claim_sig_is_deterministic() -> None:
    left = {"field": "x", "value": {"b": 2, "a": 1}}
    right = {"value": {"a": 1, "b": 2}, "field": "x"}
    assert module._claim_sig(left) == module._claim_sig(right)


def test_available_claims_filters_unavailable() -> None:
    contract = {
        "claims": [
            {"field": "external.contact_email", "availability": "available", "value": "x@y.no"},
            {"field": "external.contact_email", "availability": "unavailable", "value": None},
            {"field": "external.profile_handle", "availability": "available", "value": "https://x"},
        ]
    }
    rows = module._available_claims(contract, "external.contact_email")
    assert len(rows) == 1
    assert rows[0]["value"] == "x@y.no"
