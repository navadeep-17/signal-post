from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from norway_company_agent.model_web_search import (  # noqa: E402
    _citation_urls,
    _company_prompt,
    choose_model_url_candidates,
)
from run_model_search_discovery import _estimated_cost_usd  # noqa: E402


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


def test_model_search_cost_accounting_is_explicit_and_deterministic() -> None:
    cost = _estimated_cost_usd(
        web_search_calls=20,
        input_tokens=10_000,
        output_tokens=2_000,
        web_search_usd_per_call=0.01,
        input_usd_per_million=0.05,
        output_usd_per_million=0.25,
    )

    assert cost == 0.201
