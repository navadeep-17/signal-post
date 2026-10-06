from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_brreg_email_domain_opportunity.py"
spec = importlib.util.spec_from_file_location("audit_brreg_email_domain_opportunity", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _claim(field, value, availability="available"):
    return {"field": field, "availability": availability, "value": value}


def test_email_domains():
    assert module._email_domains("post@Example.NO; x@other.no") == ["example.no", "other.no"]
    assert module._email_domains("invalid") == []


def test_audit_counts_archived_registry_email_without_retaining_values(tmp_path: Path):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    profile_path = profiles / "profiles.jsonl"
    output = tmp_path / "output.jsonl.gz"

    profile_rows = []
    output_rows = []
    for i in range(1000):
        org = f"{i:09d}"
        profile = {
            "organisation_number": org,
            "name": f"COMPANY {i} AS",
            "evidence": {"registry": {"value": {}}},
        }
        claims = [_claim("legal_name", f"COMPANY {i} AS")]
        if i == 0:
            profile["evidence"]["registry"]["value"]["epostadresse"] = "post@company0.no"
            claims.append(_claim("official_website", "https://company0.no/"))
        elif i == 1:
            profile["evidence"]["registry"]["value"]["epostadresse"] = "post@company1.no"
        elif i == 2:
            profile["evidence"]["registry"]["value"]["epostadresse"] = "owner@gmail.com"
        profile_rows.append(profile)
        output_rows.append({"organisation_number": org, "claims": claims})

    profile_path.write_text(
        "".join(json.dumps(x) + "\n" for x in profile_rows),
        encoding="utf-8",
    )
    with gzip.open(output, "wt", encoding="utf-8") as h:
        for row in output_rows:
            h.write(json.dumps(row) + "\n")

    report = module.audit(profiles, output)
    assert report["companies"] == 1000
    assert report["current_verified_website_companies"] == 1
    assert report["registered_contact_email_companies"] == 3
    assert report["missing_website_with_registered_email"] == 2
    assert report["nongeneric_email_domain_candidate_companies"] == 1
    assert report["exact_multi_acronym_candidate_companies"] == 1
    encoded = repr(report)
    assert "post@company1.no" not in encoded
    assert "000000001" not in encoded
