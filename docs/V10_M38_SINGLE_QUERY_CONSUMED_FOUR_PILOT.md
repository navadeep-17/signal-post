# M38 — Single pre-registered homepage query for exactly four consumed companies

**Disposition: PREPARED / ZERO-CREDIT PREFLIGHT PASSED / LIVE NOT STARTED / NO MAIN MERGE / NO SCORE CLAIM.**

## Observed baseline and reason to run

- Existing M28: 20 previously consumed website-unverified companies, zero independently qualified new sites. M31: 17 failed search-to-crawl selection, three failed independent legal-entity verification.
- Existing M33 four-company repeat: 4/4 with normalized URL results, 2/4 with at least one syntactically plausible HTTPS root, zero accepted for crawl, zero independently verified sites. This is a PRIVATE internal Signalpost pipeline funnel, NOT a provider-specific benchmark.
- M36 categorizes candidate rejection flags and M37 compiles three offline query designs. Neither measured real improvement.
- Original individual M33 provider titles, URLs, snippets and ranks were deliberately not retained, so the exact reason either plausible root was rejected cannot be recovered.

## Immutable choice BEFORE any live request

Select exactly one previously untested variant for each of the SAME four previously consumed, originally abstaining Norwegian legal entities as M33: `legal_name_municipality_homepage`.

Query is quoted FULL registry legal name + registry MUNICIPALITY + `hjemmeside`. The nine-digit organization number is not part of the QUERY, but the independently fetched site MUST still display the exact target number to enter manual review.

This conservative alternative is chosen ahead of time instead of trying many variants or changing query after inspecting results. **No fallback search** if the first results are poor.

Original comparison is the previously saved, encrypted M33 report for those exact four companies; it has 0 original/M32 nominees and 0 page fetches. M38 is observational paired development only, not randomized causal identification or an independent held-out score.

## Implementation, private-only

- `src/norway_company_agent/v10_m38_alternative_search.py`: M25-equivalent fixed-endpoint Bearer-auth Basic Search POST, at most one request, no HTTP redirect, no retry, no proxies, no provider generated answer/raw content, 8-second timeout and 512-KiB maximum response. Clone and validate the original M25 request options, changing ONLY the query string to the pre-registered M37 variant.
- `scripts/run_v10_m38_pre_registered_pilot.py`: reuse M33 exact frozen historical four-company cohort and strict website-crawl/identity checks. Add M36 private reason counts for each transient search result. No new company/URL published, no provider query/title/snippet/rank/answer saved.
- `scripts/run_v10_m38_actions_wrapper.py`: fetch only SHA-pinned consumed M19-A/M19-B/M20-A archives and original encrypted M26 20-company + M33 four-company reports; decrypt BOTH in memory using existing GitHub Fernet secret; verify same historical company list/order and exact four original abstentions; compile query for all four *before* any live search. Preview stops here. Live requires exact GitHub repository/branch, a first-attempt manual dispatch, API key and absence of any previous completed M38 encrypted report. Encrypt M38 output IN MEMORY; upload ciphertext only via Actions, keep no plaintext report file.
- No M38 code is imported from qualified V8 or release, nor does it replace the production submission runner.

## Upper bounds and failure handling

| Category | M38 diagnostic maximum |
|---|---:|
| Previously consumed companies | exactly 4 |
| New Basic Search requests | 4 total, one each |
| Independent robots+homepage logical requests | 8 total |
| Total challenge logical HTTP requests reserved | 12 |
| Conservative redirect-adjusted charges | 24 |
| Batch wall-time internal guard | 180 seconds |
| Published company claims | 0 |

All request reservations happen BEFORE HTTP. Stop on provider 401/403, 429, malformed response, network timeout or request-budget violation. Do not automatically retry. The report remains private (7-day encrypted-only artifact), including any independently fetched first-party URL hashes, while public GitHub logs include no provider response content. There is no confirmed zero-dollar charge until the owner checks current Tavily usage/pay-as-you-go.

## Manual activation policy — NOT YET AUTHORIZED

Run only after a fresh user approval specifying up to FOUR free Basic Search credits, personal dashboard confirmation of pay-as-you-go OFF and at least 4 remaining free credits, plus server-side/private processing approval. The experimental job is guarded behind manual `workflow_dispatch` on the exact branch `experiment/v10-m38-pre-registered-4-homepage-query`; `main` does not expose new M38 inputs or live jobs.

Workflow `ci.yml` on this experimental branch adds M38 preview/live inputs, typed `RUN_M38_FROZEN_FOUR_SINGLE_HOMEPAGE_QUERY`, account safeguards, and immutable code checkout pinned to commit `82dd81a65297291a76d24c32a7649fb9e9810380`. Its normal pull-request baseline job contains no provider credentials. A separate branch-push-only preflight can validate real archived cohort and encrypted keys with ZERO Tavily searches.

**DO NOT RUN LIVE UNTIL THE PRE-REGISTERED SAFETY GATES AND TESTS ARE REVIEWED.** In particular, a second manual dispatch can still consume search credits if the first dies before creating an encrypted artifact. Treat the live activation as single-shot and do not retry automatically.

## Verification and release gates

- Initial M38 exact archived-cohort/secret preflight [run #38024339888](https://github.com/navadeep-17/signal-post/actions/runs/38024339888): PASS, 120 focused tests, the same four real consumed profiles and one query each validated without Tavily/website HTTP.
- M38 experimental [draft PR #181](https://github.com/navadeep-17/signal-post/pull/181) remains UNMERGED. Final head Baseline CI including workflow-guard tests must pass before user is asked to activate live.
- A candidate only qualifies for MANUAL REVIEW after independently fetched exact Norwegian 9-digit org number, same registered-domain/URL provenance, wrong-company/BRREG collision veto, and no existing V8 site lost. New sites must then be audited manually and compared with unchanged qualified V8.
- Do NOT infer a score improvement from a search-result URL, homepage-shaped candidate or even a website fetch. Promotion still requires at least 2 net-new first-party exact-company sites per 20 development companies, zero wrong-company matches and baseline losses, independent disjoint consumed transfer, and full 100-company 2000-charge/2400-second budget proof.

**Archive expiry:** the old M33 encrypted artifact is retained by GitHub only until approximately 2026-10-16 03:14 UTC, so a future live M38 would need that artifact (or a separate ciphertext-only rearchive). This is not a reason to skip user confirmation or loosen controls.
