from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent import annual_report_workforce as h2g
from norway_company_agent.external_footprint import validate_observation


def _profile(org: str, *, year: str = "2025", employees=None) -> dict:
    value = {
        "organisation_number": org,
        "latest_submitted_accounts": year,
    }
    if employees is not None:
        value["employees"] = employees
    return {
        "organisation_number": org,
        "name": f"Company {org}",
        "evidence": {"registry_live": {"status": "available", "value": value}},
        "external_observations": [],
        "run_metrics": {"logical_requests": 3, "requests": 6, "bytes": 10, "latencies_ms": []},
    }


def _observation(org: str, value: float = 1.0) -> dict:
    return {
        "id": f"annual-workforce-{org}",
        "organisation_number": org,
        "platform": "brreg",
        "signal_type": "workforce_snapshot",
        "source_url": f"https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/{org}/2025",
        "retrieved_at": "2026-09-16T00:00:00Z",
        "content_sha256": "a" * 64,
        "exact_entity": True,
        "identity_proof": [{"type": "organisation_number_in_ocr_text", "value": org}],
        "acquisition_mode": "official_api",
        "rights_status": "approved",
        "source_class": "official_annual_account_copy",
        "evidence_span": f"Antall Aarsverk i regnskapsaret {value}",
        "effective_at": "2025",
        "metrics": {
            "workforce_value": value,
            "measure": "full_time_equivalents",
            "full_time_equivalents": value,
            "year": "2025",
            "scope": "company_phrase",
            "claim_scope": "Official annual account company-scope workforce phrase.",
        },
    }


def test_extract_candidate_accepts_fte_and_abstains_on_conflict() -> None:
    count, span, status, measure = h2g.extract_candidate("Antall Aarsverk i regnskapsaret\n2.60")
    assert (count, status, measure) == (2.6, "accepted", "full_time_equivalents")
    assert "2.60" in str(span)

    count, _span, status, measure = h2g.extract_candidate(
        "Antall Aarsverk i regnskapsaret\n2.00\nAntall Aarsverk i regnskapsaret\n3.00"
    )
    assert count is None
    assert status == "conflicting_employee_counts"
    assert measure is None


def test_extract_candidate_rejects_group_phrase() -> None:
    count, _span, status, _measure = h2g.extract_candidate(
        "Konsern Antall Aarsverk i regnskapsaret 7.00"
    )
    assert count is None
    assert status == "no_employee_phrase"


def test_collect_requires_exact_org_in_ocr(monkeypatch) -> None:
    org = "123456789"
    profile = _profile(org)

    class Response:
        headers = {"content-type": "application/pdf"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit: int) -> bytes:
            return b"%PDF fake"

    class Page:
        def extract_text(self):
            return ""

    class Reader:
        pages = [Page()]

    monkeypatch.setattr(h2g.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())
    monkeypatch.setattr(h2g, "PdfReader", lambda *_args, **_kwargs: Reader())
    monkeypatch.setattr(
        h2g,
        "_ocr_pdf",
        lambda *_args, **_kwargs: f"Organisasjonsnummer {org}\nAntall Aarsverk i regnskapsaret\n2.00",
    )

    observation, audit = h2g.collect_annual_report_workforce(profile)
    assert audit["status"] == "accepted"
    assert observation is not None
    assert observation["metrics"]["workforce_value"] == 2
    assert observation["metrics"]["measure"] == "full_time_equivalents"
    assert not validate_observation(observation)

    monkeypatch.setattr(
        h2g,
        "_ocr_pdf",
        lambda *_args, **_kwargs: "Organisasjonsnummer 987654321\nAntall Aarsverk i regnskapsaret\n2.00",
    )
    observation, audit = h2g.collect_annual_report_workforce(profile)
    assert observation is None
    assert audit["status"] == "organisation_number_not_in_ocr_text"


def test_batch_enforces_request_slots_and_updates_metrics(monkeypatch) -> None:
    profiles = [_profile("111111111"), _profile("222222222"), _profile("333333333")]
    monkeypatch.setattr(h2g, "ocr_runtime_available", lambda: True)

    def fake_collect(profile, **_kwargs):
        org = profile["organisation_number"]
        return _observation(org), {
            "organisation_number": org,
            "status": "accepted",
            "request_count": 1,
            "bytes": 100,
            "request_latency_ms": 25,
        }

    monkeypatch.setattr(h2g, "collect_annual_report_workforce", fake_collect)
    monkeypatch.setattr(h2g.time, "sleep", lambda *_args: None)

    report = h2g.attach_annual_report_workforce_batch(
        profiles,
        max_requests=2,
        workers=2,
        min_start_interval=0,
        request_charge_multiplier=2,
    )
    assert report["eligible"] == 3
    assert report["selected"] == 2
    assert report["requests"] == 2
    assert report["accepted"] == 2
    assert report["added_conservative_challenge_request_charge"] == 4
    assert len(profiles[0]["external_observations"]) == 1
    assert len(profiles[1]["external_observations"]) == 1
    assert not profiles[2]["external_observations"]
    assert profiles[0]["run_metrics"]["logical_requests"] == 4
    assert profiles[0]["run_metrics"]["requests"] == 8
    assert profiles[0]["run_metrics"]["bytes"] == 110
    assert profiles[0]["run_metrics"]["latencies_ms"] == [25]


def test_batch_skips_existing_workforce_and_missing_year(monkeypatch) -> None:
    existing = _profile("111111111")
    existing["external_observations"] = [_observation("111111111")]
    missing_year = _profile("222222222", year="")
    eligible = _profile("333333333")
    monkeypatch.setattr(h2g, "ocr_runtime_available", lambda: True)
    monkeypatch.setattr(
        h2g,
        "collect_annual_report_workforce",
        lambda profile, **_kwargs: (_observation(profile["organisation_number"]), {"status": "accepted", "request_count": 1}),
    )
    monkeypatch.setattr(h2g.time, "sleep", lambda *_args: None)

    report = h2g.attach_annual_report_workforce_batch(
        [existing, missing_year, eligible],
        max_requests=10,
        workers=1,
        min_start_interval=0,
    )
    assert report["eligible"] == 1
    assert report["selected"] == 1
    assert report["accepted"] == 1
    assert len(existing["external_observations"]) == 1
    assert len(eligible["external_observations"]) == 1
