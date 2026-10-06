from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.output_contract import project_terminal_envelope  # noqa: E402

SCRIPT = ROOT / "scripts" / "replay_v9_structured_contacts.py"
spec = importlib.util.spec_from_file_location("replay_v9_structured_contacts", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _profile() -> dict:
    digest = "a" * 64
    return {
        "organisation_number": "912345678",
        "name": "EXAMPLE AS",
        "legal_form": "AS",
        "municipality": "OSLO",
        "external_observations": [],
        "evidence": {
            "registry": {
                "status": "available",
                "source_type": "official_registry_bulk",
                "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
                "retrieved_at": "2026-10-01T00:00:00Z",
                "content_sha256": "b" * 64,
                "value": {},
            },
            "website": {
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": "https://example.no/",
                "retrieved_at": "2026-10-01T00:00:00Z",
                "content_sha256": digest,
                "value": {
                    "final_url": "https://example.no/",
                    "content_sha256": digest,
                    "identity_text_excerpt": "EXAMPLE AS",
                    "identity_assessment": {
                        "status": "exact",
                        "score": 1.0,
                        "publishable": True,
                        "method": "test",
                    },
                    "structured_organisations": [
                        {
                            "@type": "Organization",
                            "name": "EXAMPLE AS",
                            "email": "post@example.no",
                            "telephone": "+47 98 76 54 32",
                        }
                    ],
                },
            },
        },
        "run_metrics": {"requests": 4},
    }


def _baseline(profile: dict) -> dict:
    envelope = {
        "run_id": "m4-test",
        "organisation_number": profile["organisation_number"],
        "state": "complete",
        "started_at": "2026-10-01T00:00:00Z",
        "completed_at": "2026-10-01T00:00:01Z",
        "profile": profile,
    }
    return project_terminal_envelope(envelope)


def test_reproject_row_adds_structured_email_and_phone_only() -> None:
    profile = _profile()
    baseline = _baseline(profile)
    before_noncontact = module._noncontact_claim_signature(baseline)

    updated, audit = module.reproject_row(baseline, profile)

    assert module._noncontact_claim_signature(updated) == before_noncontact
    pairs = module._contact_pairs(updated)
    assert ("external.contact_email", '"post@example.no"') in pairs
    assert ("external.contact_phone", '"+4798765432"') in pairs
    assert {item["field"] for item in audit} == {
        "external.contact_email",
        "external.contact_phone",
    }
    assert all(item["evidence"] for item in audit)


def test_reproject_row_preserves_existing_contact_claims() -> None:
    profile = _profile()
    baseline = _baseline(profile)
    # First replay creates the managed claims; the second replay must be idempotent.
    once, _ = module.reproject_row(baseline, profile)
    twice, audit = module.reproject_row(once, profile)
    assert module._contact_pairs(twice) == module._contact_pairs(once)
    assert audit == []
