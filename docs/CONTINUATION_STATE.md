# Signalpost Continuation State

Last updated: 2026-10-05

This file is the authoritative short handoff for the next implementation session. Live GitHub remains authoritative if any SHA/run below has advanced.

## Repository state at this checkpoint

- authoritative production branch: `main`
- current production/main SHA before this promotion: `86b60b2b5e87966c4a8beb4719e01905421b68ac`
- active promotion branch: `feature/stotteregisteret-support-awards`
- active PR: #97, `Phase 7: add exact-org Støtteregisteret support awards`
- latest code/test retune head before this documentation commit: `338730d3ddf562955c967468983bd8cb3f0cc590`
- certified V1 collector `scripts/run_signalpost_final.py` is restored byte-for-byte to blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`
- certified/current V2 evaluator `scripts/run_signalpost_v2.py` remains unchanged at blob `5b69cc320c38e3aab13cf09fe2e2a09e62751433`
- source-selection audit PR #96 is merged; its merge/main SHA is `86b60b2b5e87966c4a8beb4719e01905421b68ac`
- Phase 4 dated-activity evidence hardening remains merged and post-merge green
- PR #97 is **NOT merged** and no Builderr submission is authorized merely because this source is promoted

## Active roadmap stage

Phase 7 — typed dated activity — is the current implementation milestone being promoted through Støtteregisteret. The deterministic source-family selection gate that followed Phase 4 is complete. Phase 2 website discovery remains isolated/shelved. After PR #97 passes exact-head offline CI, exact-head consumed V8 wrapper requalification, merge and post-merge CI, the main-track NEXT is Phase 11 fresh evaluator-shaped release qualification.

## Phase 7 Støtteregisteret promotion candidate

Decision: **PROMOTE semantics / wrapper retune requires exact-head requalification before merge**.

Production semantics:

- source: official Brønnøysundregistrene Støtteregisteret complete CSV dataset;
- rights basis: NLOD;
- acquisition: one shared dataset request per evaluator batch;
- exact-company identity: **primary recipient organisation number only**;
- `Spesifisert mottaker` is contextual evidence only and can never establish target identity;
- granting authority can never establish target identity;
- event recency: <=365 days;
- at most 5 most-recent events/company;
- typed observation: `official_support_award`;
- output claim: `official.support_award`;
- canonical type/field: `support_award` / `public.official_support_award`;
- never relabel as company-authored news/social/hiring activity;
- row SHA-256 + source snapshot SHA-256 + retrieval time + exact supporting span retained;
- amounts publish only with explicit source currency; source interval amounts retain their own explicit interval currency;
- source failure is nonfatal and cannot remove the terminal company envelope.

### Consumed semantic qualification already completed

- cohort: already-consumed certified `final-release-1000` chunk 0, 100 companies; **no fresh cohort consumed**;
- workflow run: `37254237936` — PASS;
- job: `111587836938` — PASS;
- artifact: `phase5-support-v8-consumed-live-100`, ID `11321344340`;
- artifact ZIP digest: `ba2fcdcf22473cc5e6159086516e7eb32da14b43ff11c4717f889910a383e357`;
- support snapshot SHA-256: `8889b22ee01c7aaae1dd6a0c079977e00f4d390440ec0779f17d999dfbd951d1`;
- input/terminal companies: 100 / 100;
- support-award companies: 11;
- support observations/claims/canonical facts: 46 / 46 / 46;
- contract/canonical/synthesis/external-observation/registry-change-integrity/budget failures: 0;
- wrong-company publications found in manual audit: 0;
- third-party cost: $0;
- search API requests: 0;
- support requests: 1;
- BRREG change-feed requests: 1;
- H2g annual-report structural ceiling: 97;
- observed conservative request charge: 1,366 / 2,000;
- theoretical conservative request ceiling: exactly 2,000 / 2,000;
- external wall runtime: 784 s;
- generated product HTML contains the support-award facts/evidence.

Manual audit of artifact `11321344340` checked all 46 support observations: target org == primary-recipient org in supporting span, target company name == primary-recipient name on this cohort, hashes/retrieval times/evidence spans present, amount/currency pairs source-consistent, and no observation used a specified recipient to authorize identity.

This run remains definitive evidence for the **source semantics and evidence contract**, but it no longer by itself qualifies the final integration architecture because PR #97 subsequently moved the support layer out of immutable V1 and into V7. An exact-head consumed V8 rerun is therefore required before merge.

Historical pre-hardening screens (including broader 106/1000 and 88/1000 figures) are research-only and are not production-equivalent.

## PR #97 first Baseline CI and architecture correction

First exact-PR Baseline CI:

- run `37255960174`, job `111592968992`: **FAIL / correctly blocked**;
- full pytest result: **459 passed, 1 failed, 5 subtests passed**;
- sole failure: `tests/test_submission_bundle.py::test_repository_only_submission_verifier_passes`;
- cause: the first promotion shape modified `scripts/run_signalpost_final.py`, which is intentionally pinned as the immutable certified V1 collector;
- certified-1000 audit / bundle verification / refresh replay were skipped after pytest failed;
- no merge occurred and the verifier was not weakened or repinned.

Correction now on the branch:

- V1 restored exactly to pinned blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`;
- V2 remains unchanged at `5b69cc320c38e3aab13cf09fe2e2a09e62751433`;
- V7 now owns the one-request Støtteregisteret reservation, fetch, typed claim projection, canonical re-projection, synthesis rebuild, report accounting and V6 UI handoff;
- support-only CLI flags are consumed at V7 and never leak into pinned V2/V1;
- wrapper/budget regressions were rewritten around this architecture;
- latest code/test retune head before docs: `338730d3ddf562955c967468983bd8cb3f0cc590`.

## Request theorem after wrapper retune

For actual V8 on 100 companies with the 2,000 conservative-request budget:

1. V8 supplies the full 2,000 budget to V7.
2. V7 reserves one shared Støtteregisteret request = conservative charge 2 and forwards **1,998** to unchanged V2.
3. V2 reserves one shared BRREG change-feed request = conservative charge 2 and forwards **1,996** to immutable V1.
4. V1 fixed company + shared Wikidata ceiling is 901 logical requests; with a 1,996 conservative cap it can allocate **97** H2g annual-report requests.
5. V1 theoretical total = 998 logical / 1,996 conservative.
6. Add BRREG change feed -> 999 logical / 1,998 conservative.
7. Add Støtteregisteret -> **1,000 logical / exactly 2,000 conservative**.

Do not add another shared or per-company request without re-proving this theorem and explicitly deciding what loses its slot.

## Phase 2 parallel track — reconciled latest result

The exact-org Common Crawl research path remains **SHELVED / NOT PRODUCTION**.

Latest Stage-4 consumed-history result:

- generic Common Crawl sample: 3,000 domains;
- indexed unique organisation numbers: 453;
- consumed history checked: 5,900 companies;
- overlap: 4 / 5,900 (0.0678%);
- net-new exact verified sites: 2;
- result is far below the 20+/100 breakthrough threshold.

Do not merge or restart this path unchanged.

## NEXT

1. Require Baseline CI green on the new exact PR #97 head: full pytest, certified-1000 canonical audit, immutable submission-bundle verification and deterministic refresh replay.
2. After offline CI is green, run an **exact-head actual-V8 consumed requalification** on an already-consumed cohort. Require 100% terminal output, zero support/evidence/contract/canonical/synthesis/integrity failures, exact 2,000 budget proof, wrapper runtime proof, and support facts present in the evaluator-facing product.
3. Manually audit the support facts from that exact-head artifact; prior artifact `11321344340` remains semantic evidence but cannot substitute for the wrapper-path rerun.
4. Merge PR #97 only after those gates pass, using expected-head protection; verify new `main` SHA and post-merge Baseline CI.
5. Pin the exact merge SHA / post-merge run in this file and `docs/IMPLEMENTATION_LOG.md`.
6. Advance to **Phase 11 fresh evaluator-shaped release qualification**. Use a genuinely fresh cohort only then. Require 100% terminal envelopes, zero known wrong-company publications, zero evidence/contract/canonical/synthesis/integrity failures, manual audit of Støtte facts, request/runtime/cost proof, exact SHA freeze and reproducible artifacts.
7. Do **not** submit a Builderr revision solely because the code merged; submit only after the Phase-11 release gate is clean and the bundled improvement is material.
