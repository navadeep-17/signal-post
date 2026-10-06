from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_etatsbasen_archive_website_reach.py"
spec = importlib.util.spec_from_file_location("screen_etatsbasen_archive_website_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_tailid_join_counts_exact_net_new_candidates_only(tmp_path: Path) -> None:
    organisations = tmp_path / "organisations.csv"
    urls = tmp_path / "urls.csv"
    _write_csv(
        organisations,
        ["tailid", "name_nb", "orgid"],
        [
            {"tailid": "1", "name_nb": "A", "orgid": "111111111"},
            {"tailid": "2", "name_nb": "B", "orgid": "222222222"},
            {"tailid": "3", "name_nb": "NO ORG", "orgid": ""},
            {"tailid": "4", "name_nb": "OTHER", "orgid": "999999999"},
        ],
    )
    _write_csv(
        urls,
        ["tailid", "url", "language"],
        [
            {"tailid": "1", "url": "https://a.example", "language": "nb"},
            {"tailid": "2", "url": "https://b.example", "language": "nb"},
            {"tailid": "2", "url": "https://b.example/en", "language": "en"},
            {"tailid": "4", "url": "https://other.example", "language": "nb"},
        ],
    )
    result = module.scan(
        organisations,
        urls,
        {"111111111", "222222222", "333333333"},
        {"111111111"},
    )
    assert result["exact_company_hits"] == 2
    assert result["website_candidate_companies"] == 2
    assert result["website_overlap_current_verified"] == 1
    assert result["website_net_new_candidates"] == 1
    assert result["post_candidate_upper_bound_website_companies"] == 2
    encoded = repr(result)
    assert "222222222" not in encoded
    assert "https://b.example" not in encoded
