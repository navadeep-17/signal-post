# Signalpost Continuation State

Last updated: 2026-10-05

This file is the authoritative short handoff for the next implementation session. Live GitHub remains authoritative if any SHA/run below has advanced.

## Repository state at this checkpoint

- authoritative production branch before this promotion: `main`
- observed `main` SHA before promotion PR: `86b60b2b5e87966c4a8beb4719e01905421b68ac`
- clean promotion branch: `feature/stotteregisteret-support-awards`
- production code staging commit from `main`: `91e825e844100eaf1341317126dca5fe2e52fc9b`
- source-selection audit PR #96 is merged; its merge/main SHA is `86b60b2b5e87966c4a8beb4719e01905421b68ac`
- Phase 4 dated-activity evidence hardening remains merged and post-merge green.
- no Builderr submission is authorized merely because this source is promoted.

## Active roadmap stage

Phase 7 — typed dated activity — is the current implementation milestone being promoted through Støtteregisteret. The source-family selection gate that followed Phase 4 is complete. Phase 2 website discovery remains isolated/shelved. After this promotion merges and post-merge CI is green, the main-track NEXT is Phase 11 fresh evaluator-shaped release qualification.

## Phase 7 Støtteregisteret promotion candidate

Decision: **PROMOTE** after clean PR CI + merge/post-merge gate.

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

### Definitive consumed V8 qualification

- cohort: already-consumed certified `final-release-1000` chunk 0, 100 companies; **no fresh cohort consumed**;
- workflow run: `37254237936` — PASS;
- job: `111587836938` — PASS;
- qualified workflow head: `125771e7bc04664553226d0688e5f6de883900df`;
- hardened production semantics head: `59dd767a7bbc4a5f99d076be633e29a582fd711b`;
- diff between those heads is workflow-only; production code is unchanged;
- artifact: `phase5-support-v8-consumed-live-100`, ID `11321344340`;
- artifact ZIP digest: `ba2fcdcf22473cc5e6159086516e7eb32da14b43ff11c4717f889910a383e357`;
- support snapshot SHA-256: `8889b22ee01c7aaae1dd6a0c079977e00f4d390440ec0779f17d999dfbd951d1`;
- input/terminal companies: 100 / 100;
- support-award companies: 11;
- support observations/claims/canonical facts: 46 / 46 / 46;
- verified website companies: 8;
- contact-email companies: 3;
- social-profile companies: 4;
- workforce companies: 99;
- canonical `hiring_and_public_activity` companies: 16;
- contract errors: 0;
- canonical validation errors: 0;
- synthesis validation errors: 0;
- external observation validation errors: 0;
- registry-change integrity errors: 0;
- wrong-company publications found in manual audit: 0;
- third-party cost: $0;
- search API requests: 0;
- support requests: 1;
- BRREG change-feed requests: 1;
- H2g annual-report structural ceiling under V8: 97;
- observed conservative request charge: 1,366 / 2,000;
- theoretical conservative request ceiling: exactly 2,000 / 2,000;
- V8 external wall runtime: 784 s;
- generated product HTML: 4,838,708 bytes and contains support-award facts/evidence.

Manual audit of artifact `11321344340` checked all 46 support observations: target org == primary-recipient org in supporting span, target company name == primary-recipient name on this cohort, hashes/retrieval times/evidence spans present, and amount/currency pairs source-consistent. No observation used a specified recipient to authorize identity.

Historical pre-hardening screens (for context only) reported broader 106/1000 and 88/1000 figures. They must **not** be treated as production-equivalent because the final identity and amount/currency semantics were hardened afterward.

## Phase 2 parallel track — reconciled latest result

The exact-org Common Crawl research path remains **SHELVED / NOT PRODUCTION**.

Latest Stage-4 consumed-history result:

- generic Common Crawl sample: 3,000 domains;
- indexed unique organisation numbers: 453;
- consumed history checked: 5,900 companies;
- overlap: 4 / 5,900 (0.0678%);
- net-new exact verified sites: 2;
- result is far below the 20+/100 breakthrough threshold.

Do not merge or restart this path unchanged. The exact-org retrieval mechanism is technically valid, but acquisition reach is not remotely sufficient.

## Request theorem after Støtteregisteret

For actual V8 on 100 companies:

- V8 reserves 1 shared BRREG change-feed request first (conservative charge 2);
- base final runner receives conservative budget 1,998;
- fixed final-runner ceiling is 901 logical (company+Wikidata) + 1 shared Støtte = 902 logical;
- remaining annual-report ceiling is 97 logical requests;
- combined V8 theoretical logical requests = 1,000;
- conservative challenge ceiling = exactly 2,000.

Do not add another shared or per-company request without re-proving this theorem and deciding explicitly what loses its slot.

## NEXT

1. Open the clean Støtteregisteret production PR from `feature/stotteregisteret-support-awards`.
2. Require Baseline CI green on exact PR head (full pytest, certified-1000 canonical audit, submission-bundle verification, deterministic refresh replay).
3. Merge only with expected-head protection; verify new `main` SHA and post-merge Baseline CI.
4. Pin the exact merge SHA / post-merge run in this file and `IMPLEMENTATION_LOG.md`.
5. Advance to **Phase 11 fresh evaluator-shaped release qualification**. Use a genuinely fresh cohort only now that the transfer gate is strong. Require 100% terminal envelopes, zero known wrong-company publications, zero evidence/contract/canonical/synthesis/integrity failures, manual audit of Støtte facts, request/runtime/cost proof, exact SHA freeze and reproducible artifacts.
6. Do **not** submit a Builderr revision solely because the code merged; submit only after the Phase-11 release gate is clean and the bundled improvement is material.
