from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_final_runner_wires_structured_contact_phone_without_request_accounting() -> None:
    source = (ROOT / "scripts" / "run_signalpost_final.py").read_text(encoding="utf-8")
    assert "from norway_company_agent.company_site_phone import attach_company_site_contact_phone_observations" in source
    assert "project_contact_phone_observations," in source
    assert source.count("attach_company_site_contact_phone_observations(profile)") == 1
    assert source.count('project_contact_phone_observations(contract, envelope["profile"])') == 1
    assert '"contact_phone_network_requests": 0' in source
    attach_position = source.index("attach_company_site_contact_phone_observations(profile)")
    accounting_position = source.index("logical_requests = official_logical_requests + site_logical_requests")
    assert attach_position < accounting_position
