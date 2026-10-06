from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_retained_profile_field_inventory.py"
spec = importlib.util.spec_from_file_location("audit_retained_profile_field_inventory", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_inventory_keeps_counts_but_not_raw_values(tmp_path: Path) -> None:
    profiles = [
        {
            "organisation_number": "111111111",
            "name": "SECRET ONE AS",
            "evidence": {
                "website": {
                    "status": "available",
                    "value": {
                        "title": "Secret title",
                        "description": "Secret description",
                        "structured_organisations": [{"telephone": "99999999"}],
                    },
                }
            },
            "external_observations": [{"contact_email": "secret@example.test"}],
        },
        {
            "organisation_number": "222222222",
            "name": "SECRET TWO AS",
            "evidence": {
                "website": {
                    "status": "available",
                    "value": {
                        "title": "Other title",
                        "description": "",
                        "structured_organisations": [],
                    },
                }
            },
            "external_observations": [],
        },
    ]

    out = tmp_path / "out.jsonl.gz"
    with gzip.open(out, "wt", encoding="utf-8") as h:
        for p in profiles:
            h.write(
                json.dumps(
                    {
                        "organisation_number": p["organisation_number"],
                        "claims": [{"field": "official_website", "availability": "available", "value": "x"}],
                        "canonical_facts": [{"type": "website", "availability": "available"}],
                        "canonical_profile": {"data_areas": {"company_website": True}},
                    }
                )
                + "\n"
            )

    report = module.audit(profiles, out, min_companies=1)
    by_path = {row["path"]: row for row in report["retained_paths"]}
    assert by_path["evidence.website.status"]["companies"] == 2
    assert by_path["evidence.website.value.structured_organisations"]["companies"] == 1
    assert not any(path.startswith("external_observations") for path in by_path)

    encoded = json.dumps(report)
    assert "SECRET ONE AS" not in encoded
    assert "secret@example.test" not in encoded
    assert "99999999" not in encoded
    assert "Secret description" not in encoded
