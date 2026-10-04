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
9. No experimental feature enters production without measurable transfer and a clean precision audit.
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

Production `main` before the Phase-A merge already includes exact BRREG identity, financials, roles, locations/group context, evidence-linked output/canonical projection, deterministic refresh, bounded exact-site discovery, first-party social/email, workforce, company-description fallbacks, C12 dated first-party news/jobs, and Phase-1 exact-live BRREG recovery for registration date, business address, purpose/activity description and registered contacts.

Pre-merge production `main` SHA: `1589e4c5fd8c9cdc44e28574c961ee1912e47bf9`.

## 5. Work program

### Phase A — collected-vs-emitted exact BRREG recovery

Status: **IMPLEMENTED + TESTED + FRESH-QUALIFIED / NOT YET MERGED**.

Active PR: #94, branch `feature/phaseb-idle-contact-enrichment`.

Retained zero-request candidate:

- postal address (`postadresse`);
- foundation date (`stiftelsesdato`);
- articles/statutes date (`vedtektsdato`);
- Foretaksregisteret state + registration date;
- institutional sector;
- registered capital;
- VAT state + registration date;
- forced-dissolution state.

All retained official Phase-A fields:

- come only from exact-org `registry_live` evidence;
- carry exact BRREG source URL/hash/source row/source path;
- preserve explicit `False` as available;
- map missing fields to `not_available`;
- prohibit bulk/profile fallback;
- add zero source requests;
- remain idempotent.

#### Consumed Phase A3 gate

Run `37200794754` passed on 100/100 terminal companies with zero evidence/contract/canonical/synthesis errors. Coverage: forced dissolution 100, foundation 98, articles date 96, enterprise state 100/date 98, sector 95, capital 91, VAT state 100/date 48, postal address 30. Operations: 669 logical, 1,338 conservative charge, 2,000 ceiling, 473.27 s, $0, 0 search API requests.

#### First final fresh attempt — preserved failure

Run `37201683517`, seed `20261102`, excluded 8,223 previously touched companies, selected 100 unique with overlap 0. V8 itself passed and evidence/output checks were clean, but postal address was 17 against a predeclared `>=20` prevalence floor. Result: **FAIL**. The cohort is consumed and remains documented as a failure.

#### Second untouched fresh qualification — PASS

Run `37203580574` on exact measurement head `a7192c4fe9f47e26fcc2a0d3b632e86a1586cfe0`.

- all-touched exclusion: 8,323 unique companies;
- exclusion SHA: `ae5a1e78a883d75332d93bd0cd88f123e7f1a88300ee3d795067fc73c4cb2f85`;
- seed: `20261103`;
- fresh cohort: 100 unique, overlap 0;
- cohort SHA: `4078579d4a581da0b8d56e4d03d567c4032d43e93c8bb94ee3c02b140b651e40`;
- coverage: forced dissolution 100, foundation 100, articles date 99, enterprise state 100/date 98, sector 100, capital 98, VAT state 100/date 48, postal address 23, registration date/address 100;
- 100/100 terminal;
- evidence/contract/canonical/synthesis errors: 0;
- 666 logical requests;
- 1,332 conservative charge / 2,000 ceiling;
- runtime 460.916 s;
- cost $0;
- search requests 0;
- artifact `phasea-final-fresh-disjoint-100-v2`, ID `11304401011`, digest `31e12e11f2746dcf8c0b6454ab6052ab44281176363b6934889d22d57a08800b`.

**Phase A retained exact-BRREG/postal behavior is qualified.**

#### External homepage phone — rejected before merge

The zero-network labelled-phone feature had +2 net-new phone-family companies on one consumed cohort but did not transfer at company-family level:

- first fresh: 3 external-phone companies, registered phone/mobile union 38, combined union still 38 -> 0 net-new;
- second fresh: 1 external-phone company, registered phone/mobile union 33, combined union still 33 -> 0 net-new.

The fresh case (`VEST GULV AS`) was precision-correct, but BRREG already carried the same phone. Decision: **DROP** the phone feature and remove it from PR #94 before merge. Do not interpret precision-only duplication as coverage gain.

### Rejected experiment — idle exact contact-page fallback

Status: **DROP / DO NOT PROMOTE**.

Consumed transfer run `37197243641` produced zero net-new company-level contact coverage. The network fallback was removed. Do not restore it without new generic evidence.

### Phase B — verified-site enrichment 2.0

Status: **NEXT AFTER PHASE A MERGE**.

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

After Phase A/B/C. Candidate families may include BRREG support data, procurement, IP activity and shared-feed jobs. Each must pass rights/exact-ID/reach screening first.

### Phase G/H — optional ML and evidence-bounded AI

ML may rank requests but never authorize publication. AI may extract only from already-fetched verified text with a deterministic supporting span. Never use AI to establish legal identity or invent official numeric facts.

### Phase I — synthesis to 12/12

Cover what the company does, financial state, people, locations, workforce, hiring, activity, changes, unknowns and source/effective dates when supported.

### Phase J — UX to 8/8

Keep product directly linked to final JSONL with search/select, evidence-backed brief, financial periods/units, people/locations, verified website/contact/social, hiring/activity, evidence drill-down, freshness/change context, explicit unavailable states, responsive compare.

### Phase K — release qualification/submission

Do not consume another Builderr revision until a combined candidate has exact-head CI, evaluator-shaped consumed measurement, a fresh zero-overlap promotion qualification, 100/100 terminal envelopes, zero integrity errors, manual audit of newly introduced external families, request/runtime/cost compliance and an exact SHA freeze.

## 6. Measurement requirements

Every experiment reports company coverage, not only claim counts. Always include input/terminal count; website/contact/social/jobs/activity/people/locations/workforce/registry changes; each new official field; evidence/contract/canonical/synthesis errors; wrong-company findings; logical/conservative requests; runtime; third-party cost; and baseline -> new -> net-new where applicable.

## 7. Validation discipline

- consumed cohorts: tune/debug;
- fresh cohorts: promotion gates;
- once a fresh cohort is run, it is consumed even if the gate fails;
- acceptance criteria are declared before untouched cohorts;
- a green unit test or clean V8 execution alone is not qualification;
- a feature that is precise but adds zero net-new family coverage on fresh transfer data should normally be dropped rather than merged for feature count.

Maintain adversarial cases for namesakes, parent/subsidiary, shared domains, franchises, multiple org numbers, former names and rebrands.

## 8. Near-term sequence

1. Exact-head Baseline CI on the cleaned Phase-A branch after removing rejected phone code and validation-only workflows.
2. Update PR #94 title/body to the qualified exact-BRREG scope and mark ready.
3. Merge only if exact-head CI is green.
4. Verify post-merge `main` CI and record merge SHA.
5. Then resume Phase B/C, starting from measured current-main company-family coverage rather than feature guesses.

## 9. Do-not-repeat decisions

Do not restore the rejected idle contact-page fallback or the rejected duplicate external-phone feature without new net-new coverage evidence. Do not loosen exact website identity, treat generic careers as jobs, revive guessed `.com`, scrape LinkedIn/Facebook/Glassdoor, use random reviews, use paid search/API under the $0 constraint, tune against Builderr’s checked collection, or reuse a consumed fresh cohort.

## 10. Continuity protocol

Every implementation chat must read `docs/CONTINUATION_STATE.md`, this file, and live current `main`/open PR metadata before implementation. At the end of each substantial session update continuation state and implementation log; update this roadmap whenever phases, acceptance criteria or strategy change.
