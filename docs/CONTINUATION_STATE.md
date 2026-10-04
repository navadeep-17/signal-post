# Signalpost — Current Continuation State

Last updated: 2026-10-04 (Asia/Kolkata)

Repository state and live GitHub metadata are authoritative over chat history. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; strategy belongs in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Current production `main` SHA before Phase-A merge:

`1589e4c5fd8c9cdc44e28574c961ee1912e47bf9`

### Active implementation branch / PR

- branch: `feature/phaseb-idle-contact-enrichment`
- PR #94: `Phase A: exact-live BRREG zero-request breadth recovery`
- state: **OPEN / READY / NOT MERGED**
- second-fresh qualified measurement head: `a7192c4fe9f47e26fcc2a0d3b632e86a1586cfe0`
- release cleanup after qualification removed only the rejected external-phone path, one-off workflows and stale doc noise; qualified official/postal semantics were not broadened after the fresh run.

Other open draft PRs are historical/experimental and are not the active production path.

## 2. Lifecycle state

### Phase 1 exact BRREG lost-claim recovery

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** yes
- **MERGED:** yes, PR #92
- **POST-MERGE GREEN:** yes

Qualification run `37192494569`; artifact `phase1-fresh-disjoint-100`, ID `11299633898`, digest `812941edf79709cc2324b907d9efc4b889fc56ee7df9e095bfad2890a9ba5f3d`. Merge commit `911ecef4f785bb5f2b5aa7cf75a52efd6f7c3051`. Post-merge Baseline CI `37193327713` PASS.

### Phase A / PR #94 exact-live BRREG breadth

Retained production candidate:

- exact-live BRREG postal address;
- foundation date;
- statutes/articles date;
- Foretaksregisteret membership + registration date;
- institutional sector;
- registered capital structure;
- VAT-register membership + registration date;
- forced-dissolution status;
- exact source-path/URL/hash/canonical lineage;
- zero additional source requests.

Lifecycle:

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** **yes**
- **MERGED:** no
- **POST-MERGE GREEN:** not applicable yet

The external homepage-phone subfeature is **REJECTED / REMOVED** from the merge candidate. It had +2 net-new phone-family companies on one consumed cohort but **0 net-new company-level phone coverage on both fresh 100-company cohorts**, so it did not satisfy the transfer bar.

## 3. Qualification evidence

### Consumed Phase A3 gate

Run `37200794754`: PASS on exact head `ddd35f0679a9b05bdea5a26cd1b5b8f83a1fc59f`.

Artifact `phasea3-consumed-e2e`, ID `11302927164`, digest `sha256:9c7b0014d0e08686f6801e541411da8141a36d331500cd9ca11c6f181e258578`.

Coverage / 100: forced dissolution 100, foundation 98, articles date 96, Foretaksregisteret state 100/date 98, sector 95, capital 91, VAT state 100/date 48, postal address 30. Quality errors 0. Operations: 669 logical, 1,338 conservative charge, 2,000 ceiling, 473.27 s, $0, 0 search API requests.

### First fresh attempt — correctly failed and consumed

Run `37201683517`, seed `20261102`, exact head `525b80126ac48e8662886422fbb606cce29e2a20`.

- exclusion: 8,223 companies, SHA `4ed34945be5f6363a287487fd32ea87b47ab43445a22e2378a32f31695cf94ae`;
- fresh 100, overlap 0, cohort SHA `f74aed4f1c3a389e2a88699f2df02edb01815c1f81cf87d6858cc276dacd5c29`;
- V8 PASS and integrity checks clean;
- postal address 17 vs an arbitrary predeclared `>=20` floor;
- qualification result: **FAIL**;
- artifact ID `11302933473`, digest `sha256:44045fa0727fb3fab5e79f7721e706d4a2a0cf2478644f3f61983291def12aa0`.

This cohort remains consumed; the failure was never relabelled as success.

### Second untouched fresh qualification — PASS

Run `37203580574` on exact measurement head `a7192c4fe9f47e26fcc2a0d3b632e86a1586cfe0`.

Freshness:

- failed first-fresh cohort included in exclusion;
- exact exclusion union: 8,323 unique companies;
- exclusion SHA: `ae5a1e78a883d75332d93bd0cd88f123e7f1a88300ee3d795067fc73c4cb2f85`;
- seed: `20261103`;
- 100 unique companies;
- overlap: 0;
- cohort SHA: `4078579d4a581da0b8d56e4d03d567c4032d43e93c8bb94ee3c02b140b651e40`.

Fresh company coverage / 100:

- forced dissolution: 100
- foundation date: 100
- articles date: 99
- Foretaksregisteret state: 100
- Foretaksregisteret registration date: 98
- institutional sector: 100
- registered capital: 98
- VAT state: 100
- VAT registration date: 48
- postal address: 23
- registration date: 100
- registered business address: 100
- company description: 100
- registered purpose: 98

Quality/operations:

- 100/100 terminal;
- V8 `passed=true`;
- evidence errors: 0;
- contract errors: 0;
- canonical errors: 0;
- synthesis errors: 0;
- observed logical requests: 666;
- conservative charge: 1,332/2,000;
- theoretical conservative ceiling: 2,000;
- runtime: 460.916 s;
- third-party cost: $0;
- search API requests: 0.

Artifact: `phasea-final-fresh-disjoint-100-v2`, ID `11304401011`, digest `sha256:31e12e11f2746dcf8c0b6454ab6052ab44281176363b6934889d22d57a08800b`.

Qualification result for the retained exact-BRREG/postal Phase-A behavior: **PASS**.

## 4. External-phone decision

Second fresh run contained one external homepage phone, `VEST GULV AS` (`924516941`), `+47 22 20 11 70`. Retained exact-page evidence was correct, and the live company page visibly labels the same phone. The exact BRREG live response also already supplied the same registered phone.

Across the two fresh cohorts:

- first fresh: 3 external-phone companies, 38 registered phone/mobile companies, combined union still 38 -> **0 net-new**;
- second fresh: 1 external-phone company, 33 registered phone/mobile companies, combined union still 33 -> **0 net-new**.

Decision: **DROP** the external-phone feature from PR #94 before merge. This is a monotonic safety/scope reduction after qualification, not a new recall expansion.

## 5. Precision invariants

- exact organisation number remains the legal-entity anchor;
- all retained Phase-A official fields publish only from exact-org BRREG live evidence;
- explicit `False` is a valid official fact; missing stays `not_available`;
- no bulk/profile fallback for Phase-A managed fields;
- candidate discovery remains non-proof;
- generic careers page remains non-job evidence;
- parent/subsidiary inheritance remains prohibited;
- third-party API spend remains $0.

## 6. Request/runtime theorem

- 5 official logical requests/profile ceiling;
- at most 4 site logical requests/profile;
- base per-profile ceiling 9;
- annual-report PDF/OCR separately reserved;
- V5 BRREG change feed separately batched;
- qualified theoretical conservative ceiling: 2,000;
- qualified observed conservative charge: 1,332.

No retained Phase-A field adds a source request.

## 7. Current blocker

Phase A is qualified but not yet merged. The remaining blocker is release hygiene only:

1. exact-head CI on the cleaned branch after phone/workflow removal;
2. merge if green;
3. verify post-merge `main` CI.

## 8. Exact next actions

1. Confirm the cleaned PR diff contains only continuity docs, `official.py`, `v2_registry_projection.py`, `canonical_projection.py`, and the two focused Phase-A tests.
2. Require exact-head Baseline CI green on the cleaned head.
3. Merge PR #94 and update docs with merge SHA.
4. Verify post-merge `main` CI.
5. After Phase A closes, resume Phase B/C website-enrichment / adaptive-request work using company-family net-new coverage as the promotion metric.

## 9. NEXT

**NEXT: exact-head CI on the cleaned qualified Phase-A branch, then merge PR #94 only if green and verify post-merge `main`.**
