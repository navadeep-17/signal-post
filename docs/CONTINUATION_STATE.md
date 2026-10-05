# Signalpost Continuation State

Last updated: 2026-10-05

This file is the authoritative short handoff for the next implementation session. Live GitHub remains authoritative if any SHA/run below has advanced.

## Repository state

- production branch: `main`
- current `main` SHA: `a56509cd18a24a0d492e48d4c8c718ce3f5b27d9`
- Phase 7 production-code merge: `60f385b58a0f1c72f58efd35db71b1566202403a`
- Phase 7 post-merge Baseline CI: `37262030919`: **PASS**
- current precision-retune PR: **#99 — Phase 11: veto explicit wrong website owners**
- PR #99 branch: `fix/phase11-explicit-site-owner-veto`
- PR #99 latest durable production/test semantics are based on owner-veto code + adversarial regressions; temporary consumed-replay workflow has been removed
- PR #99 full Baseline CI `37314026333`: **PASS** on code/test head `532bb93f0c02b6da608bd070c7fa36349b5d8cfc`
- later Baseline CI `37314406825`: **PASS** on checksum-adjusted replay head `a7e622a89fbde026205e544473e25d6efbfa67d2`
- certified V1 `scripts/run_signalpost_final.py` remains byte-for-byte at blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`
- V2 `scripts/run_signalpost_v2.py` remains unchanged at blob `5b69cc320c38e3aab13cf09fe2e2a09e62751433`
- no Builderr submission is authorized yet

## Active stage

Phase 7 Støtteregisteret is **IMPLEMENTED + TESTED + QUALIFIED + MERGED + POST-MERGE GREEN** and remains closed.

The active main-track milestone is **Phase 11 — fresh evaluator-shaped release qualification, currently in RETUNE after a fresh precision failure**.

The first fresh Phase 11 cohort (seed `20261104`) passed all machine gates but **FAILED manual exact-company precision audit**. That cohort is permanently consumed and must never be reused as fresh validation.

Phase 2 website discovery remains shelved; do not reopen it from this failure. The fix is stricter publication verification, not broader candidate generation.

## Fresh Phase 11 run — machine PASS / manual precision FAIL

Workflow run `37309340028` used a genuinely fresh 100-company evaluator-shaped cohort.

Selection / lineage:

- qualification harness SHA `518019b54a409286766a18a2ebfae0f2bd60c64f`;
- production parent `a56509cd18a24a0d492e48d4c8c718ce3f5b27d9`;
- production-code merge under qualification `60f385b58a0f1c72f58efd35db71b1566202403a`;
- selection seed `20261104`;
- prior touched exclusion: 8,423 companies;
- exclusion SHA-256 `fd1e5c7e54d6034821553a1903fd20bea76738dcf0d5e0c75eec93b4a724a298`;
- fresh cohort SHA-256 `394eaae1b43fbe5e951fc4a61c7185c068bfa6dad1d37a7223cefc507429dd99`;
- overlap with prior touched set: 0;
- artifact ID `11346320812`;
- artifact ZIP SHA-256 `9c9ab8bb8477c949a9491f7a672ad181f43566cd9b885a1f4fc6a2dd720165cf`.

Machine result:

- 100/100 terminal completed;
- 11 support companies;
- 48 support claims = 48 support canonical facts;
- support requests 1;
- BRREG change-feed requests 1;
- observed conservative request charge 1,364 / 2,000;
- theoretical conservative ceiling exactly 2,000 / 2,000;
- wall runtime 804.632 s / 2,400 s;
- third-party API cost $0;
- search API requests 0;
- contract errors 0;
- canonical errors 0;
- synthesis errors 0;
- dangling evidence refs 0;
- support projection errors 0;
- 48 support evidence rows queued for manual audit;
- 25 external publications queued for manual audit;
- **machine gates passed = true**;
- release-qualified remained false pending manual precision audit.

Manual audit found one material exact-company defect:

- target legal entity: `INTERIØRKUPP AS` (`825188592`);
- H1c guessed candidate: `https://interiorkupp.no/`;
- the site itself states that `interiorkupp.no` is owned by **Rolf Sletvold Interiørsenter AS**, a different legal entity;
- the wrong site contaminated exactly four published external claims: official website, Instagram profile handle, social-links aggregate and contact email;
- the other manually audited published websites were clean;
- decision for seed `20261104`: **FAIL / RETUNE / NO RELEASE**.

## PR #99 generic precision fix

The fix is generic and source-agnostic; there is no company/domain blacklist.

`identity.py` now treats an explicit statement that the **current fetched site/domain** (or an unambiguous site noun such as `nettstedet` / `website`) is owned by a different named legal entity as hard negative identity evidence.

Guard properties:

- current-domain/site ownership statements only;
- unrelated ownership prose for another domain does not trigger the veto;
- same-target owner statements remain publishable;
- exact target organisation-number proof remains stronger positive evidence;
- derived social/contact publication is automatically lost when the website is quarantined.

Adversarial regressions cover:

- the Interiørkupp failure mechanism;
- same-target explicit domain owner;
- generic `Denne nettsiden eies av TARGET AS`;
- unrelated other-domain owner statement.

## Consumed-only replay of seed 20261104

Run `37314396820`, job `111777368735`, replayed the already-consumed cohort only. It is **not fresh qualification**.

The expensive V8 replay itself passed:

- 100/100 terminal;
- report `passed=true`;
- request/budget/contract/canonical/synthesis gates passed;
- third-party cost $0.

The workflow conclusion was failure only because its final verifier expected the extracted site-owner string to equal exactly `Rolf Sletvold Interiørsenter AS`. The extractor intentionally retained trailing source prose, producing:

`Rolf Sletvold Interiørsenter AS, og tilbyr et stort utvalg innen parkett, gulvbelegg, tapet og andre interiørartikler`

That verifier formatting assumption does **not** invalidate the production fix. Independent artifact audit of replay artifact ID `11347753450`, ZIP SHA-256 `ff03b78a41372f368ace904a009e82eda5c42fd5aa3d74d37a91ccaee0684e01`, proves:

- target `825188592` now has no published website;
- no `interiorkupp.no`-derived external claim remains;
- identity assessment is `status=related_or_uncertain`, `score=0.1`, `publishable=false`;
- reason is `page explicitly states that this website is owned by a different named legal entity`;
- old failed-fresh external audit had 25 published external records;
- replay has 21 non-empty external publications;
- exact set comparison: **4 removed, 0 added**;
- the four removed publications are exactly the wrong Interiørkupp website, Instagram handle, social-links aggregate and `post@interiorkupp.no` email;
- every other previously published external value is unchanged.

Decision: **precision fix is monotonic on the consumed failure cohort and is eligible for final PR cleanup/CI/merge**. Do not count this replay as fresh evidence.

## Phase 7 production semantics on main

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

## NEXT — finish retune, then new fresh Phase 11 cohort

1. Keep PR #99 limited to the generic owner-veto production code, durable regressions and authoritative docs; remove all temporary replay/qualification scaffolding.
2. Require final exact-head Baseline CI on the cleaned PR head.
3. Merge PR #99 only with expected-head protection, then require post-merge Baseline CI on `main`.
4. Treat every company in seed `20261104` as permanently touched. The next fresh exclusion must therefore be **8,523 unique companies** (8,423 prior + failed fresh 100), with the new exclusion manifest/hash recorded.
5. Select a genuinely untouched evaluator-shaped 100-company cohort; seed `20261105` is the planned next deterministic seed unless repository state has advanced.
6. Run the actual V8 release path with the unchanged request/runtime/cost limits.
7. Require 100/100 terminal envelopes; zero contract/evidence/canonical/synthesis/registry-change/support-projection integrity failures; theoretical request ceiling <=2,000; runtime <=2,400 s; third-party cost $0; search API requests 0.
8. Manually audit every published Støtteregisteret support fact and every evaluator-visible external website/contact/social/job/activity publication. Known wrong-company publications must be 0.
9. Freeze exact cohort/output/report/product hashes and artifact IDs tied to the merged production SHA.
10. Only if that new fresh cohort passes both machine and manual gates may the next Builderr release/submission be prepared.
