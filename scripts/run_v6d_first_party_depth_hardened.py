#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_v6d_first_party_depth as base  # noqa: E402
from norway_company_agent.verified_site_depth_hardened_v2 import (  # noqa: E402
    crawl_verified_site_depth_hardened_v2,
)


if __name__ == "__main__":
    # Reuse the existing experiment accounting/reporting path; only the crawl planner and
    # update publication filter change. Production V5 remains untouched.
    base.crawl_verified_site_depth = crawl_verified_site_depth_hardened_v2
    base.main()
