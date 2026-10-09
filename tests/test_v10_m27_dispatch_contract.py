"""CI-only regression checks for the M27 manual dispatcher.

No GitHub secret is read; only repository text is inspected.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / ".github/workflows/v10-m27-manual-consumed-pilot.yml"
DOC = ROOT / "docs/V10_M27_MANUAL_DISPATCH_RUNBOOK.md"
M26_SHA = "649aa9dcb0ceecf5947d2271ee846b0dc9d76e13"


def workflow():
    return FILE.read_text(encoding="utf-8")


def test_dispatch_only_no_automatic_triggers():
    s = workflow()
    assert "\non:\n  workflow_dispatch:\n" in s
    for trigger in ("push", "pull_request", "schedule", "workflow_run",
                    "repository_dispatch", "workflow_call"):
        assert "\n  " + trigger + ":" not in s


def test_default_safe_preview():
    s = workflow()
    assert "type: choice\n        default: preview" in s
    assert "          - preview\n          - live" in s
    assert "env -u TAVILY_API_KEY uv run python" in s
    assert "'attempted_companies']==0" in s
    assert "'conservative_charge_reserved']==0" in s


def test_pinned_immutable_code_and_main_only():
    s = workflow()
    assert "github.ref == 'refs/heads/main'" in s
    assert "github.repository == 'navadeep-17/signal-post'" in s
    assert "ref: " + M26_SHA in s
    assert "persist-credentials: false" in s
    assert "ref: $" + "{{" not in s
    assert "inputs.branch" not in s


def test_live_requires_multiple_positive_confirmations():
    s = workflow()
    assert "RUN_FROZEN_CONSUMED_20_ONLY" in s
    assert "test \"$RUN_ATTEMPT\" = 1" in s
    for k in ("PAYG_OFF", "FREE_CREDITS", "SERVER_SIDE"):
        assert "test \"$" + k + "\" = true" in s
    for key in ("confirm_pay_as_you_go_off", "confirm_at_least_20_credits",
                "confirm_server_side_only"):
        assert key in s


def test_read_only_nonconcurrent():
    s = workflow()
    assert "  contents: read" in s
    assert "  actions: read" in s
    assert "cancel-in-progress: false" in s
    assert "group: signalpost-m27-consumed-pilot" in s


def test_secrets_unavailable_to_preview_and_regression_steps():
    s = workflow()
    before_live = s[:s.index("      - name: Check both secrets")]
    assert "secrets." not in before_live
    assert "uv run --with pytest" in before_live
    assert s.count("secrets.TAVILY_API_KEY") == 2
    assert s.count("secrets.SIGNALPOST_PILOT_REPORT_KEY") == 2
    assert "echo \"$TAVILY_API_KEY\"" not in s


def test_encrypted_artifact_only():
    s = workflow()
    assert "Fernet(key).encrypt(report.read_bytes())" in s
    assert "report.unlink()" in s
    assert "retention-days: 1" in s
    assert "name: m27-consumed-encrypted-manual-review" in s
    assert "path: /tmp/m27-consumed-encrypted-report.fernet" in s
    artifact_section = s[s.index("      - name: Upload ONLY"):]
    assert "path: out/" not in artifact_section


def test_frozen_20_source_only_and_live_run_confirm_flags():
    s = workflow()
    for id in ("11505218381", "11525046472", "11525304908"):
        assert id in s
    for flag in ("--execute-live", "--confirm-pay-as-you-go-off",
                 "--confirm-credits-at-least-20", "--confirm-server-side-use"):
        assert flag in s


def test_runbook_warns_no_button_until_default_merge():
    s = DOC.read_text(encoding="utf-8")
    assert "default branch" in s.lower()
    assert "SIGNALPOST_PILOT_REPORT_KEY" in s
    assert "password manager" in s
    assert "TAVILY_API_KEY" in s
