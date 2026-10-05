# Phase 7 — Støtteregisteret Support-Award Promotion

Decision: **PROMOTE**, subject to clean production PR CI + merge/post-merge green.

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

## Definitive consumed V8 qualification

- Run `37254237936`, job `111587836938`: PASS.
- Qualified head `125771e7bc04664553226d0688e5f6de883900df`; production semantics match hardened head `59dd767a7bbc4a5f99d076be633e29a582fd711b` (difference is workflow-only).
- Artifact `11321344340`; ZIP SHA-256 `ba2fcdcf22473cc5e6159086516e7eb32da14b43ff11c4717f889910a383e357`.
- Cohort: certified final-release-1000 chunk 0, already consumed; 100 companies; no fresh cohort.
- 100/100 terminal; 11 support companies; 46 support observations/claims/canonical facts.
- 0 contract, canonical, synthesis, external-observation, registry-change-integrity or budget failures.
- 1 shared support request; 305,978,976 bytes; support retrieval 348,446 ms.
- Support snapshot SHA-256 `8889b22ee01c7aaae1dd6a0c079977e00f4d390440ec0779f17d999dfbd951d1`.
- V8 H2g ceiling 97; observed conservative charge 1,366/2,000; theoretical charge 2,000/2,000.
- External wall time 784 s; third-party cost $0; search API requests 0.
- Product HTML 4,838,708 bytes and contains the canonical support facts/evidence.

## Manual artifact audit

All 46 published support observations in artifact `11321344340` were checked. Every target organisation number equals the primary-recipient organisation number recorded in the evidence span; every primary-recipient name matches the target company name on this cohort; evidence span, row hash, snapshot hash and retrieval time are present; amount/currency pairs are source-backed; no observation uses a specified recipient to establish identity. Known wrong-company publications: 0.

## Budget theorem

Actual V8 reserves one BRREG change-feed request (charge 2), leaving the base runner 1,998. The base runner reserves one Wikidata request and one shared Støtte request, reducing H2g annual-report capacity to 97. Combined theoretical logical requests remain 1,000 and the conservative challenge ceiling remains exactly 2,000.

## Next gate

After clean merge and post-merge Baseline CI, move to Phase 11 fresh evaluator-shaped release qualification. Do not submit a Builderr revision merely because this source merged.
