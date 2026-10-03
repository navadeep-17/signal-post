import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_v9_m1c_unresolved_cohort as prep


def profile(org: str):
    return {
        "organisation_number": org,
        "name": f"COMPANY {org} AS",
        "municipality": "OSLO",
        "website": "",
        "evidence": {},
    }


def publishable(row, *, url="https://example.no/", source_type="deterministic_legal_name_domain_guess"):
    row = dict(row)
    row["website"] = url
    row["evidence"] = {
        **(row.get("evidence") or {}),
        "website": {
            "status": "available",
            "source_type": source_type,
            "source_url": url,
            "value": {
                "final_url": url,
                "identity_assessment": {"status": "exact", "publishable": True, "score": 1.0},
            },
        },
    }
    return row


def test_incumbent_baseline_counts_resolved_and_unresolved(monkeypatch):
    rows = [profile("111111111"), profile("222222222"), profile("333333333")]
    monkeypatch.setattr(
        prep,
        "fetch_wikidata_website_candidates",
        lambda orgs, timeout: ({"222222222": {"url": "https://two.no/"}}, {"requests": 1, "candidate_count": 1}),
    )

    def fake_discover(row, *, wikidata_candidate, timeout):
        org = row["organisation_number"]
        if org == "111111111":
            return publishable(row, url="https://one.no/"), {"requests": 2, "bytes": 100, "selected_source": "h1c_deterministic_domain"}
        if org == "222222222" and wikidata_candidate:
            return publishable(row, url="https://two.no/", source_type="wikidata_official_website_candidate"), {
                "requests": 2,
                "bytes": 120,
                "selected_source": "wikidata_candidate",
                "wikidata_candidate_available": True,
                "wikidata_attempted": True,
                "wikidata_verified": True,
            }
        return row, {"requests": 2, "bytes": 80, "selected_source": None}

    monkeypatch.setattr(prep, "discover_final_website_with_wikidata", fake_discover)
    monkeypatch.setattr(
        prep,
        "evaluate_hyphenated_no_fallback",
        lambda row, timeout, base_site_logical_requests: (row, {"attempted": False, "verified": False, "requests_added": 0, "bytes_added": 0}),
    )

    result, metrics = prep.baseline_website_discovery(rows, site_timeout=1, wikidata_timeout=1)
    assert len(result) == 3
    assert metrics["resolved"] == 2
    assert metrics["unresolved"] == 1
    assert metrics["source_counts"] == {
        "h1c_deterministic_domain": 1,
        "none": 1,
        "wikidata_candidate": 1,
    }
    assert metrics["site_logical_requests"] == 6
    assert metrics["search_api_requests"] == 0
    assert metrics["third_party_api_cost_usd"] == 0.0


def test_h1g_can_resolve_company_without_raising_site_ceiling(monkeypatch):
    row = profile("111111111")
    monkeypatch.setattr(prep, "fetch_wikidata_website_candidates", lambda orgs, timeout: ({}, {"requests": 1}))
    monkeypatch.setattr(
        prep,
        "discover_final_website_with_wikidata",
        lambda row, wikidata_candidate, timeout: (row, {"requests": 2, "bytes": 50, "selected_source": None}),
    )

    def fake_h1g(row, *, timeout, base_site_logical_requests):
        return publishable(row, url="https://company-one.no/", source_type="deterministic_legal_name_hyphenated_no_fallback"), {
            "attempted": True,
            "verified": True,
            "requests_added": 2,
            "bytes_added": 75,
        }

    monkeypatch.setattr(prep, "evaluate_hyphenated_no_fallback", fake_h1g)
    result, metrics = prep.baseline_website_discovery([row], site_timeout=1, wikidata_timeout=1)
    assert prep._publishable_website(result[0]) is True
    assert metrics["resolved"] == 1
    assert metrics["source_counts"] == {"h1g_hyphenated_no": 1}
    assert metrics["site_logical_requests"] == prep.MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE


def test_incumbent_baseline_rejects_site_request_overrun(monkeypatch):
    row = profile("111111111")
    monkeypatch.setattr(prep, "fetch_wikidata_website_candidates", lambda orgs, timeout: ({}, {"requests": 0}))
    monkeypatch.setattr(
        prep,
        "discover_final_website_with_wikidata",
        lambda row, wikidata_candidate, timeout: (row, {"requests": prep.MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE + 1, "bytes": 0}),
    )
    monkeypatch.setattr(
        prep,
        "evaluate_hyphenated_no_fallback",
        lambda row, timeout, base_site_logical_requests: (row, {"attempted": False, "verified": False, "requests_added": 0, "bytes_added": 0}),
    )
    with pytest.raises(RuntimeError, match="site request ceiling exceeded"):
        prep.baseline_website_discovery([row], site_timeout=1, wikidata_timeout=1)


def test_prepare_selects_exact_target_from_unresolved_and_records_touched_pool(tmp_path, monkeypatch):
    organisations = tmp_path / "pool.jsonl"
    organisations.write_text(
        "".join(
            json.dumps({"organisation_number": str(100000000 + i), "evaluation_split": "m1c_pool", "sample_slice": "fresh"}) + "\n"
            for i in range(5)
        ),
        encoding="utf-8",
    )
    fake_profiles = [profile(str(100000000 + i)) for i in range(5)]
    monkeypatch.setattr(
        prep,
        "profiles_from_bulk",
        lambda path, orgs: (fake_profiles, {"selected": 5, "missing_count": 0, "registry_snapshot_sha256": "a" * 64}),
    )

    baseline_rows = [
        publishable(fake_profiles[0], url="https://resolved.no/"),
        *fake_profiles[1:],
    ]
    monkeypatch.setattr(
        prep,
        "baseline_website_discovery",
        lambda profiles, site_timeout, wikidata_timeout: (
            baseline_rows,
            {
                "companies": 5,
                "resolved": 1,
                "unresolved": 4,
                "source_counts": {"none": 4, "h1c_deterministic_domain": 1},
                "site_logical_requests": 8,
                "site_request_ceiling": 20,
                "site_bytes": 100,
                "wikidata": {"requests": 1},
                "third_party_api_cost_usd": 0.0,
                "search_api_requests": 0,
            },
        ),
    )

    baseline_out = tmp_path / "baseline.jsonl"
    unresolved_out = tmp_path / "unresolved.jsonl"
    report_out = tmp_path / "report.json"
    report = prep.prepare(
        organisations_path=organisations,
        bulk_path=tmp_path / "bulk.csv",
        baseline_profiles_path=baseline_out,
        unresolved_output_path=unresolved_out,
        report_path=report_out,
        target_unresolved=3,
        site_timeout=1,
        wikidata_timeout=1,
    )
    selected = [json.loads(line) for line in unresolved_out.read_text().splitlines() if line.strip()]
    assert len(selected) == 3
    assert all(not prep._publishable_website(row) for row in selected)
    assert report["fresh_pool_companies"] == 5
    assert report["fresh_cohort_consumed_by_this_step"] == 5
    assert report["selected_unresolved"] == 3
    assert report["model_or_search_called"] is False
    assert len(baseline_out.read_text().splitlines()) == 5


def test_prepare_fails_before_model_search_when_pool_has_too_few_unresolved(tmp_path, monkeypatch):
    organisations = tmp_path / "pool.jsonl"
    organisations.write_text(json.dumps({"organisation_number": "111111111"}) + "\n", encoding="utf-8")
    one = profile("111111111")
    monkeypatch.setattr(prep, "profiles_from_bulk", lambda path, orgs: ([one], {"selected": 1, "missing_count": 0}))
    monkeypatch.setattr(
        prep,
        "baseline_website_discovery",
        lambda profiles, site_timeout, wikidata_timeout: ([publishable(one)], {"resolved": 1, "unresolved": 0}),
    )
    with pytest.raises(RuntimeError, match="need 1"):
        prep.prepare(
            organisations_path=organisations,
            bulk_path=tmp_path / "bulk.csv",
            baseline_profiles_path=tmp_path / "baseline.jsonl",
            unresolved_output_path=tmp_path / "unresolved.jsonl",
            report_path=tmp_path / "report.json",
            target_unresolved=1,
            site_timeout=1,
            wikidata_timeout=1,
        )
