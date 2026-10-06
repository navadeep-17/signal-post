from __future__ import annotations

import json

from norway_company_agent.v9_openai_websearch_v2 import (
    DEFAULT_MODEL,
    OpenAIWebSearchV2Settings,
    build_request_body,
    estimate_cost_usd,
    extract_search_results,
    parse_response,
    provider_readiness,
    search_candidate_urls,
)


def profile(
    *,
    name: str = "FALEX FORVALTNING AS",
    org: str = "917615624",
    municipality: str = "OSLO",
) -> dict:
    return {
        "organisation_number": org,
        "name": name,
        "municipality": municipality,
    }


def response(
    results,
    *,
    sources=None,
    searches: int = 1,
    input_tokens: int = 1000,
    output_tokens: int = 100,
    message_text: str = "https://hallucinated.example/",
):
    output = []
    for index in range(searches):
        output.append(
            {
                "type": "web_search_call",
                "id": f"ws_{index}",
                "status": "completed",
                "action": {
                    "type": "search",
                    "queries": ['"917615624" "FALEX FORVALTNING AS"'],
                    "sources": sources or [],
                },
                "results": results,
            }
        )
    output.append(
        {
            "type": "message",
            "content": [
                {
                    "type": "output_text",
                    "text": message_text,
                    "annotations": [
                        {
                            "type": "url_citation",
                            "url": "https://model-message-only.example/",
                            "title": "Model citation only",
                        }
                    ],
                }
            ],
        }
    )
    return {
        "id": "resp_test",
        "status": "completed",
        "output": output,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    }


def test_request_is_one_low_context_search_and_includes_raw_sources() -> None:
    body = build_request_body(profile())

    assert body["model"] == DEFAULT_MODEL == "gpt-6-luna"
    assert body["store"] is False
    assert body["reasoning"] == {"effort": "none"}
    assert body["tools"] == [{"type": "web_search", "search_context_size": "low"}]
    assert body["tool_choice"] == "required"
    assert body["max_tool_calls"] == 1
    assert body["parallel_tool_calls"] is False
    assert body["include"] == [
        "web_search_call.results",
        "web_search_call.action.sources",
    ]

    rendered = json.dumps(body)
    assert "917615624" in rendered
    assert "FALEX FORVALTNING AS" in rendered


def test_adapter_is_pinned_to_current_luna_model() -> None:
    OpenAIWebSearchV2Settings(model="gpt-6-luna")

    try:
        OpenAIWebSearchV2Settings(model="gpt-5.6-luna")
    except ValueError as exc:
        assert "pinned to gpt-6-luna" in str(exc)
    else:
        raise AssertionError("stale model must be rejected")


def test_extracts_only_explicit_web_search_call_data() -> None:
    payload = response(
        [
            {
                "url": "https://falex.no/",
                "title": "Falex Forvaltning AS – Forvaltning",
                "snippet": "Eiendomsforvaltning i Oslo",
            }
        ],
        sources=[
            {"type": "url", "url": "https://falex.no/"},
            {"type": "url", "url": "https://proff.no/selskap/falex/917615624"},
        ],
        message_text="Use https://hallucinated.example/ instead.",
    )

    extracted = extract_search_results(payload)

    assert extracted["status"] == "results_found"
    urls = [item["url"] for item in extracted["results"]]
    assert "https://falex.no/" in urls
    assert "https://proff.no/selskap/falex/917615624" in urls
    assert "https://hallucinated.example/" not in urls
    assert "https://model-message-only.example/" not in urls
    assert extracted["query_sha256"]
    assert all(len(value) == 64 for value in extracted["query_sha256"])


def test_parse_uses_transient_result_title_then_discards_provider_text() -> None:
    payload = response(
        [
            {
                "url": "https://falex.no/",
                "title": "Falex Forvaltning AS – Forvaltning",
                "snippet": "Eiendomsforvaltning i Oslo",
            },
            {
                "url": "https://proff.no/selskap/falex/917615624",
                "title": "Falex Forvaltning AS",
                "snippet": "Org nr 917 615 624",
            },
        ]
    )

    parsed = parse_response(profile(), payload)

    assert parsed["status"] == "candidates_found"
    assert parsed["candidate_urls"] == ["https://falex.no/"]
    assert parsed["publication_authorized"] is False
    assert parsed["provider_result_text_retained"] is False
    assert parsed["provider_message_text_consumed"] is False

    rendered = repr(parsed)
    assert "Falex Forvaltning AS – Forvaltning" not in rendered
    assert "Eiendomsforvaltning i Oslo" not in rendered
    assert "hallucinated.example" not in rendered


def test_source_only_url_does_not_gain_synthetic_identity_evidence() -> None:
    payload = response(
        [],
        sources=[
            {"type": "url", "url": "https://falex.no/"},
        ],
    )

    parsed = parse_response(profile(), payload)

    # A source URL alone is not promoted by invented title/snippet evidence. The existing
    # transient scorer may reject it and the adapter must accept that abstention.
    assert parsed["candidate_urls"] == []
    assert parsed["publication_authorized"] is False


def test_multiple_tool_calls_fail_closed_and_ignore_message_urls() -> None:
    payload = response(
        [{"url": "https://falex.no/", "title": "Falex Forvaltning AS"}],
        searches=2,
    )

    parsed = parse_response(profile(), payload)

    assert parsed["status"] == "tool_call_bound_violation"
    assert parsed["candidate_urls"] == []
    assert parsed["cost"]["web_search_calls"] == 2


def test_non_search_action_fails_closed() -> None:
    payload = response([])
    payload["output"][0]["action"] = {
        "type": "open_page",
        "url": "https://falex.no/",
    }

    parsed = parse_response(profile(), payload)

    assert parsed["status"] == "non_search_tool_action"
    assert parsed["candidate_urls"] == []


def test_cost_estimate_uses_current_luna_and_web_search_rates() -> None:
    cost = estimate_cost_usd(
        response([], input_tokens=1_000, output_tokens=100)
    )

    # $0.01 search + $0.0001 input + $0.00005 output.
    assert cost["web_search_calls"] == 1
    assert cost["estimated_cost_usd"] == 0.01015
    assert cost["pricing_assumption"]["model"] == "gpt-6-luna"
    assert cost["pricing_assumption"]["input_usd_per_million_tokens"] == 0.10
    assert cost["pricing_assumption"]["output_usd_per_million_tokens"] == 0.50


def test_missing_key_abstains_without_network() -> None:
    result = search_candidate_urls(profile(), api_key=" ")

    assert result["status"] == "provider_key_unavailable"
    assert result["candidate_urls"] == []
    assert result["publication_authorized"] is False
    assert result["provider_message_text_consumed"] is False


def test_provider_readiness_never_self_approves_rights_or_evaluator_key() -> None:
    blocked = provider_readiness(
        max_searches=20,
        evaluator_key_available=False,
        rights_status="unknown",
        challenge_cost_budget_usd=10.0,
        project_third_party_budget_usd=0.0,
    )
    assert blocked["allowed_for_live_v9_experiment"] is False
    assert "provider_not_evaluator_reproducible" in blocked["reasons"]
    assert "provider_key_not_available_to_evaluator" in blocked["reasons"]
    assert "provider_rights_not_confirmed" in blocked["reasons"]
    assert "project_zero_cost_policy" in blocked["reasons"]

    allowed = provider_readiness(
        max_searches=20,
        evaluator_key_available=True,
        rights_status="contract_confirmed",
        challenge_cost_budget_usd=10.0,
        project_third_party_budget_usd=10.0,
    )
    assert allowed["allowed_for_live_v9_experiment"] is True
    assert allowed["allowed_for_production_candidate"] is False
    assert allowed["projected_provider_cost_usd"] == 0.2
