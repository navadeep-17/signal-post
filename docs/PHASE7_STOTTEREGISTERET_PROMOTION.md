# Phase 7 — Støtteregisteret Support-Award Promotion

Decision: **PROMOTE / EXACT-WRAPPER CONSUMED QUALIFIED / FINAL CLEAN-HEAD CI + MERGE/POST-MERGE GATE PENDING**.

## Identity and evidence contract

- Official Brønnøysundregistrene Støtteregisteret complete CSV; NLOD.
- One shared dataset request per evaluator batch.
- Target identity is authorized only when the row's **primary recipient organisation number** exactly equals the target org number.
- `Spesifisert mottaker` and granting authority are context only.
- <=365-day awards; max 5 most-recent events/company.
- Evaluator-facing evidence retains row SHA-256, snapshot SHA-256, source row number/key, retrieval timestamp and exact evidence span.
- Amounts are emitted only with explicit source currency; interval values retain explicit interval currency.
- Claim: `official.support_award`; canonical fact: `support_award` / `public.official_support_award`.
- The fact is official support activity, never company-authored news/social/hiring activity.
- Expected source failure is nonfatal and cannot remove a terminal company envelope.

## Certified-layer architecture

PR #97 initially modified immutable certified V1. Baseline CI `37255960174` correctly rejected that shape; the verifier/pin was never weakened.

Final architecture:

- V1 restored byte-for-byte to blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`;
- V2 remains unchanged at blob `5b69cc320c38e3aab13cf09fe2e2a09e62751433`;
- V7 owns the support request reservation, fetch, support-claim projection, canonical re-projection, synthesis rebuild, report accounting and V6 evaluator handoff;
- support-specific flags terminate at V7.

## Failed wrapper gate preserved

Run `37257936472`, job `111598892070`, remains a **failed promotion gate**. The actual V8 runtime/output was clean and contained 46 support claims + 46 canonical facts, but report accounting counted the wrong fact key and emitted `published_canonical_facts=0`. The verifier correctly rejected the inconsistent report.

The fix counts `canonical_field == public.official_support_award` and is regression-covered. Do not relabel the failed run as qualified.

## Definitive exact-wrapper consumed qualification

Run `37260381903`, job `111606171316`: **PASS**.

- qualification SHA: `f47353a7f0b7eb63efa45a76c48850a7a648be2d`;
- production parent SHA: `22655265d3adc99bb2b73ef52d29caf6fa966d03`;
- qualification-only delta: temporary workflow, subsequently deleted;
- cohort: certified final-release-1000 chunk 0, already consumed; 100 companies; no fresh cohort;
- artifact `phase7-v8-consumed-requalification-100-v2`, ID `11325335788`;
- artifact ZIP SHA-256 `b60b0469ed31cc3b8651445dc786fd4ce34ad325044bebdd6572d5c261a85148`;
- 100/100 terminal;
- 11 support companies;
- 46 support claims;
- 46 support canonical facts;
- report `published_claims=46` / `published_canonical_facts=46`;
- contract/canonical/synthesis/support-projection errors: 0;
- 1 shared support request;
- support bytes: 305,978,976;
- support snapshot SHA-256 `8889b22ee01c7aaae1dd6a0c079977e00f4d390440ec0779f17d999dfbd951d1`;
- BRREG change-feed requests: 1;
- observed conservative charge: 1,366/2,000;
- theoretical conservative ceiling: exactly 2,000/2,000;
- wrapper runtime: 797.471 s / 2,400 s;
- third-party cost: $0;
- search API requests: 0;
- evaluator product: 4,839,091 bytes;
- output SHA-256 `cf03cf75f40d5b28c793befbe6708769af6c063e17f379f8af2f4e6cfb9ef9e8`;
- report SHA-256 `fc213d927b0c9bc76ac88d59c44a1e3e09d3757b723ff1358594b4229be4dbcf`;
- product SHA-256 `c81336203c3a986a82a0da71582cafbcf17df9a1695cfd4fdd358217b69022b6`.

## Exact artifact audit

All 46 support claims in artifact `11325335788` were audited by the qualification verifier and independently after download. Results:

- 46 claims == 46 root canonical support facts;
- 11 target companies;
- each claim has exactly one support evidence record;
- every evidence record carries row SHA-256, snapshot SHA-256, source row number/key and retrieval time;
- every evidence span contains the exact target primary-recipient organisation number;
- award date equals evidence `effective_at`;
- every explicit amount has source currency;
- every amount interval has explicit interval currency;
- known wrong-company publications: 0;
- audit errors: 0;
- independently calculated ZIP digest matches GitHub artifact digest.

## Request theorem

For actual V8 on 100 companies under a 2,000 conservative-request cap:

1. V8 supplies 2,000 to V7.
2. V7 reserves 1 Støtteregisteret shared request (charge 2) and forwards 1,998 to V2.
3. Unchanged V2 reserves 1 BRREG change-feed request (charge 2) and forwards 1,996 to immutable V1.
4. V1 fixed company + Wikidata ceiling is 901 logical; under 1,996 conservative it has 97 H2g annual-report slots.
5. V1 theoretical total = 998 logical / 1,996 conservative.
6. Add BRREG change feed = 999 logical / 1,998 conservative.
7. Add support dataset = **1,000 logical / exactly 2,000 conservative**.

No additional request can be added without re-proving the theorem and deliberately reallocating a slot.

## Remaining promotion gate

The source and final wrapper path are now consumed-qualified. Before merge only repository hygiene/release gates remain:

1. keep the temporary qualification workflow deleted;
2. update continuation/history/roadmap docs with the successful run while preserving failed run `37257936472`;
3. verify the final PR diff contains no V1/V2 drift or temporary qualification scaffolding;
4. run final exact-head Baseline CI after all cleanup/docs commits;
5. merge PR #97 only with expected-head protection;
6. require post-merge Baseline CI green and pin the exact production SHA/run.

After post-merge green, advance to Phase 11 fresh evaluator-shaped release qualification. Do not submit a Builderr revision merely because this source merges.
