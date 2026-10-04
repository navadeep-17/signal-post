from __future__ import annotations

from pathlib import Path
import sys

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.job_surface_signal import extract_job_listing_candidates


def test_wrapped_card_title_uses_matching_role_slug_prefix() -> None:
    html = """
    <article>
      <a href='/karriere/ledige-stillinger/2026/09/bedriftslege/'>
        Bedriftslege Oslo AF Gruppen, AF Gruppen Konsern 18.10.2026
      </a>
    </article>
    """
    rows = extract_job_listing_candidates(
        final_url="https://www.afgruppen.no/karriere/ledige-stillinger/",
        soup=BeautifulSoup(html, "lxml"),
        structured={},
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "Bedriftslege"
    assert rows[0]["deadline_raw"] == "18.10.2026"


def test_slug_mismatch_does_not_rewrite_anchor_title() -> None:
    html = """
    <article>
      <a href='/karriere/ledige-stillinger/2026/09/bedriftslege/'>
        Seniorlege Oslo AF Gruppen 18.10.2026
      </a>
    </article>
    """
    rows = extract_job_listing_candidates(
        final_url="https://www.afgruppen.no/karriere/ledige-stillinger/",
        soup=BeautifulSoup(html, "lxml"),
        structured={},
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "Seniorlege Oslo AF Gruppen 18.10.2026"
