from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_email_domain import (  # noqa: E402
    ranked_strong_registry_email_domain_candidates,
    select_strong_registry_email_domain_candidate,
)


def profile(name: str, email: str, *, website: str = "") -> dict:
    return {
        "organisation_number": "999999999",
        "name": name,
        "website": website,
        "evidence": {
            "registry": {
                "status": "available",
                "value": {"epostadresse": email},
            }
        },
    }


def test_exact_legal_name_domain_is_selected() -> None:
    selected = select_strong_registry_email_domain_candidate(
        profile("ACME NORD AS", "post@acmenord.no")
    )
    assert selected is not None
    assert selected["domain"] == "acmenord.no"
    assert selected["strength"] == "exact"


def test_acronym_domain_is_strong_but_unrelated_domain_is_not() -> None:
    ranked = ranked_strong_registry_email_domain_candidates(
        profile("MASTER SURGERY SYSTEMS AS", "post@unrelated.no;hei@mss.no")
    )
    assert len(ranked) == 1
    assert ranked[0]["domain"] == "mss.no"
    assert ranked[0]["strength"] == "acronym"


def test_unrelated_nongeneric_email_domain_does_not_consume_v9_slot() -> None:
    assert (
        select_strong_registry_email_domain_candidate(
            profile("ACME NORD AS", "post@accountingpartner.no")
        )
        is None
    )


def test_consumer_mailbox_and_existing_registry_site_are_ineligible() -> None:
    assert select_strong_registry_email_domain_candidate(
        profile("ACME NORD AS", "post@gmail.com")
    ) is None
    assert select_strong_registry_email_domain_candidate(
        profile("ACME NORD AS", "post@acmenord.no", website="https://acme.no/")
    ) is None


def test_candidate_ranking_is_deterministic_and_prefers_exact() -> None:
    ranked = ranked_strong_registry_email_domain_candidates(
        profile("MASTER SURGERY SYSTEMS AS", "post@mss.no;hei@mastersurgerysystems.no")
    )
    assert [item["strength"] for item in ranked] == ["exact", "acronym"]
    assert ranked[0]["domain"] == "mastersurgerysystems.no"
