# Signalpost — Current Continuation State

Last updated: 2026-10-04 (Asia/Kolkata)

Repository state and live GitHub metadata are authoritative over chat history. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; strategy belongs in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Current production `main` SHA:

`1589e4c5fd8c9cdc44e28574c961ee1912e47bf9`

Production feature semantics remain the Phase-1 line merged through PR #92. The current `main` tip is documentation-only over that production line.

### Active implementation branch / PR

- branch: `feature/phaseb-idle-contact-enrichment`
- PR #94: `Phase A: exact-live BRREG breadth + zero-network contact phone`
- state: **OPEN / DRAFT / NOT MERGED**
- fresh-attempt head: `525b80126ac48e8662886422fbb606cce29e2a20`
- branch was ancestry-reconciled with current `main` before the fresh attempt via merge commit `0b0c8e154bf6ac7391f1a01316f739cc9ff3892c`.

Other open draft PRs are historical/experimental and are not the active production path.

## 2. Lifecycle state

### Phase 1 exact BRREG lost-claim recovery

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** yes
- **MERGED:** yes, PR #92
- **POST-MERGE GREEN:** yes

Qualification run `37192494569`; artifact `phase1-fresh-disjoint-100`, ID `11299633898`, digest `812941edf79709cc2324b907d9efc4b889fc56ee7df9e095bfad2890a9ba5f3d`. Merge commit `911ecef4f785bb5f2b5aa7cf75a52efd6f7c3051`. Post-merge Baseline CI `37193327713` PASS.

### Phase A / PR #94 combined zero-request candidate

Retained production candidate:

- exact-live BRREG postal address;
- foundation date;
- statutes/articles date;
- Foretaksregisteret membership + registration date;
- institutional sector;
- registered capital structure;
- VAT-register membership + registration date;
- forced-dissolution status;
- zero-network explicitly labelled Norwegian phone from the already verified exact homepage;
- no idle contact-page network fallback (that experiment was rejected and removed).

Lifecycle:

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** **no**
- **MERGED:** no
- **POST-MERGE GREEN:** not applicable

Exact-head Baseline CI for first final fresh attempt: run `37201687696`, PASS on `525b80126ac48e8662886422fbb606cce29e2a20`.

## 3. Consumed evaluator-shaped measurements

### Phase A3 consumed Phase-1 cohort

Run `37200794754`: **PASS** on exact head `ddd35f0679a9b05bdea5a26cd1b5b8f83a1fc59f`.

Artifact: `phasea3-consumed-e2e`, ID `11302927164`, digest `sha256:9c7b0014d0e08686f6801e541411da8141a36d331500cd9ca11c6f181e258578`.

Company coverage / 100:

- forced dissolution: 100
- foundation date: 98
- articles date: 96
- Foretaksregisteret state: 100
- Foretaksregisteret registration date: 98
- institutional sector: 95
- registered capital: 91
- VAT state: 100
- VAT registration date: 48
- postal address: 30
- external homepage phone: 1
- external contact email: 3
- registered phone/mobile: 29
- combined phone family: 30

Quality/operations:

- terminal: 100/100
- evidence errors: 0
- contract errors: 0
- canonical errors: 0
- synthesis errors: 0
- observed logical requests: 669
- conservative charge: 1,338/2,000
- theoretical charge ceiling: 2,000
- runtime: 473.27 s
- third-party cost: $0
- search API requests: 0

### Rejected idle contact-page network fallback

Run `37197243641`: V8 PASS but promotion FAIL because net-new company-level contact coverage was zero. Artifact `phaseb-m5-consumed-transfer`, ID `11302125123`, digest `sha256:448635d91a6d141771cd116d54e15222327434f1671597c19c5e7e3d19a6cd2d`.

Decision: **DROP**. Do not restore without new generic evidence.

## 4. First final fresh qualification attempt — FAILED

Run `37201683517` on exact head `525b80126ac48e8662886422fbb606cce29e2a20`.

Freshness:

- seed: `20261102`
- prior exclusion manifest: 8,223 unique companies
- exclusion SHA: `4ed34945be5f6363a287487fd32ea87b47ab43445a22e2378a32f31695cf94ae`
- selected: 100 unique companies
- overlap: 0
- cohort SHA: `f74aed4f1c3a389e2a88699f2df02edb01815c1f81cf87d6858cc276dacd5c29`

V8 execution itself: **PASS**.

Fresh company coverage / 100:

- forced dissolution: 100
- foundation date: 99
- articles date: 97
- Foretaksregisteret state: 100
- Foretaksregisteret registration date: 98
- institutional sector: 100
- registered capital: 93
- VAT state: 100
- VAT registration date: 57
- postal address: **17**
- registration date: 100
- registered business address: 100
- company description: 100
- registered purpose: 97
- registered email: 26
- registered phone: 23
- registered mobile: 21
- external homepage phone: 3
- external contact email: 7
- registered phone/mobile companies: 38
- combined phone family companies: 38

Quality/operations:

- 100/100 terminal
- evaluator `passed=true`
- contract/canonical/synthesis/budget errors: 0
- exact evidence checks completed cleanly before the prevalence assertion
- observed logical requests: 702 combined
- conservative charge: 1,404/2,000
- theoretical ceiling: 2,000
- runtime: 451.153 s
- third-party cost: $0
- search API requests: 0

Qualification result: **FAIL** because the predeclared postal-address floor was `>=20/100` and the untouched cohort had `17/100`.

Artifact: `phasea-final-fresh-disjoint-100`, ID `11302933473`, digest `sha256:44045fa0727fb3fab5e79f7721e706d4a2a0cf2478644f3f61983291def12aa0`.

The failed cohort is now consumed and must never be reused as a fresh promotion cohort.

## 5. Precision findings / invariants

- no known wrong-company official publication was found;
- all Phase-A official facts are sourced only from the retained exact-org BRREG live response with exact URL/hash/source-field lineage;
- explicit `False` is a valid official fact; missing stays `not_available`;
- no bulk/profile fallback is permitted for Phase-A managed fields;
- homepage phone requires an already verified exact site and an explicit `Telefon` / `Tlf` / `Phone` / `Tel` label;
- candidate discovery remains non-proof;
- generic careers page remains non-job evidence;
- parent/subsidiary inheritance remains prohibited;
- third-party API spend remains $0.

Fresh external-phone cases from failed cohort: 3. Retained evidence is exact-page/hash backed. EVJU BYGDETUN live page visibly contains `Tlf.93209355`; the remaining cases remain subject to the normal exact-page evidence audit and any second-fresh manual review.

## 6. Request/runtime theorem

- 5 official logical requests/profile ceiling;
- at most 4 site logical requests/profile;
- base per-profile ceiling 9;
- annual-report PDF/OCR separately reserved;
- V5 BRREG change feed is separately batched;
- fresh attempt theoretical conservative ceiling: 2,000;
- observed conservative charge: 1,404.

No Phase-A official-field projection adds a source request.

## 7. Current blocker

The production candidate is stable, but **qualification is not yet achieved** because the first fresh promotion gate failed an arbitrary prevalence floor on an optional field (`postal_address`: 17 vs required 20).

Do not call this complete, qualified, or merge-ready yet.

## 8. Acceptance-criterion retune

The failed cohort shows that optional-field source prevalence is variable even when projection/evidence quality is perfect. A hard `>=20` floor for postal address is therefore not a sound correctness gate.

For the next untouched cohort, predeclare:

- broad near-universal fields keep strong minimum company-coverage floors;
- optional fields such as postal address and VAT registration date are promotion evidence when non-zero and exactly sourced, but their source prevalence is reported rather than used as an arbitrary universal floor;
- precision/evidence integrity remains a hard gate: zero evidence, contract, canonical and synthesis errors;
- request/runtime/cost limits remain hard gates;
- manual audit every newly introduced external-phone case.

This is a validation-criterion retune only. Production extraction/publication code should remain unchanged unless a real correctness defect is found.

## 9. Exact next 1–3 actions

1. Update the final-fresh verifier with the predeclared optional-field rule and construct a new all-touched exclusion manifest that includes the failed seed-`20261102` cohort; expected union is 8,323 unique companies with SHA `ae5a1e78a883d75332d93bd0cd88f123e7f1a88300ee3d795067fc73c4cb2f85`.
2. Run a second untouched 100-company promotion cohort using a new seed (`20261103`), preserving unchanged production semantics; require zero overlap, exact evidence integrity, V8 pass, budget/runtime/cost pass, and manually audit all fresh external-phone cases.
3. Only if that second fresh gate passes: remove validation-only workflow files from PR scope, update this state/log/roadmap with QUALIFIED evidence, mark PR #94 ready, merge, and verify post-merge `main` CI.

## 10. NEXT

**NEXT: RETUNE VALIDATION ONLY, then run a second untouched Phase-A qualification. Do not change production extraction/publication semantics unless the failed artifact exposes a correctness defect.**
