# M28 — Experiments Stay Off main

Decision: **EXPERIMENT ONLY / DO NOT MERGE**. The policy is to keep production main and the qualified V8 baseline unchanged until independent evidence proves score improvement. The former main-targeted dispatcher PR #177 was closed without merging.

## Why this route works

GitHub documents `gh workflow run WORKFLOW --ref BRANCH` for manually dispatching an existing workflow against a selected non-default branch: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow

Signalpost already has `.github/workflows/ci.yml` with a `workflow_dispatch` trigger on its default branch. M28 changes **only the copy of that existing workflow on this experiment branch**, adding a separate job restricted to `github.event_name == workflow_dispatch` and the exact `experiment/v10-m28-no-main-manual-pilot` branch. It does not touch the copy in main. Normal PR/push baseline CI still runs; the experimental provider job does not.

## What the manual job does

- Uses an immutable reviewed M26 code SHA `649aa9dcb0ceecf5947d2271ee846b0dc9d76e13` with no user-supplied ref.
- Safely defaults to `mode=preview`: verifies the original three SHA256-pinned prior-consumed cohorts, reconstructs the exact 7+7+6 source set, checks zero company/provider HTTP requests and zero published claims.
- Live is **not automatic**. It requires manual `mode=live`, exactly `RUN_FROZEN_CONSUMED_20_ONLY` as text, three affirmative billing/free-credit/security checks, secrets `TAVILY_API_KEY` and `SIGNALPOST_PILOT_REPORT_KEY`, and an initial run attempt (not a rerun). The 20-entity run can consume up to 20 Basic Search credits, in a private run, only when intentionally launched.
- Fails closed if the encryption key is missing or invalid, BEFORE Tavily use.
- Stores manual-review results only as a 1-day authenticated Fernet encrypted artifact. Never upload plaintext to Actions, GitHub issues, public docs or chat. Retain a PRIVATE copy of the independent Fernet decryption key.
- The full V8 100-company 2000-charge and 2400-second runtime proof is **not** demonstrated by this standalone developer-only 20-company runner. No production promotion or independent transfer implied.

## Safe manual preview (zero Tavily credits)

First, sign in using GitHub CLI locally (if necessary) and use:

```bash
gh workflow run ci.yml --ref experiment/v10-m28-no-main-manual-pilot -f mode=preview -R navadeep-17/signal-post
```

The M28 job should become visible on a successful GitHub dispatch of this branch's `ci.yml`. If GitHub cannot dispatch the branch's version, **do not merge code to main to work around it**; use the existing M26 local preview path described in `docs/V10_M26_CONSUMED_PILOT_RUNBOOK.md`, or revisit branch-only triggers after investigation.

Look up the dispatched workflow in the GitHub Actions tab; verify M28 preview reports exactly 20 consumed IDs and 0 external calls. The default Baseline CI job may run alongside the M28 preview because both jobs are defined in the branch version of `ci.yml`.

Do not dispatch `live` until the preview passes, the second secret is independently recoverable, and the user explicitly approves using up to 20 free credits.

## Example live activation options — NOT PERMISSION OR AN INVITATION TO RUN

An eventual manually approved execution requires all five user inputs in the branch dispatch: mode live, the exact live confirmation phrase, billing-off, sufficient-free-credit and server-only handling confirmations. **No live run was started when writing these instructions.**

## Main and release policy

- NO merge of PR #177, no new standalone dispatch YAML on main.
- No changes to official entry point `scripts/run_signalpost_v8.py`, qualified release SHA `200f056a5a60cad23610a3958b6bec62dfb624a5`, or release artifacts.
- Require at least 2 net-new exact-legal-entity websites out of frozen, previously consumed development 20; zero false company sites and no losses of previously validated claims; manually audit *every* positive.
- Then frozen, disjoint previously consumed transfer and full request/time budget proof in actual V8→V7→V2→V1 integration BEFORE proposing any main promotion. Preserve M20 sealed Gate B and unused fresh cohorts.
