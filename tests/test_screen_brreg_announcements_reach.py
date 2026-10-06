from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_brreg_announcements_reach.py"
spec = importlib.util.spec_from_file_location("screen_brreg_announcements_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_parse_inherits_date_and_exact_org(tmp_path: Path) -> None:
    html = """
    <table>
      <tr><td>Dato</td><td></td><td>01.10.2026</td></tr>
      <tr><td></td><td>ACME AS</td><td></td><td>123 456 789</td><td></td><td>Endring</td><td></td></tr>
      <tr><td></td><td>OTHER AS</td><td></td><td>987654321</td><td></td><td>Nyregistrering</td><td></td></tr>
    </table>
    """
    p = tmp_path / "day.html"
    p.write_bytes(html.encode("iso-8859-1"))
    rows = module.parse_announcement_html(p)
    assert len(rows) == 2
    assert rows[0]["organisation_number"] == "123456789"
    assert rows[0]["announcement_date"] == "01.10.2026"
    assert rows[0]["type_candidate"] == "Endring"


def test_screen_counts_net_new_vs_current_change(tmp_path: Path) -> None:
    html = """
    <table>
      <tr><td>01.10.2026</td></tr>
      <tr><td>A</td><td>111111111</td><td>Endring</td></tr>
      <tr><td>B</td><td>222222222</td><td>Nyregistrering</td></tr>
    </table>
    """
    p = tmp_path / "day.html"
    p.write_text(html, encoding="utf-8")
    report, audit = module.screen([p], {"111111111", "222222222", "333333333"}, {"111111111"})
    assert report["exact_target_companies"] == 2
    assert report["overlap_current_registry_change"] == 1
    assert report["net_new_vs_current_registry_change"] == 1
    assert len(audit) == 2


def test_current_registry_change_index(tmp_path: Path) -> None:
    p = tmp_path / "out.jsonl.gz"
    rows = [
        {
            "organisation_number": "111111111",
            "claims": [{"field": "official_registry_change", "availability": "available"}],
        },
        {"organisation_number": "222222222", "claims": []},
    ]
    with gzip.open(p, "wt", encoding="utf-8") as h:
        for row in rows:
            h.write(json.dumps(row) + "\n")
    assert module.current_registry_change_orgs(p, {"111111111", "222222222"}) == {"111111111"}
