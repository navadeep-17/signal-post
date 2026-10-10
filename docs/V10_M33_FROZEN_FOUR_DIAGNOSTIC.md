# M33 — Four-company consumed-development pipeline diagnostic (NO SCORE CLAIM)

**Status:** offline/preflight QUALIFIED; **LIVE NOT DISPATCHED**. No modification to qualified V8 or `main`.

## Why four

The completed M28 live development pilot and M31 private aggregate diagnosis showed 17/20 companies did not pass the search-to-crawl nomination stage and 3/20 selected first-party pages failed independent legal-entity identity; none earned a new official-site claim. Because the previous report intentionally discarded search result URLs/titles/snippets, the count of empty provider responses versus candidates failing the selection gate cannot be reconstructed.

M33 chooses **exactly the first four of those 17 previously abstaining** companies in frozen M24 cohort order, after verifying all three original signed evidence archives, the full 20-company SHA-256 and the original encrypted M26 report. This is targeted **development** material, never fresh holdout or evidence of production lift.

## Hard limits

- One Basic Search per company, **at most 4** Basic Search API attempts total, no automatic retries and no fallback search.
- One independent robots/homepage attempt per accepted company, reserving at most 2 first-party logical requests per company, hence **at most 8**.
- Total **at most 12 logical** / **24 conservative challenge charges** under the project ×2 model. 180-second diagnostic time cap.
- No extra provider query or crawl appended to a V8 run; this is an isolated 4-company experiment, not production integration.
- No wrong-entity claims; every potential positive still requires separately fetched first-party page proof, exact Norwegian 9-digit organisation number, registered-domain/provenance verification, additional manual review and independent transfer.
- Zero published company claims and zero official score claims.

## Confidentiality

Provider search metadata is used transiently to choose a potential site. The stored private report contains, per company, **counts and stage flags only** plus first-party URLs/hashes for positively nominated manual-review candidates. It **does not persist provider result URLs/titles/snippets/ranks/answers/raw content**. The action encrypts the report in memory using the existing repo `SIGNALPOST_PILOT_REPORT_KEY` Fernet secret and uploads **only ciphertext** retained for seven days. The old M30 encrypted report is decrypted only in memory on a private runner; the lost encryption key is never printed or exported. No company-level or provider metrics are printed publicly.

## Offline validation

- [M33 zero-credit preflight](https://github.com/navadeep-17/signal-post/actions/runs/37877462122) **passed, 68 focused tests** with SHA-pinned three-archive reconstruction and branch workflow guard scan. No Tavily/website requests.
- [M33 full Baseline CI](https://github.com/navadeep-17/signal-post/actions/runs/37877465593) **passed**, including canonical baseline and submission verification.
- In the branch-only modification to the *existing default-branch* `.github/workflows/ci.yml`, the **M33 diagnostic job runs ONLY on manual `workflow_dispatch` of this exact experimental branch**. It never runs on push/PR. Default `preview` has no provider/environment secrets. Live requires typed `RUN_FROZEN_CONSUMED_4_ONLY`, `GITHUB_RUN_ATTEMPT=1`, current free-credit balance ≥4, pay-as-you-go OFF, and private/server-side consent.
- Immutable reviewed M33 wrapper/code checkout pinned to `d095ef4bb556d487dc8b3dfe5edbf07b50b2750a`, never an arbitrary ref.

## Next (user must manually dispatch via authenticated GitHub CLI)

Only after checking the current dashboard that the remaining Basic Search credit balance is ≥4 **and PAYG remains OFF**:

```powershell
gh workflow run ci.yml --ref experiment/v10-m32-offline-crawl-nomination -f m33_mode=live -f m33_live_confirmation=RUN_FROZEN_CONSUMED_4_ONLY -f m33_payg_off=true -f m33_credits_four=true -f m33_private=true -R navadeep-17/signal-post
```

**Run only once.** No live dispatch has been made as of this documentation commit. The GitHub connector cannot issue `workflow_dispatch` itself; do not replace it with an unguarded push trigger. Inspect new Actions run and encrypted artifact before interpreting pipeline results.

If live fails/aborts, no automatic retry. If full run succeeds, decrypt the report privately on Actions using the retained repo Fernet secret and publish only suitably permitted **provider-neutral Signalpost aggregate** funnel statistics, with no company URLs, provider search content or provider-specific benchmarking.

## Release prohibition

Remain draft/unmerged. A real improvement would require independently verified **net-new** exact-entity site coverage and zero baseline losses on independently audited consumed transfer, safe 100-company slot-substitution budget/wall, evaluator-compatible auth, and zero-dollar provider spend. Synthetic nomination gain is not measured coverage lift.
