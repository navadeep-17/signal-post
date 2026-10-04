# Signalpost — Current Continuation State

Last updated: 2026-10-04 (Asia/Kolkata)

This is the first file every implementation chat must read. Repository state and live GitHub metadata are authoritative over chat history. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; strategy belongs in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Current production `main` SHA at this reconciliation:

`1589e4c5fd8c9cdc44e28574c961ee1912e47bf9`

That commit is documentation-only (`docs: reconcile continuation state with live repository`). Production feature semantics remain the Phase-1 line merged through PR #92.

### Active implementation branch / PR

- branch: `feature/phaseb-idle-contact-enrichment`
- PR #94: `Phase B: exact-site contact phone enrichment`
- state: **OPEN / DRAFT / NOT MERGED**
- current implementation head before this handoff-doc write: `83391bcbe410367428a1893c2a9f56bad3a01bcb`
- last exact measured candidate head: `e80577f1e846dcfa8252132017e9f949e0acb7d7`
- PR #94 must remain draft while Phase A2 is implemented and fresh qualification is still pending.

Other open draft PRs (#84, #78, #76) remain historical/experimental and are not the active production path.

## 2. Lifecycle state

### Phase 1 exact BRREG lost-claim recovery

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** yes, fresh zero-overlap 100
- **MERGED:** yes, PR #92
- **POST-MERGE GREEN:** yes

Qualified semantics head: `381a370e36b2e40b36f48e405c5b122191cb199c`

Merge commit: `911ecef4f785bb5f2b5aa7cf75a52efd6f7c3051`

Qualification run: `37192494569`

Artifact: `phase1-fresh-disjoint-100`, ID `11299633898`, digest `812941edf79709cc2324b907d9efc4b889fc56ee7df9e095bfad2890a9ba5f3d`

Post-merge Baseline CI: `37193327713` PASS.

Fresh 100 result:

- 100/100 terminal;
- company description 100 vs 14 baseline;
- registered purpose 96 vs 0;
- registration date 100 vs 0;
- registered business address 100 vs 0;
- registered contact email 21 vs 0;
- registered phone 17 vs 0;
- registered mobile 16 vs 0;
- evidence / output-contract / canonical / synthesis errors: 0;
- logical requests 669;
- conservative request charge 1,338/2,000;
- runtime 449.589 s;
- third-party cost $0;
- search requests 0.

### PR #94 reduced zero-network candidate

Current retained behavior after rejecting the network experiment:

- exact-live BRREG postal address projection with `/postadresse` lineage and canonical `company.postal_address`;
- explicitly labelled Norwegian contact-phone extraction from the already verified exact homepage only;
- `external.contact_phone` -> canonical `website.contact_phone`;
- no extra network request for phone extraction;
- page URL/hash/evidence-span provenance preserved;
- existing exact website identity gate remains authoritative.

State:

- **IMPLEMENTED:** yes
- **TESTED:** previously green on measured head; exact-head CI after experiment removal must be rechecked
- **QUALIFIED:** no
- **MERGED:** no
- **POST-MERGE GREEN:** not applicable

## 3. Phase A family-coverage / collected-vs-emitted audit

The audit is now sufficiently complete to make a strategic decision: **Phase A is not closed**.

### Frozen Phase-1 cohort company-family coverage

- verified website: 8/100;
- external contact email: 4/100;
- registered contact email: 21/100;
- any registered phone/mobile: 29/100;
- social profile: 3/100;
- concrete job posting: 0/100;
- dated company update: 1/100;
- workforce: 100/100;
- registry changes: 100/100;
- canonical people: 100/100;
- registered locations/workplaces: 81/100;
- careers surface: 2/100.

### Consumed Phase-1 E2E on PR #94 candidate

Run `37196444699`: **PASS**.

Artifact `phaseb-consumed-e2e`, ID `11300583926`, digest `sha256:fe0eee5d099c9128ab24cce616a7f4c7c3884ddebd5934889c56a879187c5c70`.

Measured 100-company result:

- external contact-phone companies: 2;
- external contact-email companies: 4;
- postal-address companies with an available value: 30;
- registered phone/mobile + external phone union: 31 vs 29 baseline, so +2 net-new phone-family companies;
- verified website remains 8;
- social remains 3;
- concrete jobs remain 0;
- dated activity remains 1;
- workforce 100;
- people 100;
- registered locations 81;
- 100/100 terminal;
- contract/canonical/synthesis errors: 0;
- observed logical requests: 673;
- observed conservative charge: 1,346/2,000;
- theoretical charge ceiling: 2,000;
- third-party cost: $0;
- search requests: 0.

Exact-head Baseline CI on candidate head `74527e8d072bd1456b11ba55dc3d85c27f75ac0f`: run `37196448235`, PASS.

### Rejected Phase B idle contact-page network fallback

A scheduler-shaped transfer gate was run on the consumed C12-M5 cohort.

- workflow run: `37197243641`;
- measured head: `e80577f1e846dcfa8252132017e9f949e0acb7d7`;
- V8 evaluator execution itself: PASS, 100/100 terminal;
- promotion assertion: **FAIL** because net-new company-level contact coverage was zero;
- one contact-surface phone company was observed: `977117186`, but that company already had contact-family coverage;
- observed logical requests: 679 before V5 wrapper / 680 combined;
- observed conservative charge: 1,358 before V5 wrapper / 1,360 combined;
- theoretical ceiling: 2,000;
- runtime: 438.254 s;
- cost: $0;
- search requests: 0;
- artifact: `phaseb-m5-consumed-transfer`, ID `11302125123`, digest `sha256:448635d91a6d141771cd116d54e15222327434f1671597c19c5e7e3d19a6cd2d`.

Decision: **DROP** the idle network contact-page fallback. It did not clear the roadmap's net-new-company promotion bar. The fallback workflow and contact-surface-specific tests were removed, and `wikidata_discovery.py` was restored to the production bounded Wikidata behavior. This rejected path is historical evidence, not a qualified feature.

## 4. Newly discovered zero-request Phase A2 opportunity

The frozen exact-org BRREG source snapshot contains broad official fields that are still dropped by `official.normalize_entity()` and therefore cannot reach evaluator-facing claims/canonical facts.

Measured availability on the audited 100-company snapshot includes approximately:

- foundation date (`stiftelsesdato`): 98/100;
- Foretaksregisteret registration date: 98/100;
- statutes/articles date (`vedtektsdato`): 96/100;
- institutional sector code/description: 95/100;
- capital/share-capital structure: 91/100;
- registered-in-Foretaksregisteret state: 100/100;
- registered-in-VAT state: 100/100;
- VAT registration date: 48/100.

These are materially broader than current website-dependent families and require **no additional source request** because the exact organisation-number BRREG live response is already fetched.

Precision rule: if implemented, publish only from the retained exact-org live BRREG response with precise source-field lineage. Do not fill these managed fields from bulk/profile fallback.

## 5. Precision findings / invariants

- no known wrong-company publication was found in the current audit;
- candidate discovery remains non-proof;
- exact organisation number remains the legal-entity anchor;
- contact phone is homepage-local and requires an already publishable exact website;
- unlabelled numbers do not become phone claims;
- generic careers page remains non-job evidence;
- parent/subsidiary inheritance remains prohibited;
- registry changes remain official registry activity, never company-authored news;
- missing / ambiguous / blocked remains explicit;
- third-party API policy remains $0.

## 6. Request/runtime theorem

Base per-profile structural ceiling remains:

- 5 official logical requests;
- at most 4 logical site requests;
- base per-profile ceiling 9.

Annual-report PDF/OCR is separately reserved within the 100-company challenge budget and can make an individual final `run_metrics.logical_requests` total 10. This does not mean the site scheduler exceeded four requests.

The 100-company theoretical conservative ceiling remains <=2,000.

## 7. Current blocker

Do not consume a fresh qualification cohort yet.

Reason: Phase A2 still has broad exact-live BRREG facts that can improve evaluator-visible company coverage with zero additional network requests. The roadmap requires exhausting meaningful zero-risk projection gaps before promoting network enrichment.

## 8. Exact next 1–3 actions

1. Implement Phase A2 exact-live BRREG retention/projection for the highest-value broad fields (foundation date, enterprise-register date/status, institutional sector, capital, VAT status/date), with exact source paths, fail-closed semantics, no bulk fallback, canonical mappings and idempotence tests.
2. Run exact-head Baseline CI plus a consumed evaluator-shaped measurement comparing Phase-1 baseline -> Phase A2/PR94 combined company coverage, requests/runtime/cost and evidence errors.
3. Only if precision is clean and coverage gain is broad, run one fresh zero-overlap 100-company qualification on the stabilized combined candidate; then decide PR restructuring/merge.

## 9. Do-not-repeat decisions

- do not restore the rejected idle contact-page fallback without new evidence of net-new company coverage;
- do not loosen exact website identity;
- do not treat generic careers pages as jobs;
- do not revive guessed `.com` discovery without new evidence;
- do not scrape LinkedIn/Facebook/Glassdoor;
- do not use random review scraping;
- do not use paid search/API services under the $0 constraint;
- do not tune against Builderr's checked collection;
- do not submit after every small patch.

## 10. NEXT

**NEXT: Phase A2 exact-live BRREG zero-request recovery. Implement the broad missing official fields first; do not fresh-qualify or merge PR #94 until Phase A2 is measured and stable.**
