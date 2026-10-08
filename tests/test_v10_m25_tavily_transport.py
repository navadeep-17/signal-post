"""M25: transport/budget tests use fake opener — never contact Tavily."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import json
import sys
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.tavily_bounded_transport import (
    CHALLENGE_REDIRECT_CHARGE_MULTIPLIER,
    MAX_RESPONSE_BYTES,
    SiteSlotBudget,
    TAVILY_SEARCH_ENDPOINT,
    execute_bounded_search,
)
from norway_company_agent.tavily_offline_candidate import offline_screen


PROFILE = {
    "name": "EXAMPLE BEDRIFT AS",
    "organisation_number": "123456789",
    "municipality": "OSLO",
}
FIXTURE = {
    "results": [{
        "url": "https://examplebedrift.no/",
        "title": "Example Bedrift AS",
        "content": "Org nr 123 456 789 i Oslo",
        "score": 0.99,
        "raw_content": "SECRET_PROVIDER_RAW_HTML",
    }],
    "answer": "UNTRUSTED_PROVIDER_GENERATED_ANSWER",
}


class MockResponse:
    def __init__(self, value: bytes, url: str = TAVILY_SEARCH_ENDPOINT):
        self.value = BytesIO(value)
        self.url = url

    def geturl(self):
        return self.url

    def read(self, limit):
        return self.value.read(limit)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.value.close()


class MockOpener:
    def __init__(self, response=None, error=None):
        self.calls = []
        self.response = response
        self.error = error

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error:
            raise self.error
        return self.response


def happy():
    return MockOpener(response=MockResponse(json.dumps(FIXTURE).encode()))


def test_no_key_never_dispatches():
    op = happy()
    result = execute_bounded_search(PROFILE, api_key="", opener=op)
    assert result.status == "no_key_no_request"
    assert result.logical_requests_charged == 0
    assert op.calls == []


def test_exact_one_basic_post_and_no_untrusted_provider_fields_persisted():
    op = happy()
    result = execute_bounded_search(PROFILE, api_key="FAKE_TEST_KEY", opener=op)
    assert result.status == "ok_transient_candidates_only"
    assert result.logical_requests_charged == 1
    assert result.conservative_challenge_charge == 2
    assert len(op.calls) == 1
    request, timeout = op.calls[0]
    assert request.get_method() == "POST"
    assert request.full_url == TAVILY_SEARCH_ENDPOINT
    assert request.get_header("Authorization") == "Bearer FAKE_TEST_KEY"
    assert timeout == 6.0
    body = json.loads(request.data)
    assert body["search_depth"] == "basic"
    assert body["auto_parameters"] is False
    assert body["include_answer"] is False
    assert body["include_raw_content"] is False
    assert body["include_images"] is False
    assert body["max_results"] <= 10
    assert "EXAMPLE BEDRIFT AS" in body["query"]
    assert "123456789" in body["query"]
    audit = result.audit()
    assert audit["published_company_claims"] == 0
    assert audit["payload_persisted"] is False
    assert "FAKE_TEST_KEY" not in str(audit)
    assert "SECRET_PROVIDER" not in str(audit)
    assert PROFILE["organisation_number"] not in str(audit)


def test_existing_h1b_nomination_does_not_publish_without_page():
    result = execute_bounded_search(PROFILE, api_key="FAKE_TEST_KEY", opener=happy())
    assert result.payload is not None
    nomination = offline_screen(PROFILE, result.payload)
    assert nomination["candidate_nominated"] is True
    assert nomination["status"] == "independent_fetch_required"
    assert nomination["published_claims"] == 0


def test_rate_limit_out_of_credits_is_one_charged_no_retry():
    error = urllib.error.HTTPError(TAVILY_SEARCH_ENDPOINT, 429, "Too many", {}, None)
    op = MockOpener(error=error)
    result = execute_bounded_search(PROFILE, api_key="FAKE_TEST_KEY", opener=op)
    assert result.status == "rate_limited_or_out_of_credits"
    assert result.logical_requests_charged == 1
    assert result.payload is None
    assert len(op.calls) == 1


def test_key_error_keeps_private_response_out_of_audit():
    error = urllib.error.HTTPError(TAVILY_SEARCH_ENDPOINT, 401, "SECRET_PRIVATE_REASON", {}, None)
    op = MockOpener(error=error)
    result = execute_bounded_search(PROFILE, api_key="FAKE_TEST_KEY", opener=op)
    assert result.status == "invalid_or_forbidden_key"
    assert "SECRET_PRIVATE_REASON" not in str(result.audit())


def test_redirect_is_blocked():
    error = urllib.error.HTTPError(TAVILY_SEARCH_ENDPOINT, 302, "Redirect", {}, None)
    result = execute_bounded_search(PROFILE, api_key="FAKE_TEST_KEY", opener=MockOpener(error=error))
    assert result.status == "redirect_blocked"
    assert result.conservative_challenge_charge == 2


def test_mock_redirected_success_cannot_look_like_trusted_api():
    op = MockOpener(response=MockResponse(json.dumps(FIXTURE).encode(), url="https://attacker.test/search"))
    result = execute_bounded_search(PROFILE, api_key="FAKE_TEST_KEY", opener=op)
    assert result.status == "unexpected_response_origin"
    assert result.payload is None


def test_transport_error_suppresses_raw_exception_text():
    op = MockOpener(error=urllib.error.URLError("SECRET_EXCEPTION_BODY"))
    result = execute_bounded_search(PROFILE, api_key="FAKE_TEST_KEY", opener=op)
    assert result.status == "transport_error"
    assert "SECRET_EXCEPTION_BODY" not in str(result.audit())
    assert len(op.calls) == 1


def test_oversize_response_rejected_not_persisted():
    op = MockOpener(response=MockResponse(b"x" * (MAX_RESPONSE_BYTES + 1)))
    result = execute_bounded_search(PROFILE, api_key="FAKE_TEST_KEY", opener=op)
    assert result.status == "oversized_provider_response"
    assert result.payload is None


def test_invalid_response_rejected():
    for data in (b'not-json', b'[]', b'{}', b'{"results": {}}'):
        op = MockOpener(response=MockResponse(data))
        result = execute_bounded_search(PROFILE, api_key="FAKE_TEST_KEY", opener=op)
        assert result.status in ("invalid_json_response", "invalid_search_response")
        assert result.payload is None


def test_invalid_company_identity_or_timeout_causes_zero_requests():
    cases = [
        {**PROFILE, "organisation_number": "123 456 789"},
        {**PROFILE, "organisation_number": 123456789},
        {**PROFILE, "name": ""},
        {**PROFILE, "municipality": ""},
    ]
    for case in cases:
        op = happy()
        try:
            execute_bounded_search(case, api_key="FAKE_TEST_KEY", opener=op)
        except ValueError:
            pass
        else:
            raise AssertionError("Bad organisation query accepted")
        assert op.calls == []
    for timeout in (0, 10, -1):
        op = happy()
        try:
            execute_bounded_search(PROFILE, api_key="FAKE_TEST_KEY", opener=op, timeout_seconds=timeout)
        except ValueError:
            pass
        else:
            raise AssertionError("Unsafe timeout accepted")
        assert op.calls == []


def test_search_then_homepage_consumes_three_of_four_reserved_slots():
    slots = SiteSlotBudget()
    slots.reserve_search()
    slots.reserve_homepage()
    assert slots.used == 3
    assert slots.conservative_charge == 6
    try:
        slots.reserve_homepage()
    except ValueError:
        pass
    else:
        raise AssertionError("A second homepage must not fit after search")


def test_second_search_is_denied_and_slack_does_not_allow_extra_calls():
    slots = SiteSlotBudget()
    slots.reserve_search()
    for _ in range(2):
        try:
            slots.reserve_search()
        except ValueError:
            pass
        else:
            raise AssertionError("Multiple searches must fail")
    slots.reserve_homepage()
    assert slots.used == 3
    assert slots.conservative_charge == 6


def test_theoretical_100_company_replacement_bound_not_append():
    # V8 reserves exactly 4 site calls for every company; a search-plus-crawl
    # consumes 3 within this reserve, not three extra calls.
    counted_company_cap = 100 * (5 + 4)
    shared = 1 + 97 + 1 + 1
    theoretical = (counted_company_cap + shared) * CHALLENGE_REDIRECT_CHARGE_MULTIPLIER
    assert theoretical == 2000
    naive_extra_search_plus_crawl = theoretical + 100 * (1 + 2) * 2
    assert naive_extra_search_plus_crawl == 2600


def test_real_endpoint_url_cannot_be_overridden_by_nominee():
    op = happy()
    fake = {**PROFILE, "website": "https://attacker.test/"}
    execute_bounded_search(fake, api_key="FAKE_TEST_KEY", opener=op)
    assert op.calls[0][0].full_url == TAVILY_SEARCH_ENDPOINT
