# M27 — Manual GitHub Actions dispatcher for the consumed-20 Tavily pilot

Status: **DRAFT / NOT ACTIVATED ON DEFAULT BRANCH / NO CREDITS SPENT**.
Reviewer decision required before merging the dispatcher to main.
Qualified V8 remains immutable at commit `200f056a5a60cad23610a3958b6bec62dfb624a5`. The dispatcher is CI-only; it does not change the evaluator or production website code.

## GitHub manual-run constraint

GitHub workflow_dispatch is available only for workflows present in the **default branch**:
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch

Therefore a workflow file in an experimental PR branch **does not produce a working Run workflow button yet**. M27 stages a separate, minimal PR against main containing only this dispatcher + documentation/audit tests. This is intentional: do not merge M26/M25 experimental product code, and do not touch the qualified V8 release. Merging M27 will move the main commit (as any commit must), but it changes **only CI and supporting text/tests**, not release code.

## Reviewable execution boundary

- Workflow: .github/workflows/v10-m27-manual-consumed-pilot.yml
- Trigger: **workflow_dispatch ONLY**. No PR, push, schedule, workflow_run, reusable caller, or externally supplied code ref.
- Dispatch allowed only from main on exact repo navadeep-17/signal-post.
- Checkout exact reviewed M26 commit `649aa9dcb0ceecf5947d2271ee846b0dc9d76e13` (immutable SHA; no input-based ref selection).
- Default mode **preview**: 20 previously consumed IDs, all archived SHA-256 checks, **no provider or company HTTP**, no secrets passed to code.
- LIVE requires manual choice `live`, exact typed phrase `RUN_FROZEN_CONSUMED_20_ONLY`, and three affirmative boxes: current pay-as-you-go off, 20+ current free credits, and server-side/private handling.
- LIVE allowed only on initial run_attempt=1. Clicking "Re-run" cannot rerun live and spend credits twice.
- Both modes use readonly `contents` and `actions` permissions. GitHub credentials are not persisted by checkout. Existing three consumed evidence ZIPs are downloaded read-only.
- The API secret `TAVILY_API_KEY` appears **only in the live validation and execution steps** as an environment variable; no value is echoed, and actual pilot stdout/stderr are kept in private runner temporary files.
- M26 limits 20 exact IDs, one Basic search + one independent robots/homepage path per ID, stops on provider failures; each possible result requires first-party exact nine-digit Norwegian organisation-number proof, and is manual-review-only with 0 claims published.
- Live report is encrypted using authenticated Fernet before upload. **Never upload the JSON directly**. Encryption key supplied only through second GitHub Actions secret `SIGNALPOST_PILOT_REPORT_KEY`; only encrypted binary is uploaded, with 1-day artifact retention. The action deletes plaintext on the ephemeral runner.
- If live search aborts, it still tries to encrypt any existing report for offline triage; failures are visible only as generic job failure. No Tavily-specific benchmark details are logged publicly.
- No provider production integration or official Builderr evaluator key is established by this dispatcher.

## Additional security prerequisite — independent report encryption key

In addition to your already-added repo secret `TAVILY_API_KEY`, **create another GitHub Actions secret** named:

`SIGNALPOST_PILOT_REPORT_KEY`

Generate a unique 32-byte random, Fernet-compatible key **locally**, for example (Python standard library):

    python -c "import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"

Store it privately in a password manager **before** putting the same value directly into GitHub Settings -> Secrets and variables -> Actions -> New repository secret. **Do not share it in chat, a commit, issue or screenshot**. The encrypted artifact cannot be decrypted if you lose this second key. Do not use your Tavily API key as the encryption key.

Prefer a narrowly scoped GitHub Actions **environment secret** with required reviewer approval if your repository plan supports it and collaborators need restricted access; the current workflow references repository secrets as requested.

## After the M27 dispatcher PR has been reviewed and merged

1. In Actions, open **M27 Manual Frozen-20 Pilot (Encrypted Report Only)**.
2. First choose `preview` (default). It must pass without consuming any Tavily credits.
3. Before live: check the dashboard again. Researcher plan, pay-as-you-go OFF and at least 20 free Basic credits must be true **at the time you click live**. Old screenshots are not a current-credit guarantee.
4. Choose `live`, type `RUN_FROZEN_CONSUMED_20_ONLY`, check all 3 affirmations, and explicitly run the workflow. This may consume up to 20 free Basic Search credits. Never invoke it twice casually.
5. Download the **encrypted** `m27-consumed-encrypted-manual-review` artifact promptly (1-day retention) to your private computer. Never upload decrypted files back to public GitHub, chat or search logs.
6. Decrypt privately with a Fernet-capable Python environment, using the *second secret* from your password manager as the local `SIGNALPOST_PILOT_REPORT_KEY`. Example command (Python package cryptography required):

    python -c "import os;from pathlib import Path;from cryptography.fernet import Fernet; p=Path('m27-consumed-encrypted-report.fernet'); Path('private-m27-report.json').write_bytes(Fernet(os.environ['SIGNALPOST_PILOT_REPORT_KEY'].encode()).decrypt(p.read_bytes()))"

7. Independently review every proposed site URL against exact legal entity, registry organisation number, redirect/domain provenance and first-party page evidence; do not automatically publish. Provider-neutral aggregates only may be shared externally under Tavily Support's written informational guidance.

## Remaining gates

- A live development 20 is **not** a fresh or transfer cohort and is not official Builderr scoring.
- A measured improvement requires at least two *net new* independently qualified first-party websites / consumed 20 with zero wrong-company matches, no lost prior claims and full manual audit.
- Must separately prove real V8→V7→V2→V1 request-slot **substitution**, not append calls, with <=2,000 conservative HTTP charge / 100, <=2,400sec evaluator runtime and $0 third-party spend.
- Must confirm Builderr can inject a private evaluator key; a GitHub Actions repo secret does not follow code into Builderr's infrastructure.
- Until all gates pass, keep qualified V8 branch, release artifacts, main product files and previously sealed independent holdouts unchanged.

**Never run the live workflow as a byproduct of merging it.** It is manual-only and default preview.
