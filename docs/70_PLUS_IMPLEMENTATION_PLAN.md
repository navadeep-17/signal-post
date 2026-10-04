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

Internal engineering target for the next major revision:

- recall 22-24+/50;
- precision/evidence 28-29+/30;
- synthesis 12/12;
- UX 8/8;
- total 70-73+.

This is a target, not a score prediction.

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
6. Financial and official registry values remain deterministic official-source facts.
7. One source failure must not drop a company envelope.
8. Refresh remains deterministic and idempotent.
9. No experimental source enters production without measurable net-new company coverage and a clean precision audit.
10. Third-party API spend remains $0 unless explicitly changed.
11. Site logical-request ceiling remains four per company unless a later structural theorem is separately qualified.
12. Fresh cohorts are scarce validation assets; do not consume them while a candidate is still moving.

## 3. Production architecture direction

```text
organisation number
    -> exact BRREG legal entity
       -> official exact-ID sources
       -> bounded external candidates
            -> exact identity gate
            -> verified site
                 -> retained page observations
       -> evidence-backed source observations
       -> canonical claims/facts
       -> changes + deterministic synthesis + product
```

Keep candidate-vs-verified separation and statement-level lineage throughout.

## 4. Current production foundation

Production already includes:

- exact BRREG identity, live/bulk registry context, financials, roles, locations and group context;
- evidence-linked output contract and canonical projection;
- deterministic refresh/change tracking;
- bounded website discovery via registry hints, registry-email domain, deterministic `.no`, Wikidata exact-org candidates and hyphenated `.no` fallback;
- hardened parent/namesake/parked/shared-domain conflict guards;
- first-party social links and same-domain contact email;
- registry and annual-report workforce;
- annual-report / registry description fallback;
- C12 bounded dated first-party news;
- C12 bounded current first-party jobs;
- Phase 1 exact-live BRREG recovery for registration date, business address, registered purpose, activity/description, registered email, phone and mobile;
- request/runtime/cost accounting with $0 third-party API spend.

## 5. Work program

### Phase A — current-main family coverage + collected-vs-emitted audit

Status: **AUDIT SUBSTANTIALLY COMPLETE; PHASE NOT CLOSED**.

Completed evidence:

- [x] frozen evaluator-shaped Phase-1 cohort available and audited;
- [x] company-family matrix produced for website/contact/social/jobs/activity/people/locations/workforce/registry changes;
- [x] remaining zero-risk projection gaps identified;
- [x] request/runtime/cost and precision findings recorded;
- [x] one low-cost external network candidate tested on consumed cohorts and rejected for zero net-new company coverage.

Key family baseline on the audited Phase-1 100:

- verified site 8;
- external contact email 4;
- registered contact email 21;
- any registered phone/mobile 29;
- social 3;
- strict jobs 0;
- dated company activity 1;
- workforce 100;
- registry changes 100;
- people 100;
- registered locations 81;
- careers surface 2.

PR #94's zero-network additions measured on the same consumed cohort:

- postal address available for 30 companies;
- labelled exact-homepage phone for 2 companies;
- phone-family company union 31 vs 29 baseline (+2);
- no contract/canonical/synthesis errors;
- no new source request for those two features.

#### Phase A2 — exact-live BRREG zero-request recovery

**This is the current highest-priority implementation.**

The exact organisation-number BRREG live response already fetched by production contains broad fields that are still dropped before projection. Audited availability is approximately:

| Exact BRREG field family | audited availability / 100 |
|---|---:|
| foundation date (`stiftelsesdato`) | 98 |
| Foretaksregisteret registration date | 98 |
| statutes/articles date (`vedtektsdato`) | 96 |
| institutional sector code/description | 95 |
| capital/share-capital structure | 91 |
| registered in Foretaksregisteret state | 100 |
| registered in VAT state | 100 |
| VAT registration date | 48 |

Implementation contract:

- retain selected values in `official.normalize_entity()` from the exact live response;
- project only from retained `evidence.registry_live` whose exact org/URL/hash is already attached;
- precise BRREG JSON source path per claim;
- explicit `False` booleans remain publishable facts;
- absent values become `not_available`, never inferred;
- no bulk/profile fallback for Phase A2 managed fields;
- canonical mappings stay under `company.*`;
- zero added source requests;
- idempotence and source-evidence regressions required.

Initial Phase A2 target set:

1. foundation date;
2. enterprise/Foretaksregisteret registration state + date;
3. institutional sector;
4. registered capital structure;
5. VAT registration state + date.

`vedtektsdato` may be added in the same patch if semantics/source shape remain unambiguous; otherwise defer rather than guess.

Phase A closes only after Phase A2 is measured and no similarly broad exact-live omission remains.

### Rejected experiment — idle exact contact-page fallback

Status: **DROP / DO NOT PROMOTE**.

Consumed transfer workflow `37197243641` ran full V8 successfully but failed the explicit promotion bar: a retained contact page produced one phone company (`977117186`) and **zero net-new company-level contact coverage**. The extra network fallback was removed.

Do not restore it without new, generic evidence that it adds net-new companies at acceptable request cost.

### Phase B — verified-site enrichment 2.0

Status: **DEFERRED UNTIL PHASE A2 CLOSES**.

Goal: make already-verified sites yield more distinct high-confidence families without weakening identity.

Candidates after Phase A2:

- ranked sitemap/RSS discovery;
- same-domain about/contact/team/careers/news pages;
- structured `Organization`, `LocalBusiness`, `Person`, `JobPosting`, `NewsArticle`, `Article` extraction;
- OpenGraph/canonical/`<time>`/`mailto:`/`tel:`/`sameAs` from already qualified pages.

Every extra page must justify itself by net-new family coverage. Do not unbounded-crawl.

### Phase C — adaptive request scheduler

Goal: spend scarce requests where expected company-family gain is highest.

Conceptual ranking:

```text
expected_company_coverage_gain / (identity_risk + request_cost + latency_risk)
```

Rules:

- no verified site -> stop site enrichment;
- do not spend requests on already-covered families merely for duplicate claims;
- explicit hiring evidence -> job detail before generic news;
- missing activity with no hiring signal -> dated news/RSS candidate;
- low expected gain -> abstain.

Publication gates remain deterministic even if request ranking later uses ML.

### Phase D — job coverage expansion

- measure M4 transfer on broad cohorts;
- preserve generic careers page != job;
- require concrete current role title + exact employer context + role/application URL;
- parent target cannot inherit subsidiary jobs;
- consider a shared NAV feed only if exact employer organisation-number mapping can be done efficiently and broadly.

### Phase E — dated activity expansion

Use exact company-owned news detail, RSS/Atom, sitemap candidates, structured article metadata and explicit publication dates. Optimize for one supported update across many companies rather than many updates on one company.

### Phase F — broad exact-ID official-source screens

Only after Phase A2/B/C. Candidate families include BRREG support data, procurement, IP activity and improved shared-feed jobs. Each candidate must pass rights/exact-ID/reach screen before a 100-company run.

### Phase G — ML request ranking (optional)

ML may rank candidates/pages but may not authorize publication. Deterministic identity remains authoritative.

### Phase H — evidence-bounded AI extraction (optional)

AI may extract only from already-fetched, already-verified text, with an exact supporting span that a deterministic verifier can locate. No span = no fact. Never use AI to establish legal identity or invent official numeric values.

### Phase I — synthesis to 12/12

Every brief should cover, when supported: what the company does, financial state, people, locations, workforce, hiring, public activity, changes, unknowns and source/effective dates. Unknowns remain first-class.

### Phase J — UX to 8/8

Keep the product directly linked to final generated JSONL. Required evaluator-visible capabilities remain search/select, evidence-backed brief, financial periods/units, people/locations, verified website/contact/social, hiring/activity, evidence drill-down, freshness/change context, explicit unavailable states, responsive operation and descriptive compare.

### Phase K — release qualification and submission

Do not consume another Builderr revision until a combined release candidate has:

- exact-head CI green;
- evaluator-shaped consumed measurement green;
- one fresh zero-overlap 100-company promotion qualification;
- 100/100 terminal envelopes;
- zero contract/canonical/synthesis/evidence-integrity errors;
- manual precision audit of every newly introduced external family;
- request/runtime/cost report within limits;
- exact SHA freeze.

Bundle meaningful recall improvements into one revision.

## 6. Measurement harness requirements

Every experiment reports company coverage, not only claim counts.

Minimum matrix:

| Metric | Required |
|---|---|
| input / terminal companies | yes |
| verified website companies | yes |
| registered + external contact companies | yes |
| social-profile companies | yes |
| strict job companies | yes |
| dated-activity companies | yes |
| people/leadership companies | yes |
| location/workplace companies | yes |
| workforce companies | yes |
| registry-change companies | yes |
| each new official Phase-A2 field company count | yes |
| evidence/contract/canonical/synthesis errors | yes |
| wrong-company publications | yes |
| logical + conservative requests | yes |
| runtime/latency where available | yes |
| third-party cost | yes |

Always show baseline -> new -> net-new companies by family.

## 7. Validation discipline

Use disjoint cohorts:

- development/consumed cohorts: tune and debug;
- fresh validation cohort: promotion gate;
- final untouched release audit only after the candidate freezes.

Maintain adversarial cases for namesakes, parent/subsidiary, shared/group domains, franchises, multiple org numbers, former names and rebrands.

A green unit test is never sufficient to qualify a data-source strategy.

## 8. Near-term sequence

1. Phase A2 exact-live BRREG recovery.
2. Exact-head regression/Baseline CI.
3. Consumed evaluator-shaped coverage measurement against Phase-1 baseline.
4. If broad and clean, one fresh zero-overlap 100 qualification.
5. Then decide whether the stabilized candidate should be split into a Phase-A PR or retitle/restructure PR #94 before merge.
6. Only after Phase A closes, return to Phase B/C website enrichment.

## 9. Do-not-repeat decisions

Do not prioritize broad frontend rewrites, sentiment, social-platform scraping, Google Places scraping, random reviews, guessed `.com`, or unbounded connector/source hunting. Do not restore the rejected idle contact-page fallback without new net-new coverage evidence.

## 10. Continuity protocol

Every implementation chat must read:

1. `docs/CONTINUATION_STATE.md` completely;
2. this file;
3. live current `main` and open PR metadata.

At the end of each substantial session:

1. update `docs/CONTINUATION_STATE.md`;
2. append `docs/IMPLEMENTATION_LOG.md`;
3. update this roadmap when strategy/completed phases/criteria changed;
4. record exact SHAs, runs, artifacts, coverage, precision, requests/runtime/cost, blockers and next actions.

The repository, not conversation memory, is the source of truth.
