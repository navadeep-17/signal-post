import json
from pathlib import Path
import sys
import urllib.error

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import norway_company_agent.final_site_discovery as final_site  # noqa: E402
import norway_company_agent.http as http_module  # noqa: E402
from norway_company_agent.evidence import evidence  # noqa: E402
from norway_company_agent.http import FetchResult, fetch_json  # noqa: E402
from norway_company_agent.run_budget import RunBudget  # noqa: E402
from norway_company_agent.wikidata_discovery import theoretical_wikidata_lookup_requests  # noqa: E402


def website_record(*, status="available", title="Example AS", main_text="Example AS builds reliable systems. " * 8):
    value = None
    digest = None
    if status == "available":
        digest = "a" * 64
        value = {
            "requested_url": "https://example.no/",
            "final_url": "https://example.no/",
            "registered_domain": "example.no",
            "title": title,
            "description": "",
            "main_text_excerpt": main_text,
            "social_links": [],
            "structured_organisations": [],
            "content_sha256": digest,
            "extraction_state": "static_complete",
            "pages": [{"url": "https://example.no/", "title": title, "main_text_excerpt": main_text, "content_sha256": digest}],
            "crawl_errors": [],
        }
    return evidence(
        "website",
        status,
        "test_company_site",
        "https://example.no/",
        value=value,
        content_sha256=digest,
        note="fixture",
        retrieved_at="2026-09-14T00:00:00Z",
    )


def profile(*, website="example.no"):
    return {
        "organisation_number": "923609016",
        "name": "Example AS",
        "legal_form": "AS",
        "website": website,
        "municipality": "OSLO",
        "evidence": {
            "registry": evidence(
                "registry",
                "available",
                "official_registry_bulk",
                "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
                value={
                    "navn": "Example AS",
                    "epostadresse": "post@example.no" if not website else "",
                    "forretningsadresse.kommune": "OSLO",
                },
                content_sha256="b" * 64,
                source_row_key="923609016",
                retrieved_at="2026-09-14T00:00:00Z",
            ),
        },
    }


def test_run_budget_proves_1800_request_ceiling_for_100_companies():
    budget = RunBudget()
    logical = 100 * 9
    assert budget.request_charge_multiplier == 2
    assert budget.charge_requests(logical) == 1800
    assert budget.validate(logical_requests=logical, third_party_cost_usd=0.0, wall_runtime_seconds=100) == []
    assert budget.validate(logical_requests=901, third_party_cost_usd=0.0, wall_runtime_seconds=100)


def test_h1e_final_runner_proves_1802_request_ceiling_for_100_companies():
    budget = RunBudget(max_challenge_requests=1802)
    shared = theoretical_wikidata_lookup_requests(100)
    logical = 100 * 9 + shared
    assert shared == 1
    assert logical == 901
    assert budget.charge_requests(logical) == 1802
    assert budget.validate(logical_requests=logical, third_party_cost_usd=0.0, wall_runtime_seconds=100) == []


def test_h1e_final_runner_scales_shared_lookup_ceiling_in_batches():
    budget = RunBudget(max_challenge_requests=5406)
    shared = theoretical_wikidata_lookup_requests(300)
    logical = 300 * 9 + shared
    assert shared == 3
    assert logical == 2703
    assert budget.charge_requests(logical) == 5406
    assert budget.validate(logical_requests=logical, third_party_cost_usd=0.0, wall_runtime_seconds=100) == []


def test_robots_allowed_parses_url_without_local_import_scope_error(monkeypatch):
    class RobotsResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"User-agent: *\nAllow: /\n"

    class RobotsOpener:
        def __init__(self):
            self.urls = []

        def open(self, request, timeout=6.0):
            self.urls.append(request.full_url)
            return RobotsResponse()

    opener = RobotsOpener()
    monkeypatch.setattr(final_site, "assert_public_url", lambda _: None)
    monkeypatch.setattr(final_site, "BOUNDED_SAFE_OPENER", opener)

    allowed, requests = final_site._robots_allowed("https://example.no/about", 1.0)

    assert allowed is True
    assert requests == 1
    assert opener.urls == ["https://example.no/robots.txt"]


def test_verified_registry_homepage_stops_after_one_probe(monkeypatch):
    calls = []

    def fake_fetch(url, *, source_type, timeout=6.0, max_bytes=750_000):
        calls.append((url, source_type))
        return website_record(), {"requests": 2, "bytes": 100, "latencies_ms": [10]}

    monkeypatch.setattr(final_site, "fetch_bounded_homepage", fake_fetch)
    row, metrics = final_site.discover_final_website(profile())
    assessment = (row["evidence"]["website"]["value"] or {})["identity_assessment"]
    assert assessment["publishable"] is True
    assert metrics["requests"] == 2
    assert metrics["selected_source"] == "registry_website"
    assert len(calls) == 1


def test_registry_failure_plus_h1c_failure_is_bounded_to_four_logical_requests(monkeypatch):
    calls = []

    def fake_fetch(url, *, source_type, timeout=6.0, max_bytes=750_000):
        calls.append((url, source_type))
        return website_record(status="source_error"), {"requests": 2, "bytes": 0, "latencies_ms": [5]}

    monkeypatch.setattr(final_site, "fetch_bounded_homepage", fake_fetch)
    monkeypatch.setattr(
        final_site,
        "deterministic_domain_candidates",
        lambda row, max_candidates=1: {
            "eligible": True,
            "reason": "fixture",
            "candidates": [{"domain": "example.no", "url": "https://example.no/", "strategy": "fixture"}],
        },
    )
    row, metrics = final_site.discover_final_website(profile(website="registry.example.no"))
    assert metrics["requests"] == final_site.MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE == 4
    assert len(calls) == 2
    assert metrics["promoted"] is False
    assert row["evidence"]["website"]["status"] == "source_error"


def test_email_candidate_plus_h1c_candidate_is_bounded_to_four_logical_requests(monkeypatch):
    calls = []

    def fake_fetch(url, *, source_type, timeout=6.0, max_bytes=750_000):
        calls.append((url, source_type))
        return website_record(status="source_error"), {"requests": 2, "bytes": 0, "latencies_ms": [5]}

    monkeypatch.setattr(final_site, "fetch_bounded_homepage", fake_fetch)
    monkeypatch.setattr(
        final_site,
        "registry_email_domain_candidates",
        lambda row: {
            "eligible": True,
            "reason": "fixture",
            "candidates": [{"domain": "mail-example.no", "url": "mail-example.no", "source": "fixture"}],
        },
    )
    monkeypatch.setattr(
        final_site,
        "deterministic_domain_candidates",
        lambda row, max_candidates=1: {
            "eligible": True,
            "reason": "fixture",
            "candidates": [{"domain": "example.no", "url": "https://example.no/", "strategy": "fixture"}],
        },
    )
    row, metrics = final_site.discover_final_website(profile(website=""))
    assert metrics["requests"] == 4
    assert metrics["email_attempted"] is True
    assert metrics["h1c_attempted"] is True
    assert len(calls) == 2
    assert row["evidence"]["website"]["status"] == "not_found"


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps({"ok": True}).encode("utf-8")


class _RetryOnceOpener:
    def __init__(self):
        self.calls = 0

    def open(self, request, timeout=20.0):
        self.calls += 1
        if self.calls == 1:
            raise urllib.error.URLError("temporary")
        return _FakeResponse()


def test_fetch_json_reports_retry_attempt_count(monkeypatch):
    opener = _RetryOnceOpener()
    monkeypatch.setattr(http_module, "HTTP_OPENER", opener)
    monkeypatch.setattr(http_module.time, "sleep", lambda _: None)
    result = fetch_json("https://example.test/data", attempts=3)
    assert result.status == 200
    assert result.request_count == 2
    assert opener.calls == 2


def test_fetch_result_default_request_count_keeps_snapshot_compatibility():
    result = FetchResult("https://example.test", 200, 1, 2, {"ok": True})
    assert result.request_count == 1
