from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.candidate_ranking import (  # noqa: E402
    FEATURE_NAMES,
    ML_RANKER_ID,
    MODEL_SCHEMA,
    RULES_RANKER_ID,
    generate_candidate_set,
    rank_candidates,
    ranked_probe_plan,
)


def profile(name="FJORD DATA SERVICE AS", municipality="OSLO", website="", email="post@fjorddata.no"):
    return {
        "organisation_number": "123456789",
        "name": name,
        "municipality": municipality,
        "website": website,
        "evidence": {
            "registry": {
                "status": "available",
                "value": {
                    "epostadresse": email,
                    "hjemmeside": website,
                    "forretningsadresse.postnummer": "0150",
                    "forretningsadresse.poststed": "OSLO",
                },
            }
        },
    }


def neutral_model():
    return {
        "schema": MODEL_SCHEMA,
        "feature_names": FEATURE_NAMES,
        "intercept": 0.0,
        "weights": {name: 0.0 for name in FEATURE_NAMES},
        "means": {name: 0.0 for name in FEATURE_NAMES},
        "scales": {name: 1.0 for name in FEATURE_NAMES},
    }


def test_candidate_generation_is_bounded_deduplicated_and_zero_cost():
    candidates = generate_candidate_set(profile())
    domains = [row["domain"] for row in candidates]
    assert len(domains) == len(set(domains))
    assert len(domains) <= 12
    assert "fjorddata.no" in domains
    assert "fjorddataservice.no" in domains
    assert "fjord-data-service.no" in domains
    assert "fjorddataservice.com" in domains
    assert "fds.no" in domains
    assert all(row["url"].startswith("https://") for row in candidates)


def test_both_rankers_consume_exact_same_candidate_set():
    row = profile()
    candidates = generate_candidate_set(row)
    rules = rank_candidates(row, candidates, ranker_id=RULES_RANKER_ID)
    ml = rank_candidates(row, candidates, ranker_id=ML_RANKER_ID, model=neutral_model())
    assert {item["domain"] for item in rules} == {item["domain"] for item in ml}
    assert {item["strategy"] for item in rules} == {item["strategy"] for item in ml}
    assert all(item["ranker_id"] == RULES_RANKER_ID for item in rules)
    assert all(item["ranker_id"] == ML_RANKER_ID for item in ml)


def test_rules_ranker_prefers_official_registry_email_domain_over_guesses():
    row = profile()
    candidates = generate_candidate_set(row)
    ranked = rank_candidates(row, candidates, ranker_id=RULES_RANKER_ID)
    assert ranked[0]["domain"] == "fjorddata.no"
    assert ranked[0]["strategy"] == "registry_email_domain"


def test_safe_acronym_is_not_generated_for_two_token_or_single_token_names():
    two = {row["strategy"] for row in generate_candidate_set(profile(name="FJORD DATA AS"))}
    one = {row["strategy"] for row in generate_candidate_set(profile(name="SAFE AS"))}
    assert "safe_acronym_no" not in two
    assert "safe_acronym_no" not in one


def test_municipality_variants_are_limited_to_short_names():
    short = {row["strategy"] for row in generate_candidate_set(profile(name="NORD BYGG AS", municipality="OSLO"))}
    long = {row["strategy"] for row in generate_candidate_set(profile(name="NORD BYGG SERVICE AS", municipality="OSLO"))}
    assert "legal_compact_municipality_no" in short
    assert "legal_compact_municipality_no" not in long


def test_probe_plan_excludes_domains_already_attempted_by_v5():
    row = profile(email="post@fjorddata.no")
    row["evidence"]["website_email_discovery"] = {
        "status": "not_found",
        "value": {"candidate_domain": "fjorddata.no"},
    }
    plan = ranked_probe_plan(row, ranker_id=RULES_RANKER_ID, max_probes=2)
    assert "fjorddata.no" in plan["attempted_domains"]
    assert all(item["domain"] != "fjorddata.no" for item in plan["probe_candidates"])
    assert len(plan["probe_candidates"]) <= 2


def test_ranker_metadata_is_nomination_only_not_identity_evidence():
    plan = ranked_probe_plan(profile(), ranker_id=RULES_RANKER_ID, max_probes=1)
    candidate = plan["probe_candidates"][0]
    assert "identity_assessment" not in candidate
    assert "publishable" not in candidate
    assert plan["policy"].startswith("Rank scores nominate network probes only")
