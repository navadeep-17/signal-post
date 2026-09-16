#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

PATH = Path("scripts/run_signalpost_final.py")
text = PATH.read_text(encoding="utf-8")

replacements = [
    (
        "from norway_company_agent.company_site_social import attach_company_site_social_observations  # noqa: E402\n",
        "from norway_company_agent.company_site_social import attach_company_site_social_observations  # noqa: E402\n"
        "from norway_company_agent.registry_workforce import attach_registry_workforce_observations  # noqa: E402\n",
    ),
    (
        "from norway_company_agent.external_contract import (  # noqa: E402\n"
        "    project_contact_email_observations,\n"
        "    project_profile_handle_observations,\n"
        ")\n"
        "from norway_company_agent.external_footprint import validate_observation  # noqa: E402\n",
        "from norway_company_agent.external_contract import (  # noqa: E402\n"
        "    project_contact_email_observations,\n"
        "    project_profile_handle_observations,\n"
        ")\n"
        "from norway_company_agent.external_footprint import validate_observation  # noqa: E402\n"
        "from norway_company_agent.workforce_contract import project_workforce_observations  # noqa: E402\n",
    ),
    (
        "    attach_company_site_social_observations(profile)\n"
        "    attach_company_site_contact_email_observations(profile)\n",
        "    attach_company_site_social_observations(profile)\n"
        "    attach_company_site_contact_email_observations(profile)\n"
        "    attach_registry_workforce_observations(profile)\n",
    ),
    (
        "        contract = project_profile_handle_observations(contract, envelope[\"profile\"])\n"
        "        projected.append(project_contact_email_observations(contract, envelope[\"profile\"]))\n",
        "        contract = project_profile_handle_observations(contract, envelope[\"profile\"])\n"
        "        contract = project_contact_email_observations(contract, envelope[\"profile\"])\n"
        "        projected.append(project_workforce_observations(contract, envelope[\"profile\"]))\n",
    ),
    (
        "            \"company_page_contact_email_extraction_enabled\": True,\n"
        "            \"social_platform_requests\": 0,\n",
        "            \"company_page_contact_email_extraction_enabled\": True,\n"
        "            \"registry_workforce_snapshot_enabled\": True,\n"
        "            \"registry_workforce_network_requests\": 0,\n"
        "            \"social_platform_requests\": 0,\n",
    ),
]

for before, after in replacements:
    count = text.count(before)
    if count != 1:
        raise SystemExit(f"Expected exactly one runner integration anchor, found {count}: {before[:100]!r}")
    text = text.replace(before, after, 1)

PATH.write_text(text, encoding="utf-8")
print("Applied H2e zero-request registry workforce integration to scripts/run_signalpost_final.py")
