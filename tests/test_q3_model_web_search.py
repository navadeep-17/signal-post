from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import norway_company_agent.model_web_search as model_search  # noqa: E402
from norway_company_agent.model_web_search import (  # noqa: E402
    _citation_urls,
    _company_prompt,
    choose_model_url_candidates,
)
from run_model_search_discovery import (  # noqa: E402
    DEFAULT_INPUT_USD_PER_MILLION,
    DEFAULT_MAX_PROVIDER_INPUT_TOKENS_PER_COMPANY,
    DEFAULT_MAX_PROVIDER_OUTPUT_TOKENS_PER_COMPANY,
    DEFAULT_OUTPUT_USD_PER_MILLION,
    DEFAULT_WEB_SEARCH_USD_PER_CALL,
    _conflict_quarantine,
    _estimated_cost_usd,
    _preflight_cost_ceiling_usd,
    _q3_multi_entity_org_conflict,
)


def profile() -> dict:
    return {
        "organisation_number": "123456789",
        "name": "EXAMPLE BEDRIFT AS",
        "municipality": "OSLO",
    }


def test_model_prompt_anchors_exact_legal_entity_and_nomination_boundary() -> None:
    prompt = _company_prompt(profile())

    assert "EXAMPLE BEDRIFT AS" in prompt
    assert "123456789" in prompt
    assert "OSLO" in prompt
    assert "parent" in prompt
    assert "namesake" in prompt
    assert "nominations only" in prompt


def test_response_parser_extracts_action_sources_and_url_citations() -> None:
    payload = {
        "output": [
            {
                "type": "web_search_call",
                "id": "search_1",
                "action": {
                    "type": "search",
                    "sources": [
                        {"type": "url", "url": "https://example.no/about"},
                        {"type": "url", "url": "https://other.no/"},
                    ],
                },
            },
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Likely official site: Example.",
                        "annotations": [
                            {"type": "url_citation", "url": "https://example.no/about", "title": "Example"},
                            {"type": "url_citation", "url": "https://third.no/", "title": "Third"},
                        ],
                    }
                ],
            },
        ]
    }

    results, text = _citation_urls(payload)

    assert [item["url"] for item in results] == [
        "https://example.no/about",
        "https://other.no/",
        "https://third.no/",
    ]
    assert all(item["provider"] == "openai_responses_web_search" for item in results)
    assert text == "Likely official site: Example."


def test_model_url_nominations_reject_directories_socials_and_dedupe_domains() -> None:
    results = [
        {"url": "https://proff.no/selskap/example", "rank": 1},
        {"url": "https://linkedin.com/company/example", "rank": 2},
        {"url": "https://www.example.no/contact", "rank": 3},
        {"url": "https://example.no/about", "rank": 4},
        {"url": "https://example.com/", "rank": 5},
    ]

    selected = choose_model_url_candidates(results, limit=2)

    assert [item["url"] for item in selected] == [
        "https://www.example.no/contact",
        "https://example.com/",
    ]
    assert all(item["method"] == "untrusted_model_url_nomination_v2" for item in selected)
    assert all("publishable" not in item for item in selected)
    assert all("score" not in item for item in selected)


def test_openai_request_forces_one_low_context_web_search(monkeypatch) -> None:
    captured: dict = {}
    payload = {
        "output": [
            {
                "type": "web_search_call",
                "id": "search_1",
                "action": {"type": "search", "sources": [{"type": "url", "url": "https://example.no/"}]},
            },
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Example",
                        "annotations": [
                            {"type": "url_citation", "url": "https://example.no/", "title": "Example"}
                        ],
                    }
                ],
            },
        ],
        "usage": {"input_tokens": 100, "output_tokens": 20},
    }

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps(payload).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(model_search.urllib.request, "urlopen", fake_urlopen)

    results, operation = model_search.openai_web_search_candidates(
        profile(),
        "test-key-not-real",
        timeout=7.0,
    )

    assert results[0]["url"] == "https://example.no/"
    assert captured["timeout"] == 7.0
    assert captured["body"]["model"] == "gpt-6-luna"
    assert captured["body"]["tools"] == [{"type": "web_search", "search_context_size": "low"}]
    assert captured["body"]["tool_choice"] == "required"
    assert captured["body"]["max_tool_calls"] == 1
    assert captured["body"]["max_output_tokens"] == 180
    assert captured["body"]["store"] is False
    assert "reasoning" not in captured["body"]
    assert operation["web_search_tool_calls"] == 1
    assert operation["max_web_search_tool_calls"] == 1
    assert operation["search_context_size"] == "low"


def test_provider_response_with_multiple_search_calls_hard_fails(monkeypatch) -> None:
    payload = {
        "output": [
            {"type": "web_search_call", "id": "search_1"},
            {"type": "web_search_call", "id": "search_2"},
        ],
        "usage": {"input_tokens": 100, "output_tokens": 20},
    }

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(model_search.urllib.request, "urlopen", lambda request, timeout: FakeResponse())

    with pytest.raises(RuntimeError, match="web-search call ceiling"):
        model_search.openai_web_search_candidates(profile(), "test-key-not-real")


def test_cost_accounting_and_100_company_preflight_are_deterministic() -> None:
    assert DEFAULT_WEB_SEARCH_USD_PER_CALL == 0.01
    assert DEFAULT_INPUT_USD_PER_MILLION == 0.10
    assert DEFAULT_OUTPUT_USD_PER_MILLION == 0.50

    observed = _estimated_cost_usd(
        web_search_calls=20,
        input_tokens=10_000,
        output_tokens=2_000,
        web_search_usd_per_call=DEFAULT_WEB_SEARCH_USD_PER_CALL,
        input_usd_per_million=DEFAULT_INPUT_USD_PER_MILLION,
        output_usd_per_million=DEFAULT_OUTPUT_USD_PER_MILLION,
    )
    preflight = _preflight_cost_ceiling_usd(
        companies=100,
        max_input_tokens_per_company=DEFAULT_MAX_PROVIDER_INPUT_TOKENS_PER_COMPANY,
        max_output_tokens_per_company=DEFAULT_MAX_PROVIDER_OUTPUT_TOKENS_PER_COMPANY,
        web_search_usd_per_call=DEFAULT_WEB_SEARCH_USD_PER_CALL,
        input_usd_per_million=DEFAULT_INPUT_USD_PER_MILLION,
        output_usd_per_million=DEFAULT_OUTPUT_USD_PER_MILLION,
    )

    assert observed == 0.202
    assert preflight == 1.509


def test_multi_entity_search_page_conflict_detects_target_plus_other_orgs() -> None:
    assessment = {
        "observed_organisation_numbers": ["123456789", "987654321"],
        "publishable": True,
    }

    assert _q3_multi_entity_org_conflict(profile(), assessment) is True
    assert _q3_multi_entity_org_conflict(
        profile(),
        {"observed_organisation_numbers": ["123456789"], "publishable": True},
    ) is False


def test_multi_entity_conflict_quarantine_is_not_publishable() -> None:
    assessment = {
        "status": "exact",
        "score": 1.0,
        "publishable": True,
        "observed_organisation_numbers": ["123456789", "987654321"],
        "reasons": ["target organisation number appears"],
        "method": "fixture",
    }

    result = _conflict_quarantine(assessment)

    assert result["status"] == "review"
    assert result["publishable"] is False
    assert result["score"] <= 0.8
    assert result["method"] == "q3_search_candidate_multi_entity_org_guard_v1"
    assert any("shared/group-domain" in reason for reason in result["reasons"])


def test_runner_persists_only_independently_verified_candidate_pages() -> None:
    source = (ROOT / "scripts" / "run_model_search_discovery.py").read_text(encoding="utf-8")

    assert "fetch_bounded_homepage(" in source
    assert "apply_website_identity_gate(" in source
    assert "qualify_search_discovered_website(" in source
    assert "_q3_multi_entity_org_conflict(" in source
    assert 'if verified_website is not None:' in source
    assert 'row["evidence"]["website_model_search_candidate"] = verified_website' in source
    assert 'quarantined_candidate_pages_persisted": False' in source
    assert 'row["evidence"]["website_model_search_candidate"] = website' not in source
    assert "--max-external-api-cost-usd" in source
