from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "v9-m1c-model-search-qualification.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_m1c_qualification_workflow_is_manual_only():
    text = workflow_text()
    assert "on:\n  workflow_dispatch:" in text
    # No automatic event may consume a fresh cohort or external API budget.
    trigger_block = text.split("permissions:", 1)[0]
    assert "\n  push:" not in trigger_block
    assert "\n  pull_request:" not in trigger_block
    assert "\n  schedule:" not in trigger_block


def test_m1c_requires_explicit_builderr_confirmation_and_nonzero_budget():
    text = workflow_text()
    assert "BUILDR_PROVIDER_AND_BUDGET_CONFIRMED" in text
    assert "default: 'NOT_CONFIRMED'" in text
    assert "default: 'UNCONFIRMED'" in text
    assert "test '${{ inputs.confirmation }}' = 'BUILDR_PROVIDER_AND_BUDGET_CONFIRMED'" in text
    assert "test '${{ inputs.model }}' != 'UNCONFIRMED'" in text
    assert "assert parsed['max_external_cost_usd'] > 0" in text


def test_m1c_freshness_and_manual_audit_artifacts_are_pinned():
    text = workflow_text()
    assert "HISTORICAL_EXCLUDE_SHA256: 5f5560498fa22a15a24a74ab05ebbba820cc20cf9a164cd5fa007ee898deb17c" in text
    assert "CAREERS_TRANSFER_SHA256: 1d50c3eddb91004c6413ffd263e25b166b9ec822cceae9c9bb8c0908edd997b3" in text
    assert "assert len(rows)==8020 and len(set(orgs))==8020" in text
    assert "--count 40 --seed 20261016" in text
    assert "--target-unresolved 20" in text
    assert "--limit 20" in text
    assert "manual-accepted-site-review.jsonl" in text


def test_m1c_provider_raw_output_is_not_an_artifact():
    text = workflow_text()
    artifact_block = text.split("- name: Upload qualification evidence without raw provider output", 1)[1]
    assert "manual-accepted-site-review.jsonl" in artifact_block
    assert "model-search-output.jsonl" in artifact_block
    # The qualified output is destination-page evidence; raw provider payload/text must never be named or uploaded.
    assert "raw-provider" not in artifact_block.casefold()
    assert "provider-response" not in artifact_block.casefold()
