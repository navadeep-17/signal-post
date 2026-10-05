# Signalpost Continuation State

Last updated: 2026-10-05

This file is the authoritative short handoff for the next implementation session. Live GitHub remains authoritative if any SHA/run below has advanced.

## Repository state

- production branch: `main`
- production/main SHA: `60f385b58a0f1c72f58efd35db71b1566202403a`
- Phase 7 PR #97 is **MERGED**
- Phase 7 merge commit: `60f385b58a0f1c72f58efd35db71b1566202403a`
- post-merge Baseline CI: run `37262030919`, job `111611064093`: **PASS**
- final pre-merge clean head: `a6187cad81e38a1e24618f6e16f33d40b247063d`
- final pre-merge Baseline CI: `37261892046`: **PASS**
- certified V1 `scripts/run_signalpost_final.py` remains byte-for-byte at blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`
- V2 `scripts/run_signalpost_v2.py` remains unchanged at blob `5b69cc320c38e3aab13cf09fe2e2a09e62751433`
- no Builderr submission is authorized merely because Phase 7 merged

## Active stage

Phase 7 Støtteregisteret is **IMPLEMENTED + TESTED + CONSUMED-WRAPPER QUALIFIED + MERGED + POST-MERGE GREEN** and is closed as a production-promotion milestone.

The active main-track milestone is now **Phase 11 — fresh evaluator-shaped release qualification**. Use a genuinely fresh, disjoint 100-company cohort. Phase 2 website discovery remains shelved.

## Phase 7 production semantics now on main

- official Brønnøysundregistrene Støtteregisteret complete CSV; NLOD;
- one shared dataset request per evaluator batch;
- **primary recipient organisation number only** establishes target identity;
- `Spesifisert mottaker` and granting authority are context-only and never authorize identity;
- <=365-day awards; max 5 most-recent events/company;
- observation `official_support_award`;
- claim `official.support_award`;
- canonical type/field `support_award` / `public.official_support_award`;
- official support is never relabelled as company-authored news/social/hiring activity;
- evaluator-facing evidence retains row SHA-256, source snapshot SHA-256, source row number/key, retrieval time and exact supporting span;
- amounts publish only with explicit source currency; interval amounts retain interval currency;
- expected source failure is nonfatal and cannot remove a terminal company envelope.

## Definitive consumed wrapper qualification

Run `37260381903`, job `111606171316`: **PASS**.

- qualification SHA `f47353a7f0b7eb63efa45a76c48850a7a648be2d`;
- production parent `22655265d3adc99bb2b73ef52d29caf6fa966d03`;
- already-consumed certified final-release-1000 chunk 0; 100 companies; no fresh cohort;
- artifact `phase7-v8-consumed-requalification-100-v2`, ID `11325335788`;
- artifact ZIP SHA-256 `b60b0469ed31cc3b8651445dc786fd4ce34ad325044bebdd6572d5c261a85148`;
- 100/100 terminal;
- 11 support companies;
- 46 support claims = 46 support canonical facts; report 46/46;
- all 46 support evidence rows audited; audit errors 0;
- support snapshot SHA-256 `8889b22ee01c7aaae1dd6a0c079977e00f4d390440ec0779f17d999dfbd951d1`;
- support requests 1; BRREG change-feed requests 1;
- observed conservative request charge 1,366 / 2,000;
- theoretical conservative ceiling exactly 2,000 / 2,000;
- wrapper wall runtime 797.471 s / 2,400 s;
- third-party cost $0; search API requests 0;
- contract/canonical/synthesis/support-projection errors 0;
- evaluator product contains the support facts/evidence.

The earlier exact-wrapper run `37257936472` remains a **failed promotion gate**: production output contained 46 claims + 46 canonical facts, but a report-only counter bug emitted 46/0. The verifier correctly failed it. The bug was fixed by counting `canonical_field == public.official_support_award` and is regression-covered. Do not rewrite that historical failure as success.

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

## NEXT — Phase 11 fresh release qualification

1. Freeze production SHA `60f385b58a0f1c72f58efd35db71b1566202403a` as the release candidate under test; do not change production semantics during the run.
2. Build an all-touched exclusion set from every previously consumed/fresh/failed qualification cohort available in repository artifacts/history.
3. Select a genuinely fresh evaluator-shaped 100-company cohort with **0 overlap** against that exclusion and record seed, exclusion count/SHA and cohort SHA.
4. Run the actual V8 evaluator path with the same production request/runtime/cost limits and generate evaluator-facing product output.
5. Require 100/100 terminal envelopes; zero output-contract, evidence, canonical, synthesis, registry-change and support-projection integrity failures; theoretical request ceiling <=2,000; runtime <=2,400 s; third-party cost $0; search API requests 0.
6. Manually/programmatically audit every published Støtteregisteret support fact on the fresh cohort for exact primary-recipient identity, row/snapshot provenance, award/effective date consistency and source-backed currencies.
7. Audit any other newly observed external website/job/activity cases for wrong-company publication; known wrong-company publications must be 0.
8. Freeze output/report/product/cohort hashes and upload reproducible qualification artifacts tied to the exact production SHA.
9. Only if Phase 11 is clean, prepare the next Builderr release/submission bundle. Do **not** submit merely because Phase 7 is merged.
