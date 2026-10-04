# Signalpost — Current Continuation State

Last updated: 2026-10-04 (Asia/Kolkata)

Repository state and live GitHub metadata are authoritative over chat history. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; architecture/phase order belongs in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Phase-A production merge commit:

`8a729036350c019e107cd68a08641f1fff6796f6`

PR #94: `Phase A: exact-live BRREG zero-request breadth recovery`

- state: **MERGED**
- qualified measurement head: `a7192c4fe9f47e26fcc2a0d3b632e86a1586cfe0`
- cleaned/reconciled PR head: `d36ea6edefc58e38ad656042d93c6a409c4f02e7`
- exact-head Baseline CI: `37205694426` PASS
- merge commit: `8a729036350c019e107cd68a08641f1fff6796f6`
- post-merge Baseline CI: `37205739214` PASS

The latest `main` roadmap commit `ea79bf6283497dd991a9a106d7dffb8f3001d418` was reconciled into the PR before merge, so its Phase 0–11 architecture is preserved.

Other open draft PRs are historical/experimental and are not the active production path.

## 2. Lifecycle state

### Phase 1 / Phase A collected-vs-emitted exact BRREG recovery

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** yes
- **MERGED:** yes, PR #94
- **POST-MERGE GREEN:** yes

Retained production behavior:

- exact-live BRREG postal address;
- foundation date;
- statutes/articles date;
- Foretaksregisteret membership + registration date;
- institutional sector;
- registered capital structure;
- VAT-register membership + registration date;
- forced-dissolution status;
- exact source-path / source-row / URL / hash / canonical lineage;
- explicit `False` remains an available official fact;
- missing exact-live fields remain `not_available`;
- no bulk/profile fallback for these managed fields;
- zero additional source requests.

### Earlier Phase 1 lost-claim recovery

PR #92 remains **QUALIFIED + MERGED + POST-MERGE GREEN**. Qualification run `37192494569`; merge commit `911ecef4f785bb5f2b5aa7cf75a52efd6f7c3051`; post-merge Baseline CI `37193327713` PASS.

## 3. Phase-A qualification evidence

### Consumed gate

Run `37200794754`: PASS on `ddd35f0679a9b05bdea5a26cd1b5b8f83a1fc59f`.

Artifact `phasea3-consumed-e2e`, ID `11302927164`, digest `sha256:9c7b0014d0e08686f6801e541411da8141a36d331500cd9ca11c6f181e258578`.

Coverage / 100: forced dissolution 100, foundation 98, articles 96, Foretaksregisteret state 100/date 98, sector 95, capital 91, VAT state 100/date 48, postal address 30. Evidence/contract/canonical/synthesis errors: 0. Operations: 669 logical, 1,338 conservative charge, 2,000 ceiling, 473.27 s, $0, 0 search requests.

### First fresh attempt — FAILED and consumed

Run `37201683517`, seed `20261102`, head `525b80126ac48e8662886422fbb606cce29e2a20`.

- exclusion: 8,223 companies, SHA `4ed34945be5f6363a287487fd32ea87b47ab43445a22e2378a32f31695cf94ae`;
- fresh 100, overlap 0, cohort SHA `f74aed4f1c3a389e2a88699f2df02edb01815c1f81cf87d6858cc276dacd5c29`;
- V8 PASS and integrity checks clean;
- postal address 17 vs predeclared `>=20` optional-field prevalence floor;
- qualification result: **FAIL**;
- artifact ID `11302933473`, digest `sha256:44045fa0727fb3fab5e79f7721e706d4a2a0cf2478644f3f61983291def12aa0`.

This failure remains historical evidence and this cohort must never be reused as fresh validation data.

### Second untouched fresh qualification — PASS

Run `37203580574` on qualified measurement head `a7192c4fe9f47e26fcc2a0d3b632e86a1586cfe0`.

Freshness:

- failed first-fresh cohort added to exclusions;
- exclusion union: 8,323 unique companies;
- exclusion SHA: `ae5a1e78a883d75332d93bd0cd88f123e7f1a88300ee3d795067fc73c4cb2f85`;
- seed: `20261103`;
- 100 unique companies;
- overlap: 0;
- cohort SHA: `4078579d4a581da0b8d56e4d03d567c4032d43e93c8bb94ee3c02b140b651e40`.

Coverage / 100:

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

Quality / operations:

- 100/100 terminal;
- V8 `passed=true`;
- evidence errors: 0;
- contract errors: 0;
- canonical errors: 0;
- synthesis errors: 0;
- logical requests: 666;
- conservative charge: 1,332/2,000;
- theoretical ceiling: 2,000;
- runtime: 460.916 s;
- third-party cost: $0;
- search API requests: 0.

Artifact: `phasea-final-fresh-disjoint-100-v2`, ID `11304401011`, digest `sha256:31e12e11f2746dcf8c0b6454ab6052ab44281176363b6934889d22d57a08800b`.

## 4. Rejected external-phone paths

### Zero-network homepage phone

The labelled homepage-phone feature was precision-correct but failed the company-family transfer bar:

- consumed Phase-1 cohort: +2 net-new phone-family companies;
- first fresh: 3 external-phone companies, registered phone/mobile union 38, combined union still 38 -> 0 net-new;
- second fresh: 1 external-phone company, registered phone/mobile union 33, combined union still 33 -> 0 net-new.

Fresh case `VEST GULV AS` (`924516941`) correctly exposed `+47 22 20 11 70`, but exact BRREG live already supplied the same registered phone.

Decision: **DROP**. The extractor/projector/tests/canonical mapping were removed/restored before PR #94 merged.

### Idle contact-page network fallback

Consumed transfer run `37197243641` produced zero net-new company-level contact coverage. Decision remains **DROP / DO NOT RESTORE** without new generic evidence.

## 5. Precision and budget invariants

- exact organisation number is the legal-entity anchor;
- candidate generation is never publication proof;
- exact-live official fields publish only from exact-org BRREG evidence;
- page-level external provenance remains mandatory;
- parent/subsidiary inheritance remains prohibited;
- generic careers page is not a job;
- missing/blocked/ambiguous remains explicit;
- third-party API spend remains $0;
- base structural ceiling remains 5 official + at most 4 site logical requests/profile;
- annual-report and shared BRREG-change reservations remain separately accounted;
- qualified 100-company conservative ceiling remains 2,000.

## 6. Phase transition

Phase 1 / collected-vs-emitted exact BRREG recovery is **closed**.

Per `docs/70_PLUS_IMPLEMENTATION_PLAN.md`, the next architectural stage is Phase 2: **website discovery improvement**, followed by Phase 3 sitemap/targeted-page enrichment and Phase 4 page-level observation integrity.

Do not jump directly to optional ML/AI or broad new official connectors.

## 7. Exact next actions

1. Re-baseline current `main` company-family coverage after PR #94, especially verified website/contact/social/jobs/activity families.
2. Audit existing website candidate sources and rejection reasons to identify the highest-yield exact-site discovery gap without weakening identity.
3. Screen one bounded Phase-2 website-discovery strategy on consumed companies first; require net-new exact verified sites, wrong-company audit, request/runtime/cost accounting, and a PROMOTE/RETUNE/SHELVE/DROP decision.
4. Only after Phase-2 site reach improves, proceed to sitemap + targeted-page extraction.

## 8. NEXT

**NEXT: Phase 2 exact website-coverage improvement. Start with a current-main candidate/rejection audit and choose one bounded discovery strategy that can add net-new exact verified company sites without weakening identity.**
