#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from norway_company_agent.v6e_annual_report_hook import install_annual_report_candidate_hook  # noqa: E402


def main() -> None:
    install_annual_report_candidate_hook()
    from run_signalpost_final import main as production_base_main  # noqa: WPS433

    production_base_main()


if __name__ == "__main__":
    main()
