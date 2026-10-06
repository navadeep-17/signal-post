from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_brreg_change_website_candidates.py"
spec = importlib.util.spec_from_file_location("verify_brreg_change_website_candidates", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_normalize_candidate_adds_https_and_requires_host() -> None:
    assert module.normalize_candidate("www.example.no/path") == "https://www.example.no/path"
    assert module.normalize_candidate("https://example.no") == "https://example.no"


def test_read_candidates_requires_consumed_uncovered_exact_org(tmp_path: Path) -> None:
    path = tmp_path / "candidates.jsonl"
    path.write_text(
        '{"organisation_number":"123456789","candidate":"example.no"}\n',
        encoding="utf-8",
    )
    profiles = {"123456789": {"organisation_number": "123456789", "name": "EXAMPLE AS"}}
    rows = module.read_candidates(path, profiles=profiles, current_websites=set())
    assert len(rows) == 1
    assert rows[0][0] == "123456789"
    assert rows[0][2] == "https://example.no"


def test_verify_one_uses_identity_and_registry_guard(monkeypatch) -> None:
    profile = {
        "organisation_number": "123456789",
        "name": "EXAMPLE AS",
        "evidence": {},
    }

    monkeypatch.setattr(
        module,
        "fetch_bounded_homepage",
        lambda *args, **kwargs: (
            {
                "status": "available",
                "source_url": "https://example.no",
                "value": {"final_url": "https://example.no"},
            },
            {"requests": 2},
        ),
    )
    monkeypatch.setattr(
        module,
        "apply_website_identity_gate",
        lambda profile, record: {
            "website": {
                **record,
                "value": {
                    **(record.get("value") or {}),
                    "identity_assessment": {
                        "status": "exact",
                        "publishable": True,
                        "observed_organisation_numbers": ["123456789"],
                        "reasons": ["exact target organisation number observed"],
                    },
                },
            },
            "assessment": {
                "status": "exact",
                "publishable": True,
                "observed_organisation_numbers": ["123456789"],
                "reasons": ["exact target organisation number observed"],
            },
        },
    )

    def fake_guard(trial):
        return trial, []

    monkeypatch.setattr(module, "apply_registry_risk_guard", fake_guard)

    result = module.verify_one(
        ("123456789", profile, "https://example.no"),
        timeout=1.0,
    )
    assert result["site_requests"] == 2
    assert result["identity_publishable"] is True
    assert result["guard_publishable"] is True
    assert result["wrong_explicit_org"] is False
