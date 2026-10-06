from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_site_unlock import audit_new_verified_site_unlock  # noqa: E402


def ev(eid: str, url: str = "https://example.no/") -> dict:
    return {
        "id": eid,
        "source_url": url,
        "retrieved_at": "2026-10-06T00:00:00Z",
        "content_sha256": "a" * 64,
        "claim_span": "fixture",
    }


def claim(field: str, eid: str, value: str = "x") -> dict:
    return {
        "field": field,
        "availability": "available",
        "value": value,
        "evidence_ids": [eid],
    }


def row(org: str, claims: list[dict], evidence: list[dict]) -> dict:
    return {
        "organisation_number": org,
        "claims": claims,
        "evidence": evidence,
        "errors": [],
        "operations": {"requests": 1, "runtime_ms": 1, "third_party_cost_usd": 0.0},
    }


def test_new_site_reports_downstream_company_family_edges() -> None:
    baseline = [
        row("111111111", [], []),
        row("222222222", [claim("official_website", "old")], [ev("old", "https://old.no/")]),
    ]
    challenger = [
        row(
            "111111111",
            [
                claim("official_website", "web", "https://example.no/"),
                claim("external.profile_handle", "social", "https://linkedin.com/company/example"),
                claim("external.contact_email", "mail", "post@example.no"),
            ],
            [ev("web"), ev("social"), ev("mail")],
        ),
        row("222222222", [claim("official_website", "old")], [ev("old", "https://old.no/")]),
    ]

    report = audit_new_verified_site_unlock(baseline, challenger)
    assert report["new_verified_website_companies"] == 1
    assert report["lost_verified_website_companies"] == 0
    assert report["net_new_company_family_edges_from_new_sites"] == 2
    audit = report["new_site_audit_rows"][0]
    assert audit["organisation_number"] == "111111111"
    assert audit["unlocked_families"] == ["social", "external_contact"]
    assert audit["all_relevant_evidence_hashed_and_timestamped"] is True


def test_lost_site_is_never_silently_ignored() -> None:
    baseline = [row("111111111", [claim("official_website", "web")], [ev("web")])]
    challenger = [row("111111111", [], [])]
    report = audit_new_verified_site_unlock(baseline, challenger)
    assert report["new_verified_website_companies"] == 0
    assert report["lost_verified_website_companies"] == 1
    assert report["lost_verified_website_organisation_numbers"] == ["111111111"]


def test_missing_hash_requires_manual_followup() -> None:
    broken = ev("web")
    broken["content_sha256"] = ""
    report = audit_new_verified_site_unlock(
        [row("111111111", [], [])],
        [row("111111111", [claim("official_website", "web")], [broken])],
    )
    assert report["new_site_audit_rows"][0]["all_relevant_evidence_hashed_and_timestamped"] is False
