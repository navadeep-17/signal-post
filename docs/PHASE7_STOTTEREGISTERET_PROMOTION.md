# Phase 7 — Støtteregisteret Support-Award Promotion

Decision: **PROMOTE source semantics / exact-head wrapper requalification pending before merge**.

## Identity and evidence contract

- Official Brønnøysundregistrene Støtteregisteret complete CSV; NLOD.
- One shared dataset request per evaluator batch.
- Target identity is authorized only when the row's **primary recipient organisation number** exactly equals the target org number.
- `Spesifisert mottaker` and granting authority are context only.
- <=365-day awards; max 5 most-recent events/company.
- Row SHA-256, snapshot SHA-256, retrieval timestamp and exact evidence span retained.
- Amounts are emitted only with explicit source currency; interval values retain explicit interval currency.
- Claim: `official.support_award`; canonical fact: `support_award` / `public.official_support_award`.
- The fact is official support activity, never company-authored news/social/hiring activity.
- Expected source failure is nonfatal and cannot remove a terminal company envelope.

## Consumed semantic qualification

Run `37254237936`, job `111587836938`: **PASS**.

- Artifact `11321344340`; ZIP SHA-256 `ba2fcdcf22473cc5e6159086516e7eb32da14b43ff11c4717f889910a383e357`.
- Cohort: certified final-release-1000 chunk 0, already consumed; 100 companies; no fresh cohort.
- 100/100 terminal; 11 support companies; 46 support observations/claims/canonical facts.
- 0 contract, canonical, synthesis, external-observation, registry-change-integrity or budget failures.
- 1 shared support request; 305,978,976 bytes; support retrieval 348,446 ms.
- Support snapshot SHA-256 `8889b22ee01c7aaae1dd6a0c079977e00f4d390440ec0779f17d999dfbd951d1`.
- H2g ceiling 97; observed conservative charge 1,366/2,000; theoretical charge 2,000/2,000.
- External wall time 784 s; third-party cost $0; search API requests 0.
- Product HTML contained the canonical support facts/evidence.

This run remains definitive evidence for the source's **identity, evidence, amount/currency and typed-event semantics**. It was run before the final integration layer was moved from V1 to V7, so an exact-head consumed V8 rerun is required to qualify the final wrapper architecture.

## Manual artifact audit

All 46 published support observations in artifact `11321344340` were checked. Every target organisation number equals the primary-recipient organisation number recorded in the evidence span; every primary-recipient name matches the target company name on this cohort; evidence span, row hash, snapshot hash and retrieval time are present; amount/currency pairs are source-backed; no observation uses a specified recipient to establish identity. Known wrong-company publications: 0.

## PR #97 CI correction

PR #97 initially placed the support fetch inside `scripts/run_signalpost_final.py`. Baseline CI run `37255960174`, job `111592968992`, correctly rejected that design:

- pytest: **459 passed, 1 failed, 5 subtests passed**;
- only failing test: repository-only submission verifier;
- failure reason: `run_signalpost_final.py` is the immutable certified V1 collector and its blob drifted;
- no merge occurred;
- the verifier and immutable pin were not weakened or repinned.

The architecture was corrected instead:

- certified V1 restored byte-for-byte to blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`;
- current V2 remains unchanged at blob `5b69cc320c38e3aab13cf09fe2e2a09e62751433`;
- V7 owns Støtteregisteret reservation, fetch, support-claim projection, canonical re-projection, synthesis rebuild, report accounting and V6 UI handoff;
- support-specific flags are consumed by V7 and never reach pinned V2/V1;
- code/test retune head before documentation commits: `338730d3ddf562955c967468983bd8cb3f0cc590`.

## Corrected request theorem

For actual V8 on 100 companies with a 2,000 conservative-request cap:

1. V8 supplies 2,000 to V7.
2. V7 reserves 1 Støtteregisteret shared request (charge 2) and forwards **1,998** to V2.
3. Unchanged V2 reserves 1 BRREG change-feed request (charge 2) and forwards **1,996** to immutable V1.
4. V1 fixed company + Wikidata ceiling is 901 logical; under 1,996 conservative it has **97** H2g annual-report slots.
5. V1 theoretical total = 998 logical / 1,996 conservative.
6. Add BRREG change feed = 999 logical / 1,998 conservative.
7. Add support dataset = **1,000 logical / exactly 2,000 conservative**.

No additional request can be added without re-proving the theorem and deliberately reallocating a slot.

## Promotion gate

Before merge, require all of the following on the final PR architecture:

1. exact-head Baseline CI green: full pytest, certified-1000 canonical audit, immutable submission-bundle verifier, deterministic refresh replay;
2. exact-head actual-V8 consumed requalification on an already-consumed cohort;
3. 100% terminal outputs and zero output-contract/canonical/synthesis/registry-change/support integrity failures;
4. support request bounded to one, combined theoretical conservative ceiling <=2,000, runtime <= configured wrapper ceiling, cost $0, search API requests 0;
5. evaluator-facing V6 product contains the support facts/evidence;
6. manual audit of every published support fact in the exact-head artifact;
7. clean final PR diff with no temporary qualification workflows/harnesses.

Only after those gates pass may PR #97 merge. Then require post-merge Baseline CI and pin the exact production SHA/run. After that, advance to Phase 11 fresh evaluator-shaped release qualification. Do not submit a Builderr revision merely because this source merged.
