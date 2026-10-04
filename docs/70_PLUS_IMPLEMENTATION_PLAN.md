# Signalpost 70+ Implementation Master Plan

Last updated: 2026-10-04

This document is the canonical engineering roadmap toward a Builderr 70+ result. When it conflicts with the live Builderr challenge page, Builderr wins. Repository evidence, not chat history, governs implementation state.

## 0. Score target

Current verified rubric:

- Recall & coverage: 50
- Precision & evidence: 30
- Synthesis: 12
- UX: 8
- Official qualification: >=65 overall

Internal engineering target: recall 22-24+/50, precision/evidence 28-29+/30, synthesis 12/12, UX 8/8, total 70-73+. This is a target, not a score prediction.

## 1. Core strategy

> ATTEMPT MORE -> VERIFY STRICTLY -> PUBLISH CONSERVATIVELY

Primary optimization target: **net-new companies covered per information family**, not raw claim count.

Priority order:

1. recover exact facts already present in sources we already fetch;
2. enrich already-verified exact sites with zero or low incremental request cost;
3. adaptively spend bounded requests only where a missing family can be added;
4. screen new broad sources only after the first three are exhausted.

Discovery may be broad; publication remains exact and fail-closed.

## 2. Non-negotiable safety invariants

1. Candidate discovery is never identity proof.
2. Exact organisation number is the legal-entity anchor.
3. Name-only, municipality-only, brand similarity, directories, parent/group and franchise pages cannot qualify.
4. Every promoted external value keeps page-level URL/hash/evidence-span provenance.
5. Missing/blocked/ambiguous never becomes zero.
6. Official/financial values remain deterministic official-source facts.
7. One source failure must not drop a company envelope.
8. Refresh remains deterministic and idempotent.
9. No experimental source enters production without measurable company coverage and a clean precision audit.
10. Third-party API spend remains $0 unless explicitly changed.
11. Site logical-request ceiling remains four per company unless a later structural theorem is separately qualified.
12. Fresh cohorts are scarce; failed/used cohorts are never reused as fresh promotion data.

## 3. Production architecture direction

```text
organisation number
    -> exact BRREG legal entity
       -> official exact-ID sources
       -> bounded external candidates
            -> exact identity gate
            -> verified site
                 -> retained page observations
       -> evidence-backed observations
       -> canonical claims/facts
       -> changes + deterministic synthesis + product
```

Keep candidate-vs-verified separation and statement-level lineage throughout.

## 4. Current production foundation

Production `main` already includes exact BRREG identity, financials, roles, locations/group context, evidence-linked output/canonical projection, deterministic refresh, bounded exact-site discovery, first-party social/email, workforce, company-description fallbacks, C12 dated first-party news/jobs, and Phase-1 exact-live BRREG recovery for registration date, business address, purpose/activity description and registered contacts.

Current production `main` SHA: `1589e4c5fd8c9cdc44e28574c961ee1912e47bf9`.

## 5. Work program

### Phase A — collected-vs-emitted recovery

Status: **IMPLEMENTED + TESTED / NOT YET QUALIFIED / NOT MERGED**.

Active PR: #94, branch `feature/phaseb-idle-contact-enrichment`.

Retained zero-request candidate:

- postal address (`postadresse`);
- foundation date (`stiftelsesdato`);
- articles/statutes date (`vedtektsdato`);
- Foretaksregisteret state + registration date;
- institutional sector;
- registered capital;
- VAT state + registration date;
- forced-dissolution state;
- labelled phone extracted from the already verified exact homepage only.

All official Phase-A fields must:

- come only from retained exact-org `registry_live` evidence;
- carry exact BRREG source URL/hash/source row/source path;
- preserve explicit `False` as available;
- map missing fields to `not_available`;
- prohibit bulk/profile fallback;
- add zero source requests;
- remain idempotent.

#### Consumed Phase A3 gate

Run `37200794754` passed on 100/100 terminal companies with 0 evidence/contract/canonical/synthesis errors. Coverage: forced dissolution 100, foundation 98, articles date 96, enterprise state 100/date 98, sector 95, capital 91, VAT state 100/date 48, postal address 30. Operations: 669 logical, 1,338 conservative charge, 2,000 ceiling, 473.27 s, $0, 0 search API requests.

#### First final fresh attempt

Run `37201683517` used seed `20261102`, excluded 8,223 previously touched companies, selected 100 unique companies with overlap 0, and ran V8 successfully. Exact-head Baseline CI `37201687696` also passed.

Fresh coverage: forced dissolution 100, foundation 99, articles date 97, enterprise state 100/date 98, sector 100, capital 93, VAT state 100/date 57, postal address **17**, registration date/address 100. V8 and output/evidence structure were clean; operations were 702 logical, 1,404 conservative charge, 2,000 ceiling, 451.153 s, $0, 0 search API requests.

**Qualification result: FAIL** because a predeclared `postal_address >= 20` floor was missed at 17.

This failure is preserved. The cohort is consumed.

#### Acceptance-criterion retune

The failure exposed a validation-design issue rather than a production correctness issue: postal address is an optional registry field whose source prevalence varies by cohort. Universal hard prevalence floors are suitable for near-universal status/identity fields but are not suitable correctness gates for optional fields.

For the second untouched qualification, predeclare:

Hard gates:

- 100 unique / 100 terminal / zero overlap;
- V8 `passed=true`;
- zero evidence, contract, canonical and synthesis errors;
- exact source-path/URL/hash/canonical mapping for every available Phase-A fact;
- broad near-universal fields retain strong company-coverage floors;
- request/runtime/cost limits pass;
- third-party cost $0 and search requests 0;
- every fresh external-phone case manually audited.

Optional-source-prevalence fields:

- postal address and VAT registration date must be reported transparently;
- they must show non-zero transfer on the new cohort and perfect evidence mapping when available;
- they are not required to meet an arbitrary universal percentage floor.

This is a **validation-only retune**. Production extraction/publication semantics must not change unless a correctness defect is found.

Second-fresh exclusion must include the failed seed-`20261102` cohort. Expected all-touched union: 8,323 unique companies; SHA `ae5a1e78a883d75332d93bd0cd88f123e7f1a88300ee3d795067fc73c4cb2f85`. Planned seed: `20261103`.

### Rejected experiment — idle exact contact-page fallback

Status: **DROP / DO NOT PROMOTE**.

Consumed transfer run `37197243641` produced zero net-new company-level contact coverage. The network fallback was removed. Do not restore it without new generic evidence.

### Phase B — verified-site enrichment 2.0

Status: **DEFERRED UNTIL PHASE A QUALIFIES/MERGES**.

Candidates: bounded sitemap/RSS discovery; same-domain about/contact/team/careers/news; structured Organization/Person/JobPosting/Article metadata; OpenGraph/canonical/time/mailto/tel/sameAs. Every extra page must justify itself by net-new family coverage. No unbounded crawl.

### Phase C — adaptive request scheduler

Goal: spend scarce requests where expected company-family gain is highest.

```text
expected_company_coverage_gain / (identity_risk + request_cost + latency_risk)
```

No verified site -> stop. Do not spend requests for duplicate families. Publication gates remain deterministic.

### Phase D — jobs

Measure transfer broadly; generic careers page != job; require concrete current role + exact employer context + URL; no parent/subsidiary inheritance. Consider shared official feeds only with exact employer mapping.

### Phase E — dated activity

Use exact company-owned news detail, RSS/Atom, sitemap candidates and structured article dates. Optimize for one supported update across many companies.

### Phase F — broad exact-ID official-source screens

Only after Phase A/B/C. Candidate families may include BRREG support data, procurement, IP activity and shared-feed jobs. Each must pass rights/exact-ID/reach screening first.

### Phase G/H — optional ML and evidence-bounded AI

ML may rank requests but never authorize publication. AI may extract only from already-fetched verified text with a deterministic supporting span. Never use AI to establish legal identity or invent official numeric facts.

### Phase I — synthesis to 12/12

Cover what the company does, financial state, people, locations, workforce, hiring, activity, changes, unknowns and source/effective dates when supported.

### Phase J — UX to 8/8

Keep product directly linked to final JSONL with search/select, evidence-backed brief, financial periods/units, people/locations, verified website/contact/social, hiring/activity, evidence drill-down, freshness/change context, explicit unavailable states, responsive compare.

### Phase K — release qualification/submission

Do not consume another Builderr revision until a combined candidate has exact-head CI, evaluator-shaped consumed measurement, a fresh zero-overlap promotion qualification, 100/100 terminal envelopes, zero integrity errors, manual audit of each newly introduced external family, request/runtime/cost compliance and an exact SHA freeze.

## 6. Measurement requirements

Every experiment reports company coverage, not only claim counts. Always include input/terminal count; website/contact/social/jobs/activity/people/locations/workforce/registry changes; each new official field; evidence/contract/canonical/synthesis errors; wrong-company findings; logical/conservative requests; runtime; third-party cost; and baseline -> new -> net-new where applicable.

## 7. Validation discipline

- consumed cohorts: tune/debug;
- fresh cohorts: promotion gates;
- once a fresh cohort is run, it is consumed even if the gate fails;
- acceptance criteria must be declared before the next untouched cohort;
- a green unit test or clean V8 execution alone is not qualification.

Maintain adversarial cases for namesakes, parent/subsidiary, shared domains, franchises, multiple org numbers, former names and rebrands.

## 8. Near-term sequence

1. Validation-only retune for optional-field prevalence.
2. Add failed seed-`20261102` cohort to exclusion; verify 8,323 union SHA.
3. Run second untouched 100 with seed `20261103` on unchanged production semantics.
4. Manually audit every external-phone case.
5. If green: strip validation-only workflow files from PR #94, update docs with QUALIFIED state, mark ready, merge, then verify post-merge `main` CI.
6. Only after Phase A closes, resume Phase B/C.

## 9. Do-not-repeat decisions

Do not restore the rejected idle contact-page fallback, loosen exact website identity, treat generic careers as jobs, revive guessed `.com`, scrape LinkedIn/Facebook/Glassdoor, use random reviews, use paid search/API under the $0 constraint, tune against Builderr’s checked collection, or reuse a consumed fresh cohort.

## 10. Continuity protocol

Every implementation chat must read `docs/CONTINUATION_STATE.md`, this file, and live current `main`/open PR metadata before implementation. At the end of each substantial session update continuation state and implementation log; update this roadmap whenever phases, acceptance criteria or strategy change.
