from __future__ import annotations

import csv
import gzip
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_peppol_website_overlap.py"
spec = importlib.util.spec_from_file_location("screen_peppol_website_overlap", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _write_targets(path: Path) -> None:
    rows = [
        {"organisation_number": "111111111"},
        {"organisation_number": "222222222"},
        {"organisation_number": "333333333"},
        {"organisation_number": "444444444"},
    ]
    path.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")


def _write_output(path: Path) -> None:
    rows = [
        {
            "organisation_number": "111111111",
            "claims": [{"field": "official_website", "availability": "available", "value": "https://one.test"}],
        },
        {"organisation_number": "222222222", "claims": []},
        {
            "organisation_number": "333333333",
            "claims": [{"field": "official_website", "availability": "unavailable", "value": None}],
        },
        {"organisation_number": "444444444", "claims": []},
    ]
    with gzip.open(path, "wt", encoding="utf-8") as h:
        for row in rows:
            h.write(json.dumps(row) + "\n")


def _write_peppol(path: Path) -> None:
    cols = ["Participant ID", "Websites", "Contact email", "Names (per-row)"]
    rows = [
        {
            "Participant ID": "iso6523-actorid-upis::0192:111111111",
            "Websites": "https://one-peppol.test",
            "Contact email": "secret1@example.test",
            "Names (per-row)": "ONE AS",
        },
        {
            "Participant ID": "iso6523-actorid-upis::0192:222222222",
            "Websites": "https://two.test",
            "Contact email": "secret2@example.test",
            "Names (per-row)": "TWO AS",
        },
        {
            "Participant ID": "iso6523-actorid-upis::0192:333333333",
            "Websites": "",
            "Contact email": "secret3@example.test",
            "Names (per-row)": "THREE AS",
        },
    ]
    with gzip.open(path, "wt", encoding="iso-8859-1", newline="") as h:
        w = csv.DictWriter(h, fieldnames=cols, delimiter=";")
        w.writeheader()
        w.writerows(rows)


def test_compare_reports_only_aggregate_overlap(tmp_path: Path) -> None:
    targets = tmp_path / "targets.jsonl"
    output = tmp_path / "output.jsonl.gz"
    peppol = tmp_path / "peppol.csv.gz"
    _write_targets(targets)
    _write_output(output)
    _write_peppol(peppol)

    target_orgs = module.read_target_orgs(targets)
    report = module.compare(peppol, output, target_orgs)

    assert report["current_verified_website_companies"] == 1
    assert report["peppol_exact_participant_companies"] == 3
    assert report["peppol_website_candidate_companies"] == 2
    assert report["peppol_website_overlap_current_verified"] == 1
    assert report["peppol_website_net_new_candidates"] == 1
    assert report["post_candidate_upper_bound_website_companies"] == 2
    encoded = repr(report)
    assert "111111111" not in encoded
    assert "https://two.test" not in encoded
    assert "secret2@example.test" not in encoded
