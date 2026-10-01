from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent import annual_report_intelligence as v3
from norway_company_agent.external_footprint import validate_observation


def _profile(org: str = "123456789") -> dict:
    return {
        "organisation_number": org,
        "name": "Example AS",
        "evidence": {
            "registry_live": {
                "status": "available",
                "value": {
                    "organisation_number": org,
                    "latest_submitted_accounts": "2025",
                },
            }
        },
        "external_observations": [],
        "run_metrics": {
            "logical_requests": 5,
            "requests": 10,
            "bytes": 20,
            "latencies_ms": [],
        },
    }


class _Response:
    headers = {"content-type": "application/octet-stream"}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit: int) -> bytes:
        return b"%PDF v3-fixture"


class _Page:
    def __init__(self, text: str):
        self.text = text

    def extract_text(self) -> str:
        return self.text


class _Reader:
    def __init__(self, text: str):
        self.pages = [_Page(text)]


def _report_text(org: str = "123456789", *, workforce: bool = True) -> str:
    workforce_line = "Antall Aarsverk i regnskapsaret 2.00\n" if workforce else ""
    return (
        f"Organisasjonsnummer {org}\n"
        "Arsberetning for regnskapsaret 2025. Denne teksten er lang nok til a unnga OCR i testen.\n"
        "Virksomhetens art\n"
        "Selskapet utvikler og leverer programvare for energibransjen i Norge og Sverige.\n"
        f"{workforce_line}"
        "Fortsatt drift\n"
        "Styret bekrefter forutsetningen om fortsatt drift.\n"
    )


def test_single_report_request_yields_workforce_and_description(monkeypatch) -> None:
    profile = _profile()
    text = _report_text()
    monkeypatch.setattr(v3.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response())
    monkeypatch.setattr(v3, "PdfReader", lambda *_args, **_kwargs: _Reader(text))

    observations, audit = v3.collect_annual_report_intelligence(profile, ocr_pages=0)

    assert audit["request_count"] == 1
    assert audit["status"] == "accepted"
    assert audit["workforce_status"] == "accepted"
    assert audit["description_status"] == "accepted"
    assert len(observations) == 2
    assert {row["signal_type"] for row in observations} == {
        "workforce_snapshot",
        "company_profile",
    }
    assert all(not validate_observation(row) for row in observations)
    assert len({row["content_sha256"] for row in observations}) == 1
    assert len({row["source_url"] for row in observations}) == 1


def test_description_can_survive_when_workforce_phrase_abstains(monkeypatch) -> None:
    profile = _profile()
    text = _report_text(workforce=False)
    monkeypatch.setattr(v3.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response())
    monkeypatch.setattr(v3, "PdfReader", lambda *_args, **_kwargs: _Reader(text))

    observations, audit = v3.collect_annual_report_intelligence(profile, ocr_pages=0)

    assert audit["request_count"] == 1
    assert audit["workforce_status"] == "no_employee_phrase"
    assert audit["description_status"] == "accepted"
    assert len(observations) == 1
    assert observations[0]["signal_type"] == "company_profile"
    assert "programvare" in observations[0]["company_description"]


def test_exact_org_gate_blocks_all_observations(monkeypatch) -> None:
    profile = _profile("123456789")
    text = _report_text("987654321")
    monkeypatch.setattr(v3.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response())
    monkeypatch.setattr(v3, "PdfReader", lambda *_args, **_kwargs: _Reader(text))

    observations, audit = v3.collect_annual_report_intelligence(profile, ocr_pages=0)

    assert observations == []
    assert audit["status"] == "organisation_number_not_in_ocr_text"
    assert audit["workforce_status"] == "not_attempted"
    assert audit["description_status"] == "not_attempted"


def test_batch_reuses_one_request_and_attaches_both_observations(monkeypatch) -> None:
    profiles = [_profile("111111111"), _profile("222222222")]
    monkeypatch.setattr(v3, "ocr_runtime_available", lambda: True)
    monkeypatch.setattr(v3.time, "sleep", lambda *_args: None)

    def fake_collect(profile, **_kwargs):
        org = profile["organisation_number"]
        workforce = {
            "id": f"wf-{org}",
            "organisation_number": org,
            "platform": "brreg",
            "signal_type": "workforce_snapshot",
        }
        description = {
            "id": f"desc-{org}",
            "organisation_number": org,
            "platform": "brreg",
            "signal_type": "company_profile",
            "company_description": "Selskapet leverer tjenester til norske virksomheter.",
        }
        return [workforce, description], {
            "organisation_number": org,
            "status": "accepted",
            "workforce_status": "accepted",
            "description_status": "accepted",
            "request_count": 1,
            "bytes": 100,
            "request_latency_ms": 25,
        }

    monkeypatch.setattr(v3, "collect_annual_report_intelligence", fake_collect)

    report = v3.attach_annual_report_intelligence_batch(
        profiles,
        max_requests=2,
        workers=2,
        min_start_interval=0,
        request_charge_multiplier=2,
    )

    assert report["requests"] == 2
    assert report["accepted"] == 2
    assert report["descriptions_accepted"] == 2
    assert report["observations_accepted"] == 4
    assert report["added_conservative_challenge_request_charge"] == 4
    assert all(len(profile["external_observations"]) == 2 for profile in profiles)
    assert profiles[0]["run_metrics"]["logical_requests"] == 6
    assert profiles[0]["run_metrics"]["requests"] == 12
    assert profiles[0]["run_metrics"]["bytes"] == 120
    assert profiles[0]["run_metrics"]["latencies_ms"] == [25]


def test_batch_keeps_h2g_eligibility_so_description_adds_no_new_request_class(monkeypatch) -> None:
    registry_covered = _profile("111111111")
    registry_covered["evidence"]["registry_live"]["value"]["employees"] = 7
    eligible = _profile("222222222")
    monkeypatch.setattr(v3, "ocr_runtime_available", lambda: True)
    monkeypatch.setattr(v3.time, "sleep", lambda *_args: None)
    monkeypatch.setattr(
        v3,
        "collect_annual_report_intelligence",
        lambda profile, **_kwargs: (
            [],
            {
                "organisation_number": profile["organisation_number"],
                "status": "no_publishable_observation",
                "workforce_status": "no_employee_phrase",
                "description_status": "no_company_activity_section",
                "request_count": 1,
            },
        ),
    )

    report = v3.attach_annual_report_intelligence_batch(
        [registry_covered, eligible],
        max_requests=10,
        workers=1,
        min_start_interval=0,
    )

    assert report["eligible"] == 1
    assert report["selected"] == 1
    assert report["requests"] == 1
    assert not registry_covered["external_observations"]
