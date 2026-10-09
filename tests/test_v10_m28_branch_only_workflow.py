"""M28 branch-only workflow safety tests; NO network or secret accesses."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=(ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
BRANCH="experiment/v10-m28-no-main-manual-pilot"
PIN="649aa9dcb0ceecf5947d2271ee846b0dc9d76e13"


def job():
    return WORKFLOW.split("\n  experimental-consumed-20:\n", 1)[1]


def test_dispatch_is_existing_baseline_workflow_not_new_main_file():
    assert WORKFLOW.startswith("name: Baseline CI\n")
    assert "\non:\n  workflow_dispatch:\n    inputs:\n" in WORKFLOW
    assert "\n  pull_request:\n" in WORKFLOW
    assert "\n  push:\n" in WORKFLOW


def test_manual_job_only_on_exact_private_experiment_ref():
    j=job()
    assert "github.event_name == 'workflow_dispatch'" in j
    assert "github.ref == 'refs/heads/" + BRANCH + "'" in j
    assert "github.repository == 'navadeep-17/signal-post'" in j
    assert "github.ref == 'refs/heads/main'" not in j
    assert "refs/heads/release/" not in j


def test_v8_and_m26_not_dynamically_selected():
    j=job()
    assert "ref: " + PIN in j
    assert "persist-credentials: false" in j
    assert "ref: $" + "{{" not in j
    assert "inputs.branch" not in j


def test_default_zero_network_preview_and_explicit_live():
    assert "default: preview" in WORKFLOW
    assert "          - preview\n          - live" in WORKFLOW
    assert "env -u TAVILY_API_KEY uv run python" in job()
    assert "--execute-live" in job()
    assert "RUN_FROZEN_CONSUMED_20_ONLY" in job()
    for guard in ("PAYG_OFF", "FREE_CREDITS", "SERVER_SIDE"):
        assert 'test "$' + guard + '" = true' in job()
    assert 'test "$RUN_ATTEMPT" = 1' in job()


def test_repeated_dispatch_cannot_cancel_previous_credit_spending():
    assert "cancel-in-progress: $" + "{{ github.event_name != 'workflow_dispatch' }}" in WORKFLOW
    assert "group: signalpost-m28-frozen20" in job()
    assert "cancel-in-progress: false" in job()


def test_no_secrets_visible_to_baseline_or_default_preview():
    prefix=WORKFLOW.split("\n  experimental-consumed-20:\n",1)[0]
    assert "secrets.TAVILY_API_KEY" not in prefix
    j=job()
    before_live=j[:j.index("      - name: Check both secrets")]
    assert "secrets." not in before_live
    assert j.count("secrets.TAVILY_API_KEY")==2
    assert j.count("secrets.SIGNALPOST_PILOT_REPORT_KEY")==2


def test_review_artifact_always_encrypted():
    j=job()
    assert "Fernet(key).encrypt(report.read_bytes())" in j
    assert "report.unlink()" in j
    assert "retention-days: 1" in j
    assert "path: /tmp/m27-consumed-encrypted-report.fernet" in j
    assert "path: out/" not in j[j.index("      - name: Upload ONLY"):]


def test_only_previously_consumed_selection_eligible():
    j=job()
    for artifact in ("11505218381","11525046472","11525304908"):
        assert artifact in j
    assert "out/m27-preview.json" in j
    assert 'test "$MODE" = preview' in j


def test_runbook_references_cli_branch_manual_dispatch():
    doc=(ROOT / "docs/V10_M28_NO_MAIN_PILOT.md").read_text(encoding="utf-8")
    assert "gh workflow run ci.yml --ref experiment/v10-m28-no-main-manual-pilot -f mode=preview" in doc
    assert "do not merge" in doc.lower()
