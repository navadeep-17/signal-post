from __future__ import annotations

import csv
import gzip
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_peppol_candidate_verification_yield.py"
spec = importlib.util.spec_from_file_location("screen_peppol_candidate_verification_yield", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _write_export(path: Path) -> None:
    fields = ["Participant ID", "Websites", "Contact email", "Names (per-row)"]
    rows = [
        {
            "Participant ID": "iso6523-actorid-upis::0192:111111111",
            "Websites": "https://already.example",
            "Contact email": "private@example.test",
            "Names (per-row)": "ALREADY AS",
        },
        {
            "Participant ID": "iso6523-actorid-upis::0192:222222222",
            "Websites": "https://b.example\nhttps://a.example",
            "Contact email": "private2@example.test",
            "Names (per-row)": "CANDIDATE AS",
        },
        {
            "Participant ID": "iso6523-actorid-upis::9908:333333333",
            "Websites": "https://wrong.example",
            "Contact email": "private3@example.test",
            "Names (per-row)": "WRONG AS",
        },
    ]
    with gzip.open(path, "wt", encoding="iso-8859-1", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def test_collects_only_net_new_exact_0192_and_retains_no_contact_data(tmp_path: Path) -> None:
    export = tmp_path / "peppol.csv.gz"
    _write_export(export)
    companies = {
        "111111111": {"organisation_number": "111111111", "name": "ALREADY AS"},
        "222222222": {"organisation_number": "222222222", "name": "CANDIDATE AS"},
        "333333333": {"organisation_number": "333333333", "name": "WRONG AS"},
    }
    result = module.collect_net_new_candidates(export, companies, {"111111111"})
    assert result == {"222222222": "https://a.example/"}
    assert "private2@example.test" not in repr(result)
