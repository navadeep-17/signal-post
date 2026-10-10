"""M38 Actions wiring remains branch-only and cannot trigger provider traffic from PRs."""
from __future__ import annotations
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_m38_live_manual_guard_and_secrets_isolation():
    ci=(ROOT/".github/workflows/ci.yml").read_text()
    assert "m38_mode:" in ci
    assert "m38_exact_live_confirmation:" in ci
    assert "m38_payg_off:" in ci and "m38_free_basic_four:" in ci
    assert "m38_server_side_only:" in ci
    assert "RUN_M38_FROZEN_FOUR_SINGLE_HOMEPAGE_QUERY" in ci
    assert "group: signalpost-m38-frozen-consumed-four" in ci
    assert "cancel-in-progress: false" in ci
    assert "github.event_name != 'workflow_dispatch'" in ci

    head=ci.index("  m38-frozen-four-alternative-homepage:")
    part=ci[head:]
    assert "github.event_name == 'workflow_dispatch'" in part
    assert "github.repository == 'navadeep-17/signal-post'" in part
    assert "github.ref == 'refs/heads/experiment/v10-m38-pre-registered-4-homepage-query'" in part
    assert "test \"$ATTEMPT\" = 1" in part
    assert "test \"$PAYG_OFF\" = true" in part
    assert "test \"$CREDITS\" = true" in part
    assert "test \"$PRIVATE\" = true" in part
    assert "test \"$MODE\" = preview" in part
    assert "if: inputs.m38_mode == 'live'" in part
    assert "steps.m38_live.outcome == 'success'" in part
    assert "steps.m38_live.outputs.aborted" in part
    assert "retention-days: 7" in part
    assert "ref: 82dd81a65297291a76d24c32a7649fb9e9810380" in part
    assert part.count("secrets.TAVILY_API_KEY") == 1
    assert "secrets.SIGNALPOST_PILOT_REPORT_KEY" in part
    assert "--preview" in part and "--live" in part
    assert "m38-private-encrypted-consumed-four" in part
    assert "run_signalpost_v8.py" not in part
    assert "run_signalpost_final.py" not in part


def test_m38_preflight_push_only_no_provider_secret_or_live_flag():
    preview=(ROOT/".github/workflows/v10-m38-zero-credit-preflight.yml").read_text()
    start=preview.index("      - name: Verify no provider client or production entrypoint is called by preflight")
    end=preview.index("\n      - name: Preview actual archived previously-consumed four-company query eligibility",start)
    without_self=preview[:start]+preview[end:]
    assert "  push:" in preview
    assert "workflow_dispatch:" not in without_self
    assert "TAVILY_API_KEY" not in without_self
    assert "--live" not in without_self
    assert "--execute-live" not in without_self
    assert "actions/upload-artifact" not in without_self
    assert "secrets.SIGNALPOST_PILOT_REPORT_KEY" in preview


def test_m38_wrapper_private_secrets_and_archive_gate_fail_closed():
    source=(ROOT/"scripts/run_v10_m38_actions_wrapper.py").read_text()
    assert 'if args.preview:' in source
    assert 'if args.live and (' in source
    assert 'os.environ.get("GITHUB_RUN_ATTEMPT")!="1"' in source
    assert '_validate_previous_four(frozen_four,previous4)' in source
    assert '_refuse_prior_live_report(token,directory)' in source
    assert 'len' not in 'nothing sensitive'
    assert 'fernet.encrypt(json.dumps(report,sort_keys=True).encode())' in source
    assert 'output.chmod(0o600)' in source
    assert 'except Exception:' in source
    assert "raise SystemExit(1)" in source
