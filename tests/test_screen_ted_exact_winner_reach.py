from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_ted_exact_winner_reach.py"
spec = importlib.util.spec_from_file_location("screen_ted_exact_winner_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_winner_query_batches_exact_orgs() -> None:
    query = module.build_winner_query(["123456789", "987654321"])
    assert query == "winner-identifier IN (123456789 987654321)"


def test_exact_orgs_reject_numeric_substring_collision() -> None:
    assert module.exact_orgs(["123456789", "NO:ORG 987654321"]) == {"123456789", "987654321"}
    assert module.exact_orgs(["01234567890"]) == set()


def test_single_winner_allows_contact_candidate_attribution() -> None:
    notice = {
        "winner-identifier": ["0192:123456789"],
        "winner-name": ["TARGET AS"],
        "winner-internet-address": ["https://target.example"],
        "winner-email": ["post@target.example"],
        "winner-decision-date": ["2026-05-01"],
        "publication-number": ["1-2026"],
    }
    result = module.analyse_notice(notice, {"123456789"}, date(2021, 10, 5))
    assert result["target_orgs"] == ["123456789"]
    assert result["recent"] is True
    assert result["unambiguous_single_winner"] is True
    assert result["websites"] == ["https://target.example"]
    assert result["emails"] == ["post@target.example"]


def test_multiwinner_notice_counts_activity_but_suppresses_contacts() -> None:
    notice = {
        "winner-identifier": ["123456789", "987654321"],
        "winner-internet-address": ["https://one.example", "https://two.example"],
        "winner-email": ["one@example.test", "two@example.test"],
        "publication-date": ["2026-07-01"],
    }
    result = module.analyse_notice(notice, {"123456789"}, date(2021, 10, 5))
    assert result["target_orgs"] == ["123456789"]
    assert result["recent"] is True
    assert result["unambiguous_single_winner"] is False
    assert result["websites"] == []
    assert result["emails"] == []


def test_nonwinner_target_does_not_match_other_notice_numbers() -> None:
    notice = {
        "winner-identifier": ["987654321"],
        "notice-title": ["Contract involving reference 123456789"],
        "publication-date": ["2026-07-01"],
    }
    result = module.analyse_notice(notice, {"123456789"}, date(2021, 10, 5))
    assert result["target_orgs"] == []


def test_field_value_supports_nested_fields_response_shape() -> None:
    notice = {"fields": {"winner-identifier": ["123456789"]}}
    assert module.field_strings(notice, "winner-identifier") == ["123456789"]
