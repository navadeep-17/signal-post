from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import norway_company_agent.brreg_changes as changes  # noqa: E402
from norway_company_agent.canonical_projection import (  # noqa: E402
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.synthesis import build_company_synthesis, validate_company_synthesis  # noqa: E402


ORG = "123456789"


def _contract(org: str = ORG) -> dict:
    return {
        "organisation_number": org,
        "run": {
            "run_id": "fixture",
            "started_at": "2026-10-01T00:00:00Z",
            "completed_at": "2026-10-01T00:00:01Z",
            "terminal_status": "completed",
        },
        "claims": [],
        "evidence": [],
        "changes": [],
        "errors": [],
        "operations": {"requests": 0, "runtime_ms": 1, "third_party_cost_usd": 0.0},
    }


def _event(*, event_id: str = "42", effective_at: str = "2026-09-10T12:00:00Z") -> dict:
    return {
        "organisation_number": ORG,
        "event_id": event_id,
        "event_type": "Endring",
        "effective_at": effective_at,
        "retrieved_at": "2026-10-01T00:00:00Z",
        "source_url": changes.target_source_url(ORG),
        "retrieval_url": changes.build_change_feed_url([ORG]),
        "content_sha256": "a" * 64,
        "changes": [
            {
                "path": "/sisteInnsendteAarsregnskap",
                "label": "latest submitted annual accounts",
                "operation": "replace",
                "value": "2025",
            }
        ],
        "summary": "latest submitted annual accounts updated: 2025",
    }


class _Headers:
    def get(self, key: str, default: str = "") -> str:
        return default


class _Response:
    def __init__(self, payload: dict):
        self.raw = json.dumps(payload).encode("utf-8")
        self.headers = _Headers()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit: int) -> bytes:
        return self.raw[:limit]


def _payload(events: list[dict]) -> dict:
    return {
        "_embedded": {"oppdaterteEnheter": events},
        "page": {"size": 10000, "totalElements": len(events), "totalPages": 1, "number": 0},
    }


def test_change_feed_request_ceiling_and_exact_source_url() -> None:
    assert changes.theoretical_change_feed_requests(0) == 0
    assert changes.theoretical_change_feed_requests(1) == 1
    assert changes.theoretical_change_feed_requests(100) == 1
    assert changes.theoretical_change_feed_requests(101) == 2

    url = changes.build_change_feed_url([ORG, "987654321"])
    assert url.startswith(changes.ENDPOINT + "?")
    assert "includeChanges=true" in url
    assert "%2C" in url
    assert changes.target_source_url(ORG).count(ORG) == 1


def test_fetch_filters_unknown_paths_old_events_and_caps_recent_events(monkeypatch) -> None:
    events = [
        {
            "organisasjonsnummer": ORG,
            "oppdateringsid": 5,
            "dato": "2026-09-20T10:00:00Z",
            "endringstype": "Endring",
            "endringer": [{"op": "replace", "path": "/antallAnsatte", "value": 13}],
        },
        {
            "organisasjonsnummer": ORG,
            "oppdateringsid": 4,
            "dato": "2026-09-10T10:00:00Z",
            "endringstype": "Endring",
            "endringer": [{"op": "replace", "path": "/sisteInnsendteAarsregnskap", "value": "2025"}],
        },
        {
            "organisasjonsnummer": ORG,
            "oppdateringsid": 3,
            "dato": "2026-08-10T10:00:00Z",
            "endringstype": "Endring",
            "endringer": [{"op": "add", "path": "/naeringskode1", "value": {"kode": "62.100", "beskrivelse": "Programmering"}}],
        },
        {
            "organisasjonsnummer": ORG,
            "oppdateringsid": 2,
            "dato": "2026-07-10T10:00:00Z",
            "endringstype": "Endring",
            "endringer": [{"op": "replace", "path": "/vedtektsdato", "value": "2026-07-01"}],
        },
        {
            "organisasjonsnummer": ORG,
            "oppdateringsid": 99,
            "dato": "2026-09-25T10:00:00Z",
            "endringstype": "Endring",
            "endringer": [{"op": "replace", "path": "/unsupportedField", "value": "x"}],
        },
        {
            "organisasjonsnummer": ORG,
            "oppdateringsid": 1,
            "dato": "2024-01-01T10:00:00Z",
            "endringstype": "Endring",
            "endringer": [{"op": "replace", "path": "/antallAnsatte", "value": 1}],
        },
    ]
    monkeypatch.setattr(changes.urllib.request, "urlopen", lambda request, timeout=20.0: _Response(_payload(events)))

    grouped, metrics = changes.fetch_registry_change_events(
        [ORG],
        as_of="2026-10-01T00:00:00Z",
        lookback_days=365,
        max_events_per_company=3,
    )

    assert metrics["requests"] == 1
    assert metrics["integrity_errors"] == []
    assert metrics["events_received"] == 6
    assert metrics["events_published"] == 3
    assert [item["event_id"] for item in grouped[ORG]] == ["5", "4", "3"]
    assert grouped[ORG][0]["summary"] == "registered employee count updated: 13"
    assert grouped[ORG][2]["changes"][0]["label"] == "registered industry"


def test_fetch_flags_unexpected_organisation_and_never_attributes_it(monkeypatch) -> None:
    payload = _payload(
        [
            {
                "organisasjonsnummer": "987654321",
                "oppdateringsid": 7,
                "dato": "2026-09-20T10:00:00Z",
                "endringstype": "Endring",
                "endringer": [{"op": "replace", "path": "/antallAnsatte", "value": 4}],
            }
        ]
    )
    monkeypatch.setattr(changes.urllib.request, "urlopen", lambda request, timeout=20.0: _Response(payload))

    grouped, metrics = changes.fetch_registry_change_events([ORG], as_of="2026-10-01T00:00:00Z")

    assert grouped[ORG] == []
    assert metrics["events_published"] == 0
    assert metrics["integrity_errors"] == ["Unexpected organisation number in BRREG change feed: 987654321"]


def test_projection_is_idempotent_evidence_backed_and_rejects_wrong_company() -> None:
    first = changes.project_registry_change_claims(_contract(), [_event()])
    second = changes.project_registry_change_claims(deepcopy(first), [_event()])
    assert second == first

    claims = [item for item in first["claims"] if item.get("field") == "official_registry_change"]
    assert len(claims) == 1
    assert claims[0]["signal_type"] == "official_registry_change"
    assert "not company-authored news" in claims[0]["claim_scope"]
    evidence_by_id = {item["id"]: item for item in first["evidence"]}
    evidence = evidence_by_id[claims[0]["evidence_ids"][0]]
    assert evidence["source_class"] == "official"
    assert evidence["source_row_key"] == "42"
    assert evidence["effective_at"] == "2026-09-10T12:00:00Z"
    assert validate_contract_object(first) == []

    wrong = _event()
    wrong["organisation_number"] = "987654321"
    with pytest.raises(ValueError, match="organisation number mismatch"):
        changes.project_registry_change_claims(_contract(), [wrong])


def test_registry_change_flows_to_canonical_company_record_and_what_changed() -> None:
    projected = changes.project_registry_change_claims(_contract(), [_event()])
    canonical = project_canonical_profile(projected)
    assert validate_canonical_projection(canonical) == []

    registry_facts = [fact for fact in canonical["canonical_facts"] if fact.get("type") == "registry_change"]
    assert len(registry_facts) == 1
    assert registry_facts[0]["canonical_field"] == "company.registry_change"
    assert registry_facts[0] in canonical["canonical_profile"]["company_record"]
    assert canonical["canonical_profile"]["public_activity"] == []

    canonical["synthesis"] = build_company_synthesis(canonical)
    assert validate_company_synthesis(canonical) == []
    changed = canonical["synthesis"]["what_changed"]
    assert changed["change_count"] == 1
    assert "official BRREG registry change" in changed["text"]
    assert "latest submitted annual accounts updated: 2025" in changed["text"]
    assert changed["source_boundary"].startswith("registry_changes are official BRREG")
    assert registry_facts[0]["evidence_ids"][0] in changed["evidence_ids"]
