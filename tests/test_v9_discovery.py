from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_discovery import (  # noqa: E402
    build_v9_query_plan,
    nominate_v9_candidate_urls,
)


def profile() -> dict:
    return {
        "organisation_number": "123456789",
        "name": "EXAMPLE BEDRIFT AS",
        "municipality": "OSLO",
    }


def result(
    url: str,
    *,
    title: str = "Example Bedrift AS",
    snippet: str = "Org nr 123 456 789 Oslo",
    rank: int = 1,
) -> dict:
    return {
        "url": url,
        "title": title,
        "snippet": snippet,
        "rank": rank,
        "provider": "test_provider",
        "query": "transient query text",
    }


def test_query_plan_matches_v9_org_number_first_strategy() -> None:
    plan = build_v9_query_plan(profile())
    queries = [item["query"] for item in plan]

    assert queries == [
        '"123456789"',
        '"123 456 789"',
        '"Org.nr. 123 456 789"',
        '"EXAMPLE BEDRIFT AS" "123456789"',
        '"EXAMPLE BEDRIFT AS" "org nr"',
    ]
    assert all(len(item["query_sha256"]) == 64 for item in plan)


def test_nomination_output_is_urls_only_not_provider_text() -> None:
    decision = nominate_v9_candidate_urls(
        profile(),
        [result("https://examplebedrift.no/")],
    )

    assert decision["candidate_urls"] == ["https://examplebedrift.no/"]
    assert decision["publication_authorized"] is False
    assert decision["provider_result_text_retained"] is False

    rendered = repr(decision)
    assert "Example Bedrift AS" not in rendered
    assert "Org nr 123 456 789 Oslo" not in rendered
    assert "transient query text" not in rendered


def test_social_and_directory_hosts_are_rejected() -> None:
    decision = nominate_v9_candidate_urls(
        profile(),
        [
            result("https://facebook.com/examplebedrift"),
            result("https://proff.no/selskap/example-bedrift-as/123456789"),
        ],
    )

    assert decision["candidate_urls"] == []
    assert all(
        item["reason"] == "blocked_non_first_party_host"
        for item in decision["decisions"]
    )


def test_candidates_are_deduplicated_by_registered_domain() -> None:
    decision = nominate_v9_candidate_urls(
        profile(),
        [
            result("https://www.examplebedrift.no/", rank=1),
            result("https://examplebedrift.no/kontakt", rank=2),
        ],
    )

    assert decision["candidate_count"] == 1
    assert len(decision["candidate_urls"]) == 1
    assert any(
        item["reason"] == "duplicate_registered_domain"
        for item in decision["decisions"]
    )


def test_candidate_count_is_hard_bounded_to_three() -> None:
    rows = [
        result(f"https://examplebedrift{i}.no/", rank=i)
        for i in range(1, 6)
    ]

    decision = nominate_v9_candidate_urls(profile(), rows, max_candidates=3)

    assert len(decision["candidate_urls"]) <= 3
    assert decision["max_candidates"] == 3


def test_weak_name_only_result_does_not_get_nominated() -> None:
    decision = nominate_v9_candidate_urls(
        profile(),
        [
            result(
                "https://random-brand.no/",
                title="Example Bedrift AS",
                snippet="Bedrift i Oslo",
            )
        ],
    )

    assert decision["candidate_urls"] == []
    assert decision["decisions"][0]["reason"] == "insufficient_nomination_evidence"
