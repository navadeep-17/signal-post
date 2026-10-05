# Signalpost Continuation State

Last updated: 2026-10-05

This file is the authoritative short handoff for the next implementation session. Live GitHub remains authoritative if any SHA/run below has advanced.

## Repository state

- production branch: `main`
- production/main SHA before this promotion: `86b60b2b5e87966c4a8beb4719e01905421b68ac`
- active branch: `feature/stotteregisteret-support-awards`
- active PR: #97, `Phase 7: add exact-org Støtteregisteret support awards`
- PR #97 is **NOT merged yet**
- clean branch head immediately after removing the successful qualification workflow: `7b107c29cbc18103a8f37a58994aad677c09a143`
- certified V1 `scripts/run_signalpost_final.py` remains byte-for-byte at blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`
- V2 `scripts/run_signalpost_v2.py` remains unchanged at blob `5b69cc320c38e3aab13cf09fe2e2a09e62751433`
- no Builderr submission is authorized merely because Phase 7 qualifies or merges

## Active stage

Phase 7 Støtteregisteret is now **IMPLEMENTED + TESTED + CONSUMED-WRAPPER QUALIFIED / FINAL CLEAN-HEAD CI + MERGE/POST-MERGE GATE PENDING**. Phase 2 website discovery remains shelved. After PR #97 merges and post-merge Baseline CI is green, the main-track NEXT is Phase 11 fresh evaluator-shaped release qualification.

## Production semantics

- official Brønnøysundregistrene Støtteregisteret complete CSV; NLOD;
- one shared dataset request per evaluator batch;
- **primary recipient organisation number only** establishes target identity;
- `Spesifisert mottaker` and granting authority are context-only and never authorize identity;
- <=365-day awards; max 5 most-recent events/company;
- observation `official_support_award`;
- claim `official.support_award`;
- canonical type/field `support_award` / `public.official_support_award`;
- never relabel official support as company-authored news/social/hiring activity;
- evaluator-facing evidence retains row SHA-256, source snapshot SHA-256, source row number/key, retrieval time and exact supporting span;
- amounts publish only with explicit source currency; interval amounts retain interval currency;
- expected source failure is nonfatal and cannot remove a terminal company envelope.

## Certified-layer correction

The first PR shape modified immutable V1. Baseline CI run `37255960174`, job `111592968992`, correctly blocked it: 459 tests passed and only the repository-only submission verifier failed. The verifier/pin was not weakened or repinned.

The corrected architecture keeps V1/V2 unchanged. V7 owns the Støtteregisteret request reservation, fetch, claim projection, canonical re-projection, synthesis rebuild, report accounting and V6 evaluator handoff. Support-only CLI flags terminate at V7.

## Offline qualification lineage

Provenance-hardened head `7d3c9672dbb592851d705ebe38a1674752fa4c48` passed Baseline CI `37257806967` including full pytest, certified-1000 canonical audit, immutable submission-bundle verification and deterministic refresh replay.

The first exact-wrapper consumed run `37257936472`, job `111598892070`, was **not qualified**: runtime/output passed and the artifact contained 46 claims + 46 canonical facts with zero evidence defects, but V7's report counter incorrectly tested `fact.type == public.official_support_award` and reported 46 claims / 0 canonical facts. The verifier correctly rejected the inconsistent report. The bug was fixed by counting `canonical_field == public.official_support_award` and covered by regression.

The counter-fix/docs parent `22655265d3adc99bb2b73ef52d29caf6fa966d03` then passed full Baseline CI `37260229913`.

## Definitive exact-wrapper consumed qualification

Status: **PASS**.

- workflow run: `37260381903`;
- job: `111606171316`;
- qualification SHA: `f47353a7f0b7eb63efa45a76c48850a7a648be2d`;
- production parent SHA: `22655265d3adc99bb2b73ef52d29caf6fa966d03`;
- only qualification-only delta at the run SHA: temporary workflow, subsequently deleted;
- cohort: certified `final-release-1000` chunk 0, already consumed; 100 companies; **no fresh cohort**;
- artifact: `phase7-v8-consumed-requalification-100-v2`, ID `11325335788`;
- artifact ZIP SHA-256: `b60b0469ed31cc3b8651445dc786fd4ce34ad325044bebdd6572d5c261a85148`;
- 100/100 terminal companies;
- 11 support companies;
- 46 support claims;
- 46 support canonical facts;
- report `published_claims=46` and `published_canonical_facts=46`;
- support snapshot SHA-256: `8889b22ee01c7aaae1dd6a0c079977e00f4d390440ec0779f17d999dfbd951d1`;
- support requests: 1;
- support bytes: 305,978,976;
- BRREG change-feed requests: 1;
- observed conservative request charge: 1,366 / 2,000;
- theoretical conservative ceiling: exactly 2,000 / 2,000;
- wrapper wall runtime: 797.471 s / 2,400 s;
- third-party API cost: $0;
- search API requests: 0;
- contract errors: 0;
- canonical errors: 0;
- synthesis errors: 0;
- support projection errors: 0;
- support evidence rows audited: 46;
- evaluator product bytes: 4,839,091;
- output SHA-256: `cf03cf75f40d5b28c793befbe6708769af6c063e17f379f8af2f4e6cfb9ef9e8`;
- report SHA-256: `fc213d927b0c9bc76ac88d59c44a1e3e09d3757b723ff1358594b4229be4dbcf`;
- product SHA-256: `c81336203c3a986a82a0da71582cafbcf17df9a1695cfd4fdd358217b69022b6`.

Independent post-run artifact audit repeated the verifier checks and found **0 errors** across all 46 support claims: exact primary-recipient org in the evidence span, one evidence record/claim, row hash, snapshot hash, row number/key, retrieval time, matching effective/award date, and explicit amount/interval currency where applicable. The artifact ZIP digest independently matches GitHub's digest.

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

## Phase 2 parallel track

Common Crawl exact-org Stage 4 remains **SHELVED / NOT PRODUCTION**: 3,000 generic domains -> 453 indexed org numbers -> 4/5,900 consumed overlap -> 2 net-new exact sites. Do not restart unchanged.

## NEXT

1. Update `docs/IMPLEMENTATION_LOG.md`, this roadmap and the Phase-7 promotion report with run `37260381903` / artifact `11325335788` while preserving failed run `37257936472` as historical failure.
2. Verify the PR diff contains only durable production/tests/docs changes and no temporary qualification workflow; confirm V1/V2 are absent from the diff.
3. Run **final exact-head Baseline CI after all cleanup/docs commits**.
4. If green, merge PR #97 with expected-head protection.
5. Verify the exact new `main` SHA and require post-merge Baseline CI green.
6. Pin merge SHA + post-merge run in continuity/history docs.
7. Advance to **Phase 11 fresh evaluator-shaped release qualification** only after post-merge green. Use a genuinely fresh cohort there, with 100% terminal envelopes, zero known wrong-company publications, zero evidence/contract/canonical/synthesis/integrity failures, support-fact audit, request/runtime/cost proof, exact SHA freeze and reproducible artifacts.
8. Do not submit a Builderr revision solely because PR #97 merges; submit only after the Phase-11 fresh release gate is clean and materially improves the bundle.
