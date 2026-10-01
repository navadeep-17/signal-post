from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent import annual_report_workforce as h2g
from norway_company_agent.workforce_contract import project_workforce_observations


def _profile(org: str = "123456789") -> dict:
    return {
        "organisation_number": org,
        "name": "Example AS",
        "latest_submitted_accounts": "2025",
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
        "run_metrics": {"logical_requests": 0, "requests": 0, "bytes": 0, "latencies_ms": []},
    }


def test_same_annual_report_fetch_yields_workforce_and_description(monkeypatch) -> None:
    org = "123456789"
    profile = _profile(org)
    # Workforce extraction intentionally targets the OCR-normalized spellings used by
    # the production H2g parser (aarsverk/regnskapsaret), while the description heading
    # remains representative of the original Norwegian report text.
    report_text = (
        f"Organisasjonsnummer {org}\n"
        "Virksomhetens art\n"
        "Selskapet utvikler og leverer programvare for energibransjen i Norge og Sverige.\n"
        "Antall aarsverk i regnskapsaret er 4\n"
        "Fortsatt drift\n"
        "Styret bekrefter forutsetningen om fortsatt drift.\n"
        + ("Tilleggsinformasjon. " * 10)
    )

    class Response:
        headers = {"content-type": "application/pdf"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit: int) -> bytes:
            return b"%PDF shared-report-bytes"

    class Page:
        def extract_text(self):
            return report_text

    class Reader:
        pages = [Page()]

    calls = {"fetch": 0}

    def fake_urlopen(*_args, **_kwargs):
        calls["fetch"] += 1
        return Response()

    monkeypatch.setattr(h2g.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(h2g, "PdfReader", lambda *_args, **_kwargs: Reader())

    workforce, audit = h2g.collect_annual_report_workforce(profile, ocr_pages=0)

    assert calls["fetch"] == 1
    assert workforce is not None
    assert workforce["signal_type"] == "workforce_snapshot"
    assert workforce["metrics"]["workforce_value"] == 4
    assert audit["description_status"] == "accepted"

    descriptions = [
        row
        for row in profile["external_observations"]
        if row.get("signal_type") == "company_profile" and row.get("company_description")
    ]
    assert len(descriptions) == 1
    assert "programvare" in descriptions[0]["company_description"]
    assert descriptions[0]["content_sha256"] == workforce["content_sha256"]
    assert descriptions[0]["source_url"] == workforce["source_url"]


def test_workforce_projection_chains_annual_report_description() -> None:
    profile = _profile()
    description = "Selskapet utvikler og leverer programvare for energibransjen i Norge."
    profile["external_observations"] = [
        {
            "id": "annual-description-test",
            "organisation_number": "123456789",
            "platform": "brreg",
            "signal_type": "company_profile",
            "source_url": "https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/123456789/2025",
            "retrieved_at": "2026-10-01T00:00:00Z",
            "content_sha256": "a" * 64,
            "exact_entity": True,
            "identity_proof": [{"type": "organisation_number_in_report_text", "value": "123456789"}],
            "acquisition_mode": "official_api",
            "rights_status": "approved",
            "source_class": "official_annual_account_copy",
            "evidence_span": description,
            "effective_at": "2025",
            "company_description": description,
            "metrics": {"claim_scope": "Official annual-account company activity description."},
        }
    ]
    contract = {"organisation_number": "123456789", "claims": [], "evidence": []}

    projected = project_workforce_observations(contract, profile)

    claims = [row for row in projected["claims"] if row.get("field") == "company_description"]
    assert len(claims) == 1
    assert claims[0]["value"] == description
    assert claims[0]["platform"] == "brreg"
    assert claims[0]["evidence_ids"]


def test_batch_reports_description_reuse_without_extra_requests(monkeypatch) -> None:
    profile = _profile()
    monkeypatch.setattr(h2g, "ocr_runtime_available", lambda: True)
    monkeypatch.setattr(h2g.time, "sleep", lambda *_args: None)

    def fake_collect(target, **_kwargs):
        org = target["organisation_number"]
        target.setdefault("external_observations", []).append(
            {
                "id": "annual-description-batch",
                "organisation_number": org,
                "platform": "brreg",
                "signal_type": "company_profile",
                "company_description": "Selskapet leverer programvare til energibransjen i Norge.",
            }
        )
        workforce = {
            "id": "annual-workforce-batch",
            "organisation_number": org,
            "signal_type": "workforce_snapshot",
        }
        return workforce, {
            "organisation_number": org,
            "status": "accepted",
            "description_status": "accepted",
            "request_count": 1,
            "bytes": 100,
            "request_latency_ms": 10,
        }

    monkeypatch.setattr(h2g, "collect_annual_report_workforce", fake_collect)

    report = h2g.attach_annual_report_workforce_batch(
        [profile],
        max_requests=1,
        workers=1,
        min_start_interval=0,
        request_charge_multiplier=2,
    )

    assert report["requests"] == 1
    assert report["accepted"] == 1
    assert report["description_accepted"] == 1
    assert report["description_status_counts"] == {"accepted": 1}
    assert profile["run_metrics"]["logical_requests"] == 1
    assert profile["run_metrics"]["requests"] == 2
