from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_brreg_email_domain_shadow_yield.py"
spec = importlib.util.spec_from_file_location("screen_brreg_email_domain_shadow_yield", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def profile(name: str, email: str, website: str = ""):
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


def test_select_candidate_keeps_only_strong_non_generic_domain() -> None:
    exact = module.select_candidate(profile("ACME NORD AS", "post@acmenord.no"))
    assert exact is not None
    assert exact["domain"] == "acmenord.no"
    assert exact["strength"] == "exact"

    assert module.select_candidate(profile("ACME NORD AS", "post@gmail.com")) is None
    assert module.select_candidate(profile("ACME NORD AS", "post@unrelated.no")) is None


def test_strong_candidates_skip_current_verified_websites() -> None:
    profiles = {
        "111111111": {
            **profile("ALPHA BETA AS", "post@alphabeta.no"),
            "organisation_number": "111111111",
        },
        "222222222": {
            **profile("GAMMA DELTA AS", "post@gammadelta.no"),
            "organisation_number": "222222222",
        },
    }
    rows = module.strong_candidates(profiles, {"111111111"})
    assert len(rows) == 1
    assert rows[0][0] == "222222222"
    assert rows[0][2]["domain"] == "gammadelta.no"
