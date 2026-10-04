from __future__ import annotations

from pathlib import Path
import sys

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.job_surface_signal import extract_homepage_hiring_signal


def test_explicit_af_style_count_is_active() -> None:
    soup = BeautifulSoup(
        "<section><strong>10</strong> Antall ledige stillinger i AF akkurat nå</section>",
        "lxml",
    )
    signal = extract_homepage_hiring_signal(final_url="https://www.afgruppen.no/", soup=soup)
    assert signal["active_vacancies"] is True
    assert signal["active_vacancy_count"] == 10


def test_unrelated_number_near_generic_careers_text_is_not_active() -> None:
    soup = BeautifulSoup(
        """
        <main>
          <p>47 år med lokal erfaring og trygghet.</p>
          <nav><a href='/ledige-stillinger'>Ledige stillinger</a></nav>
          <p>Her oppdaterer vi så snart det kommer ledige stillinger.</p>
        </main>
        """,
        "lxml",
    )
    signal = extract_homepage_hiring_signal(final_url="https://www.granne.no/", soup=soup)
    assert signal["active_vacancies"] is False
    assert signal["active_vacancy_count"] == 0
