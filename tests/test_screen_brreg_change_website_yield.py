from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_brreg_change_website_yield.py"
spec = importlib.util.spec_from_file_location("screen_brreg_change_website_yield", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_read_candidates_requires_unique_exact_org_and_value(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_text(
        json.dumps({"organisation_number": "935038308", "candidate": "brandsrudbil.no"}) + "\n",
        encoding="utf-8",
    )
    assert module.read_candidates(path) == [
        {"organisation_number": "935038308", "candidate": "brandsrudbil.no"}
    ]


def test_read_candidates_rejects_duplicate_org(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_text(
        "".join(
            [
                json.dumps({"organisation_number": "935038308", "candidate": "a.no"}) + "\n",
                json.dumps({"organisation_number": "935038308", "candidate": "b.no"}) + "\n",
            ]
        ),
        encoding="utf-8",
    )
    try:
        module.read_candidates(path)
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate org must be rejected")
