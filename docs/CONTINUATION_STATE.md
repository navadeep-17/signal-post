# Signalpost Continuation State

Last updated: 2026-10-05

This file is the authoritative short handoff for the next implementation session. Live GitHub remains authoritative if any SHA/run below has advanced.

## Repository state

- production branch: `main`
- current production/main SHA before this promotion: `86b60b2b5e87966c4a8beb4719e01905421b68ac`
- active branch: `feature/stotteregisteret-support-awards`
- active PR: #97, `Phase 7: add exact-org Støtteregisteret support awards`
- PR #97 is **NOT merged**
- no Builderr submission is authorized from this branch yet
- certified V1 collector `scripts/run_signalpost_final.py` remains byte-for-byte at blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`
- current V2 evaluator `scripts/run_signalpost_v2.py` remains unchanged at blob `5b69cc320c38e3aab13cf09fe2e2a09e62751433`
- current production code/test fix head before this documentation commit: `6695a5c4a8c8bd2a4499db1d3b30752f6a817c60`

## Active stage

Phase 7 — typed official dated activity through Brønnøysundregistrene Støtteregisteret — remains the active promotion milestone. Source selection is complete; Phase 2 website discovery remains shelved. The main-track NEXT after this merge/post-merge gate is Phase 11 fresh evaluator-shaped release qualification.

## Production semantics

- source: official Brønnøysundregistrene Støtteregisteret complete CSV; NLOD;
- one shared dataset request per evaluator batch;
- **primary recipient organisation number only** establishes target identity;
- `Spesifisert mottaker` and granting authority are context-only and never authorize identity;
- <=365-day awards; max 5 most-recent events/company;
- observation: `official_support_award`;
- claim: `official.support_award`;
- canonical fact: `support_award` / `public.official_support_award`;
- official support activity is never relabelled as company-authored news/social/hiring activity;
- evaluator-facing evidence retains row SHA-256, source snapshot SHA-256, source row number/key, retrieval time and exact supporting span;
- amounts publish only with explicit source currency; interval amounts retain interval currency;
- expected source failure is nonfatal and cannot remove a terminal company envelope.

## Immutable-layer correction

The first PR #97 shape incorrectly modified certified V1. Baseline CI run `37255960174`, job `111592968992`, correctly failed only the repository-only submission verifier after 459 tests passed. The verifier/pin was not weakened or repinned.

The architecture was corrected instead:

- V1 restored exactly to `9be89b9827135b1ed703318e1d189d5d3b8ca604`;
- V2 remains unchanged at `5b69cc320c38e3aab13cf09fe2e2a09e62751433`;
- V7 owns Støtteregisteret reservation/fetch/projection/report accounting and rebuilds canonical+synthesis before the V6 evaluator surface;
- support-only CLI flags terminate at V7 and never leak into pinned V2/V1.

## Offline gate

The provenance-hardened production head `7d3c9672dbb592851d705ebe38a1674752fa4c48` passed full Baseline CI run `37257806967`:

- full pytest: PASS;
- certified-1000 canonical audit: PASS;
- immutable submission-bundle verification: PASS;
- deterministic refresh replay: PASS;
- refresh qualification verification: PASS.

After the consumed requalification exposed a report-only counting bug, the counter fix was committed as:

- source fix `d027fbadb5dac2f6ac07ef9a3b5cba97a5caf788`;
- regression head `6695a5c4a8c8bd2a4499db1d3b30752f6a817c60`.

A new exact-head Baseline CI is therefore required on the final docs-inclusive head before the next live rerun.

## First exact-wrapper consumed requalification

Run `37257936472`, job `111598892070`, qualification SHA `05cb7ff9e3defbaea8c5264ceca51467e2be1173` used the production parent `7d3c9672dbb592851d705ebe38a1674752fa4c48` plus only a temporary qualification workflow.

Result: **V8 runtime PASS / qualification verifier FAIL due report-counter bug / production support output itself audited clean**.

Runtime/output facts:

- actual one-command V8 path: PASS;
- 100/100 terminal companies;
- support source status: available;
- support requests: 1;
- support bytes: 305,978,976;
- support observations/claims: 46 across 11 companies;
- support snapshot SHA-256: `8889b22ee01c7aaae1dd6a0c079977e00f4d390440ec0779f17d999dfbd951d1`;
- BRREG change-feed requests: 1;
- H2g annual-report requests: 97 theoretical slots, 85 observed;
- observed conservative request charge: 1,366 / 2,000;
- theoretical conservative ceiling: exactly 2,000 / 2,000;
- wrapper wall runtime: 872.984 s / 2,400 s;
- third-party cost: $0;
- search API requests: 0;
- product HTML: 4,839,164 bytes and contains support facts/evidence;
- contract/canonical/synthesis/support-projection integrity errors: 0.

Artifact:

- artifact ID `11323453311`, `phase7-v8-consumed-requalification-100`;
- ZIP SHA-256 `2bdfe26920ed5e67a24859b69ca0c84b2d7863a7c21a2e22e47dfbd529aafef9`.

Manual/programmatic artifact audit of all 46 support claims found:

- 46 claims == 46 root canonical facts == 46 `canonical_profile.public_activity` support facts;
- 11 support companies;
- every claim has exactly one evidence record;
- every evidence record has row SHA-256 + snapshot SHA-256 + source row number/key + retrieval time;
- every evidence span contains the exact target primary-recipient organisation number;
- every award date matches evidence `effective_at`;
- every amount has explicit currency and every interval has explicit interval currency;
- audit errors: **0**.

Why the verifier failed:

- V7 report code counted support canonical facts using `fact["type"] == "public.official_support_award"`;
- canonical facts correctly encode `type="support_award"` and `canonical_field="public.official_support_award"`;
- report therefore emitted `published_claims=46` but `published_canonical_facts=0` even though the output contained all 46 canonical facts;
- the qualification verifier correctly rejected this inconsistent report;
- the fix now counts by canonical field and has a dedicated regression.

Do **not** relabel run `37257936472` as qualified. It remains a failed promotion gate whose failure isolated a report-accounting defect.

## Request theorem

For actual V8 on 100 companies under the 2,000 conservative-request cap:

1. V8 supplies 2,000 to V7.
2. V7 reserves one Støtteregisteret request = charge 2 and forwards 1,998 to V2.
3. V2 reserves one BRREG change-feed request = charge 2 and forwards 1,996 to immutable V1.
4. V1 fixed company + shared Wikidata ceiling = 901 logical.
5. V1 can allocate 97 H2g annual-report requests.
6. V1 total = 998 logical / 1,996 conservative.
7. + change feed = 999 / 1,998.
8. + Støtteregisteret = **1,000 logical / exactly 2,000 conservative**.

Do not add another shared or per-company request without re-proving this theorem and explicitly deciding what loses its slot.

## Prior consumed semantic proof

Run `37254237936`, artifact `11321344340`, remains valid source-semantic evidence: 100/100 terminal, 11 support companies, 46 observations/claims/canonical facts, zero integrity failures, and a 46/46 manual identity/evidence audit. It predates the final V7 integration boundary, so it cannot substitute for the exact-wrapper rerun.

## Phase 2 parallel track

Common Crawl exact-org Stage 4 remains **SHELVED / NOT PRODUCTION**: 3,000 generic domains -> 453 indexed org numbers -> 4/5,900 consumed overlap -> 2 net-new exact sites. Do not restart unchanged.

## NEXT

1. Require Baseline CI green on the current final code/docs head containing the canonical-report counter fix.
2. Re-run exact-head actual-V8 qualification on the same already-consumed certified 100; no fresh cohort.
3. Require support report `published_claims == published_canonical_facts == actual output support facts`, plus all prior identity/provenance/budget/runtime/product checks.
4. Manually audit the exact-head artifact again; all support claims must preserve exact primary-recipient identity and full row/snapshot provenance.
5. Delete temporary qualification workflow and verify the PR diff contains only durable production/tests/docs changes.
6. Run final exact-head Baseline CI after cleanup.
7. Merge PR #97 only with expected-head protection after all gates are green; run post-merge Baseline CI and pin exact merge SHA/run.
8. Advance to **Phase 11 fresh evaluator-shaped release qualification** only after post-merge green.
9. Do not submit a Builderr revision solely because PR #97 merges; submit only after the Phase-11 fresh release gate is clean and materially improves the bundle.
