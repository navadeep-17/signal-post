from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_brreg_live_website_gap.py"
spec = importlib.util.spec_from_file_location("audit_brreg_live_website_gap", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def profile(org: str, bulk: str, live: str):
    return {
        "organisation_number": org,
        "website": bulk or None,
        "evidence": {
            "registry_live": {
                "status": "available",
                "value": {"website": live or None},
            }
        },
    }


def test_audit_distinguishes_same_changed_and_live_only() -> None:
    profiles = {
        "111111111": profile("111111111", "https://same.no/", "same.no"),
        "222222222": profile("222222222", "old.no", "new.no"),
        "333333333": profile("333333333", "", "live-only.no"),
        "444444444": profile("444444444", "bulk-only.no", ""),
    }
    result = module.audit(profiles, set())
    assert result["unresolved_live_website_same_as_profile"] == 1
    assert result["unresolved_live_website_changed_from_profile"] == 1
    assert result["unresolved_live_website_only_no_profile_website"] == 1
    assert result["unresolved_profile_website_but_no_live_website"] == 1
    assert result["genuinely_new_live_website_candidate_companies"] == 2


def test_verified_company_is_not_a_new_candidate() -> None:
    profiles = {
        "111111111": profile("111111111", "old.no", "new.no"),
    }
    result = module.audit(profiles, {"111111111"})
    assert result["genuinely_new_live_website_candidate_companies"] == 0
