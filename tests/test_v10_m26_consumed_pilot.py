"""M26 in-memory-only tests. No company-page or Tavily network calls."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import run_v10_m26_consumed_pilot as pilot  # noqa: E402
from norway_company_agent.tavily_bounded_transport import SearchResult  # noqa: E402

MANIFEST = json.loads((ROOT / "evaluation" / "v10_m24_consumed_dev_20.json").read_text())
IDS = [org for group in ("m19_a", "m19_b", "m20_a")
       for org in MANIFEST["selected_per_cohort"][group]]
URL = "https://examplebedrift.no/"


def profile(org="123456789"):
    return {"organisation_number": org, "name": "EXAMPLE BEDRIFT AS", "municipality": "OSLO", "website": ""}


def frozen_profiles():
    return [profile(org) for org in IDS]


def page(org, *, url=URL, text=None, status="available"):
    body = text if text is not None else (
        f"Velkommen EXAMPLE BEDRIFT AS i Oslo. Organisasjonsnummer {org}."
    )
    return {
        "status": status,
        "source_url": url,
        "value": {
            "requested_url": URL, "final_url": url,
            "registered_domain": "examplebedrift.no",
            "title": "EXAMPLE BEDRIFT AS", "description": "",
            "identity_text_excerpt": body, "main_text_excerpt": body,
            "pages": [], "structured_organisations": [],
            "social_links": [], "content_sha256": "1234abcdef",
        }
    }


def ok_search(p, *, api_key, timeout_seconds):
    assert api_key == "FAKE_IN_MEMORY"
    assert timeout_seconds <= 8
    return SearchResult(
        status="ok_transient_candidates_only",
        logical_requests_charged=1, conservative_challenge_charge=2,
        payload={"results": [{
            "url": URL, "title": "EXAMPLE BEDRIFT AS",
            "content": f"Org {p['organisation_number']} EXAMPLE BEDRIFT AS OSLO",
            "score": 0.99, "raw_content": "PRIVATE_PROVIDER_HTML",
        }], "answer": "UNTRUSTED_GENERATED_ANSWER"}
    )


def site_fn(url, *, source_type, timeout):
    assert url == URL
    assert timeout <= 6
    assert source_type == "experiment_search_nominated_company_homepage"
    return page("123456789"), {"requests": 2}


def test_manifest_has_exact_frozen_20():
    assert len(IDS) == len(set(IDS)) == 20
    assert MANIFEST["selected_list_sha256"] == pilot.EXPECTED_SHA
    assert MANIFEST["permission_to_merge"] is False
    assert MANIFEST["live_provider_authorized"] is False


def test_preview_always_zero_requests_even_with_accidental_fake_key():
    def must_not_call(*a, **kw):
        raise AssertionError("Dry run initiated network")
    report = pilot.run_pilot(
        frozen_profiles(), live=False, api_key="FAKE_IN_MEMORY",
        search_fn=must_not_call, fetch_fn=must_not_call
    )
    assert report["attempted_companies"] == 0
    assert report["logical_requests_reserved"] == 0
    assert report["conservative_charge_reserved"] == 0
    assert report["published_company_claims"] == 0
    assert len(report["rows"]) == 20
    assert all(x["status"] == "dry_run_no_network" for x in report["rows"])


def test_live_refuses_missing_key_without_call():
    def must_not_call(*a, **kw):
        raise AssertionError("No-key run initiated network")
    try:
        pilot.run_pilot(frozen_profiles(), live=True, api_key="", search_fn=must_not_call)
    except ValueError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Missing key accepted")


def test_direct_helper_refuses_any_non_frozen_or_duplicate_company():
    for records in (
        frozen_profiles()[:-1],
        frozen_profiles() + [profile("111111111")],
        [profile("111111111") for _ in range(20)],
        frozen_profiles()[::-1],
    ):
        try:
            pilot.run_pilot(records, live=False)
        except ValueError:
            pass
        else:
            raise AssertionError("Non-frozen sequence accepted")


def test_single_search_no_site_never_publishes_claim():
    searches = []
    def fake_search(p, *, api_key, timeout_seconds):
        searches.append(p["organisation_number"])
        return SearchResult("ok_transient_candidates_only", 1, 2, {"results": []})
    item = pilot.run_one(profile(), key="FAKE_IN_MEMORY", search_fn=fake_search, fetch_fn=lambda *a, **k: 1/0)
    assert len(searches) == 1
    assert item["site_logical_requests_reserved"] == 1
    assert item["conservative_charge_reserved"] == 2
    assert item["published_claims"] == 0
    assert item["status"] == "no_candidate_qualified_for_independent_fetch"


def test_one_search_plus_one_independent_page_for_manual_review_only():
    item = pilot.run_one(profile(), key="FAKE_IN_MEMORY", search_fn=ok_search, fetch_fn=site_fn)
    assert item["status"] == "manual_exact_org_site_review_required"
    assert item["site_logical_requests_reserved"] == 3
    assert item["conservative_charge_reserved"] == 6
    assert item["published_claims"] == 0
    assert item["first_party_site_url"] == URL
    assert item["first_party_sha256"] == "1234abcdef"
    assert "UNTRUSTED" not in str(item)
    assert "PRIVATE_PROVIDER_HTML" not in str(item)


def test_independent_page_wrong_org_rejected():
    item = pilot.run_one(
        profile(), key="FAKE_IN_MEMORY", search_fn=ok_search,
        fetch_fn=lambda *a, **kw: (page("987654321"), {"requests": 2})
    )
    assert item["status"] == "first_party_identity_rejected"
    assert item["published_claims"] == 0


def test_fake_cross_domain_redirect_rejected_even_with_correct_org():
    item = pilot.run_one(
        profile(), key="FAKE_IN_MEMORY", search_fn=ok_search,
        fetch_fn=lambda *a, **kw: (
            page("123456789", url="https://parentcorp.no/"), {"requests": 2}
        )
    )
    assert item["status"] in ("cross_domain_redirect_rejected", "first_party_identity_rejected")
    assert item["published_claims"] == 0


def test_ambiguous_legal_name_location_not_enough_without_exact_org():
    item = pilot.run_one(
        profile(), key="FAKE_IN_MEMORY", search_fn=ok_search,
        fetch_fn=lambda *a, **kw: (
            page("123456789", text="EXAMPLE BEDRIFT AS opererer i Oslo."), {"requests": 2}
        )
    )
    assert item["status"] == "exact_org_number_missing_from_fetched_page"
    assert item["published_claims"] == 0


def test_over_budget_first_party_fetch_rejected():
    item = pilot.run_one(
        profile(), key="FAKE_IN_MEMORY", search_fn=ok_search,
        fetch_fn=lambda *a, **kw: (page("123456789"), {"requests": 3})
    )
    assert item["status"] == "independent_fetch_budget_violation"
    assert item["conservative_charge_reserved"] == 6


def test_invalid_key_or_rate_limit_aborts_remaining_19():
    for error in ("invalid_or_forbidden_key", "rate_limited_or_out_of_credits"):
        calls = []
        def bad(p, *, api_key, timeout_seconds):
            calls.append(p["organisation_number"])
            return SearchResult(error, 1, 2)
        report = pilot.run_pilot(
            frozen_profiles(), live=True, api_key="FAKE_IN_MEMORY", search_fn=bad
        )
        assert report["aborted"]
        assert report["attempted_companies"] == 1
        assert report["conservative_charge_reserved"] == 2
        assert len(calls) == 1
        assert report["published_company_claims"] == 0


def test_runtime_guard_blocks_all_search_requests_when_no_time_left():
    clock_values = iter([0.0, pilot.MAX_PILOT_WALL_SECONDS])
    report = pilot.run_pilot(
        frozen_profiles(), live=True, api_key="FAKE_IN_MEMORY",
        search_fn=lambda *a, **kw: 1/0, clock=lambda: next(clock_values)
    )
    assert report["aborted"] is True
    assert report["abort_reason"] == "pilot_time_guard"
    assert report["attempted_companies"] == 0


def test_20_candidate_ceiling_all_mocked_no_published_claims():
    def dynamic_site(url, *, source_type, timeout):
        return page("999999999"), {"requests": 2}
    report = pilot.run_pilot(
        frozen_profiles(), live=True, api_key="FAKE_IN_MEMORY",
        search_fn=ok_search, fetch_fn=dynamic_site
    )
    assert report["attempted_companies"] == 20
    assert report["logical_requests_reserved"] == 60
    assert report["conservative_charge_reserved"] == 120
    assert report["conservative_dev_20_charge_ceiling"] == 120
    assert report["published_company_claims"] == 0
    assert report["manually_reviewable_exact_org_sites"] == 0
    assert report["third_party_cost_usd_confirmed"] is None


def test_screenshot_balance_is_not_read_from_source_or_promoted():
    # Account state is an external observation, never a frozen code constant.
    assert not hasattr(pilot, "TAVILY_API_KEY")
    assert pilot.MAX_BATCH == 20
    assert pilot.MAX_PILOT_WALL_SECONDS == 600
