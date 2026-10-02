#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from norway_company_agent.v6h_subunit_contact_hook import install_subunit_contact_hint_hook  # noqa: E402


def main() -> None:
    # Install before importing the production base runner. fetch_official_modules() resolves
    # normalize_locations from its module globals at call time, so the normal BRREG subunit
    # request now retains website/email hints without creating another network request.
    install_subunit_contact_hint_hook()
    from run_signalpost_final import main as production_base_main  # noqa: WPS433

    production_base_main()


if __name__ == "__main__":
    main()
