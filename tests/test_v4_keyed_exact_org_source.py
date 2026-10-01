from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_keyed_exact_org_source.py"
spec = importlib.util.spec_from_file_location("screen_keyed_exact_org_source", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_analyse_payload_matches_compact_and_grouped_exact_org() -> None:
    compact = module.analyse_payload(b'{"organisationNumber":"123456789"}', "123456789")
    grouped = module.analyse_payload(b'<id>123 456 789</id>', "123456789")

    assert compact["matched"] is True
    assert compact["exact_org_occurrences"] == 1
    assert grouped["matched"] is True
    assert grouped["exact_org_occurrences"] == 1


def test_analyse_payload_rejects_numeric_substring_collision() -> None:
    result = module.analyse_payload(b'{"id":"01234567890"}', "123456789")

    assert result["matched"] is False
    assert result["exact_org_occurrences"] == 0


def test_build_request_keeps_secret_only_in_header() -> None:
    request = module.build_request(
        "https://example.test/company/{organisation_number}",
        "123456789",
        api_key="super-secret-key",
        api_key_header="Ocp-Apim-Subscription-Key",
        accept="application/json",
    )

    assert request.full_url == "https://example.test/company/123456789"
    assert "super-secret-key" not in request.full_url
    assert request.get_header("Ocp-apim-subscription-key") == "super-secret-key"
    assert request.get_header("Accept") == "application/json"


def test_build_request_requires_exact_org_placeholder_and_https() -> None:
    with pytest.raises(ValueError, match="organisation_number"):
        module.build_request(
            "https://example.test/company",
            "123456789",
            api_key="key",
            api_key_header="X-Key",
            accept="application/json",
        )

    with pytest.raises(ValueError, match="https"):
        module.build_request(
            "http://example.test/company/{organisation_number}",
            "123456789",
            api_key="key",
            api_key_header="X-Key",
            accept="application/json",
        )
