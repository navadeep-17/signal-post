"""No-network adversarial tests for M24 consumed-cohort preflight."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "m24_preflight", ROOT / "scripts" / "check_v10_m24_pilot_gate.py"
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
MANIFEST = json.loads((ROOT / "evaluation" / "v10_m24_consumed_dev_20.json").read_text())


def test_frozen_manifest_and_missing_permission_fail_closed():
    out = module.evaluate(MANIFEST)
    assert out["frozen_development_count"] == 20
    assert out["frozen_selection_sha256"] == module.EXPECTED_LIST_SHA
    assert len(out["missing_or_unattested_items"]) == 8
    assert out["live_provider_authorized"] is False
    assert out["production_promotion_authorized"] is False
    assert out["external_requests_performed"] == 0


def test_synthetic_all_true_attestations_never_authorise_api():
    fake = {
        "evidence": {
            name: {"verified": True, "reference": "synthetic:NOT-LEGAL-PROOF"}
            for name in module.REQUIREMENTS
        }
    }
    out = module.evaluate(MANIFEST, fake)
    assert out["self_reported_requirements_complete"] is True
    assert out["missing_or_unattested_items"] == []
    assert out["provider_permission_independently_verified"] is False
    assert out["real_provider_runtime_measured"] is False
    assert out["run_production_code_request_ceiling_proven"] is False
    assert out["live_provider_authorized"] is False
    assert out["fresh_evaluation_authorized"] is False


def test_partial_attestation_does_not_count_missing_citation():
    fake = {"evidence": {"competition_use": {"verified": True, "reference": ""}}}
    out = module.evaluate(MANIFEST, fake)
    assert "competition_use" in out["missing_or_unattested_items"]


def test_rejects_credentials_even_if_embedded_as_nested_object():
    fake = {"evidence": {"competition_use": {"verified": True, "reference": "memo",
                                           "api_key": "DO_NOT_ACCEPT"}}}
    try:
        module.evaluate(MANIFEST, fake)
    except ValueError as exc:
        assert "credentials" in str(exc)
    else:
        raise AssertionError("Accidentally allowed secrets into attestation")


def test_rejects_tampered_selection_even_when_advertised_digest_unchanged():
    altered = copy.deepcopy(MANIFEST)
    altered["selected_per_cohort"]["m19_a"][0] = "000000000"
    try:
        module.evaluate(altered)
    except ValueError as exc:
        assert "changed" in str(exc)
    else:
        raise AssertionError("Altered frozen entity ID accepted")


def test_rejects_duplicate_company_across_cohorts():
    altered = copy.deepcopy(MANIFEST)
    altered["selected_per_cohort"]["m20_a"][0] = altered["selected_per_cohort"]["m19_a"][0]
    try:
        module.evaluate(altered)
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("Duplicate org accepted")


def test_rejects_fresh_relabel_or_approval_flags():
    for key, value in (
        ("type", "FRESH_HOLDOUT"),
        ("permission_to_merge", True),
        ("live_provider_authorized", True),
        ("qualified_v8_sha", "unqualified"),
    ):
        altered = {**MANIFEST, key: value}
        try:
            module.evaluate(altered)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Unsafe relabel or permission was accepted: {key}")


def test_rejects_numeric_and_non_ascii_org_numbers():
    for bad in (123456789, "①23456789", "12345 789", "12345"):
        altered = copy.deepcopy(MANIFEST)
        altered["selected_per_cohort"]["m19_b"][0] = bad
        try:
            module.evaluate(altered)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Unsafe organisation number was accepted: {bad!r}")


def test_rejects_invalid_attestation_json_shapes():
    for data in (["bad"], {"evidence": ["bad"]}, {"evidence": {"competition_use": True}}):
        if data == {"evidence": {"competition_use": True}}:
            assert "competition_use" in module.evaluate(MANIFEST, data)["missing_or_unattested_items"]
            continue
        try:
            module.evaluate(MANIFEST, data)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid attestation type passed")
