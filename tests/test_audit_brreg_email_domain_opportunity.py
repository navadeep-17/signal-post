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


def test_email_domain_parser():
    assert module._email_domain("post@Example.NO") == "example.no"
    assert module._email_domain("invalid") is None


def test_audit_counts_without_retaining_values(tmp_path: Path):
    path = tmp_path / "out.jsonl.gz"
    rows = []
    for i in range(1000):
        org = f"{i:09d}"
        claims = [_claim("legal_name", f"COMPANY {i} AS")]
        if i == 0:
            claims += [
                _claim("registered_contact_email", "post@company0.no"),
                _claim("official_website", "https://company0.no/"),
            ]
        elif i == 1:
            claims += [_claim("registered_contact_email", "post@company1.no")]
        elif i == 2:
            claims += [_claim("registered_contact_email", "owner@gmail.com")]
        rows.append({"organisation_number": org, "claims": claims})
    with gzip.open(path, "wt", encoding="utf-8") as h:
        for row in rows:
            h.write(json.dumps(row) + "\n")

    report = module.audit(path)
    assert report["companies"] == 1000
    assert report["current_verified_website_companies"] == 1
    assert report["registered_contact_email_companies"] == 3
    assert report["missing_website_with_registered_email"] == 2
    assert report["nongeneric_email_domain_candidate_companies"] == 1
    assert report["exact_multi_acronym_candidate_companies"] == 1
    encoded = repr(report)
    assert "post@company1.no" not in encoded
    assert "000000001" not in encoded
