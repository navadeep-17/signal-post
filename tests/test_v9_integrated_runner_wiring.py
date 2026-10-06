from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v8_wrapper_wires_structured_contact_phone_without_request_accounting() -> None:
    source = (ROOT / "scripts" / "run_signalpost_v8.py").read_text(encoding="utf-8")
    assert "from norway_company_agent.company_site_phone import attach_company_site_contact_phone_observations" in source
    assert "from norway_company_agent.external_contract import project_contact_phone_observations" in source
    assert source.count("attach_company_site_contact_phone_observations(profile)") == 1
    assert source.count("project_contact_phone_observations(row, profile)") == 1
    assert '"contact_phone_network_requests": 0' in source
    assert '"structured_contact_phone_projection_zero_network"' in source


def test_pinned_v1_runner_is_not_the_m4_integration_surface() -> None:
    source = (ROOT / "scripts" / "run_signalpost_final.py").read_text(encoding="utf-8")
    assert "attach_company_site_contact_phone_observations" not in source
    assert "project_contact_phone_observations" not in source
