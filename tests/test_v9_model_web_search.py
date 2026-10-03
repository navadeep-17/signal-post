from __future__ import annotations

import json
from pathlib import Path
import sys

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
    DEFAULT_OUTPUT_USD_PER_MILLION,
    DEFAULT_WEB_SEARCH_USD_PER_CALL,
    _estimated_cost_usd,
)


def profile() -> dict:
    return {
        "organisation_number": "123456789",
        "name": "EXAMPLE BEDRIFT AS",
        "municipality": "OSLO",
    }


def test_model_prompt_anchors_exact_legal_entity() -> None:
    prompt = _company_prompt(profile())

    assert "EXAMPLE BEDRIFT AS" in prompt
    assert "123456789" in prompt
    assert "OSLO" in prompt
    assert "parent-company" in prompt
    assert "namesakes" in prompt


def test_response_parser_extracts_url_citations_without_raw_payload_fields() -> None:
    payload = {
        "output": [
            {"type": "web_search_call", "id": "search_1"},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Likely official site: Example.",
                        "annotations": [
                            {"type": "url_citation", "url": "https://example.no/", "title": "Example"},
                            {"type": "url_citation", "url": "https://example.no/", "title": "Duplicate"},
                            {"type": "url_citation", "url": "https://other.no/", "title": "Other"},
                        ],
                    }
                ],
            },
        ]
    }

    results, text = _citation_urls(payload)

    assert [item["url"] for item in results] == ["https://example.no/", "https://other.no/"]
    assert results[0]["provider"] == "openai_responses_web_search"
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
    assert all(item["method"] == "untrusted_model_url_nomination_v1" for item in selected)


def test_model_candidate_rank_is_not_treated_as_identity_proof() -> None:
    selected = choose_model_url_candidates(
        [
            {"url": "https://parent-group.no/", "rank": 1, "title": "Parent Group"},
            {"url": "https://possible-company.no/", "rank": 2, "title": "Possible"},
        ],
        limit=2,
    )

    assert len(selected) == 2
    assert all("publishable" not in item for item in selected)
    assert all("score" not in item for item in selected)


def test_openai_web_search_request_forces_and_bounds_hosted_search(monkeypatch) -> None:
    captured: dict = {}
    payload = {
        "output": [
            {"type": "web_search_call", "id": "search_1"},
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
    assert captured["body"]["tools"] == [{"type": "web_search"}]
    assert captured["body"]["tool_choice"] == "required"
    assert captured["body"]["max_tool_calls"] == 1
    assert captured["body"]["reasoning"] == {"effort": "none"}
    assert captured["body"]["store"] is False
    assert operation["web_search_tool_calls"] == 1
    assert operation["max_web_search_tool_calls"] == 1
    assert operation["web_search_required"] is True


def test_model_search_cost_accounting_is_explicit_and_deterministic() -> None:
    assert DEFAULT_WEB_SEARCH_USD_PER_CALL == 0.01
    assert DEFAULT_INPUT_USD_PER_MILLION == 0.10
    assert DEFAULT_OUTPUT_USD_PER_MILLION == 0.50

    cost = _estimated_cost_usd(
        web_search_calls=20,
        input_tokens=10_000,
        output_tokens=2_000,
        web_search_usd_per_call=DEFAULT_WEB_SEARCH_USD_PER_CALL,
        input_usd_per_million=DEFAULT_INPUT_USD_PER_MILLION,
        output_usd_per_million=DEFAULT_OUTPUT_USD_PER_MILLION,
    )

    assert cost == 0.202
