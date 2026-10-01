# Signalpost V3 Implementation Plan

Date: 2026-10-01

Baseline leaderboard result: **42.21/100**

- Recall / coverage: **12.89 / 50**
- Precision / evidence: **18.92 / 30**
- Synthesis: **7.20 / 12**
- UX: **3.20 / 8**

Current production branch already contains the V2 canonical projection and V2.1 deterministic synthesis/product surface. V3 therefore prioritizes **new exact, evidence-backed facts**, not another output-shape rewrite.

## Objective

Develop toward a score with qualification margin, while preserving the strongest property of the current system: exact-entity evidence and deterministic abstention.

Internal engineering target only (not a Builderr score prediction):

- recall / coverage >= 30/50
- precision / evidence >= 24/30
- synthesis >= 9/12
- UX >= 5/8
- total >= 68/100

Stretch target: 75+.

## Rules for every milestone

1. Candidate discovery never proves identity.
2. No fact is published without source URL, retrieval time, content hash and evidence span where applicable.
3. Existing exact-company gates are never weakened for recall.
4. New network work must remain inside the official request/runtime envelope.
5. A source is screened cheaply before a full qualification run.
6. Every promoted feature must transfer to a zero-overlap cohort.
7. ML/AI may rank, extract or synthesize, but deterministic evidence validation decides publication.
8. A failed experiment is documented and dropped rather than merged for feature count.

## Milestone 1 — Annual-report intelligence reuse

**Goal:** turn BRREG annual-report OCR that is already paid for by H2g into additional exact official facts with zero additional network requests on reports already fetched.

First target: a conservative `company_description` / business-activity fact from explicit annual-report sections such as `Virksomhetens art` or `Selskapets virksomhet`.

Implementation sequence:

1. [x] add a pure deterministic business-description extractor over annual-report text;
2. [x] emit a narrowly scoped BRREG `company_profile` observation;
3. [x] project it only when no stronger verified-company-site description already exists;
4. [x] require exact organisation number in the report text;
5. [x] add false-positive guards for group-only / boilerplate passages;
6. [x] reuse the existing H2g annual-report fetch/OCR so one report request can derive workforce + description;
7. [x] preserve the existing H2g eligibility and request class, so V3 does not create a second annual-report fetch path;
8. [x] chain annual-report description projection through the existing final-runner workforce projection path without changing the runner call site;
9. [x] add a machine-readable V3 audit for observed description reach, stronger-source suppression, shared-report reuse and evidence completeness;
10. [x] run fresh zero-overlap qualification, harden observed false positives, then transfer to a second untouched confirmation cohort.

### Milestone 1 qualification evidence

The first 100-company confirmation cohort exposed two useful false-positive classes rather than being promoted blindly:

- an OCR-flattened `Utvikling i resultat og stilling` section was swallowed after a valid activity sentence;
- an investor/financing narrative was incorrectly treated as business activity.

Both cases were converted into deterministic guards and exact regression tests. The consumed cohort was then rerun only as a regression check: **9/9 published annual descriptions were manually acceptable**, with all nine reusing the same annual report as workforce evidence.

A separate untouched final confirmation cohort was then frozen with seed `20261005` after excluding **7,100** previously touched companies. Results:

- 100 companies, 100 unique organisations, **0 overlap**;
- 11 annual-report company-description observations;
- 11 published company-description claims;
- **11/11 manually audited descriptions were company-scope business/activity descriptions**;
- all 11 reused the same BRREG annual report already used for workforce extraction;
- 0 duplicate observations, 0 orphan published descriptions, 0 evidence errors;
- production and V3 audit both passed;
- observed conservative challenge-request charge: **1,370 / 2,000**;
- wall runtime: **442.952 s / 2,400 s**;
- third-party cost: **$0**;
- search API requests: **0**;
- contract errors: **0**;
- change errors: **0**.

Latest branch Baseline CI is green after the hardening and qualification-workflow changes.

**Promotion gate: satisfied for Milestone 1.** The new fact type transferred to an untouched zero-overlap cohort with useful net-new reach and no wrong-entity/non-activity descriptions in manual audit.

## Milestone 2 — Broad official public-activity sources

Screen exact-org, zero/low-cost Norwegian sources before coding full connectors:

- BRREG Støtteregisteret (support/grant activity)
- Doffin procurement data
- Patentstyret open data
- NAV / Arbeidsplassen jobs (revisit only if a stronger bounded lookup strategy beats the previous feed screen)

Only implement a connector when rights are clear, exact entity attribution is deterministic, and a 10–20 company screen suggests useful random-company reach.

## Milestone 3 — ML request ranking

Use the existing labelled identity history (correct sites, namesakes, parents, service providers, parked pages, redirects) to train a lightweight candidate/page ranker.

Allowed role of ML:

- rank which domain/page to spend a request on;
- prioritize legal/contact/about/news/job pages;
- estimate expected evidence yield.

Forbidden role of ML:

- publish a company match solely from a model score;
- generate financial values;
- override deterministic identity/evidence gates.

Candidate models: logistic regression / gradient boosting first. Prefer a small auditable model over a large neural model.

## Milestone 4 — Evidence-bounded AI extraction

Add optional LLM extraction over already-fetched first-party pages and annual-report text.

Rules:

- strict JSON schema;
- every extracted fact must include a verbatim supporting span from supplied text;
- deterministic verifier must find that span in the source text;
- identity is fixed before the LLM sees the document;
- no evidence span -> abstain;
- official numeric financial values remain deterministic.

Targets: business description, products/services, named leaders, operating locations, concrete job postings and dated company activity.

## Milestone 5 — Recall-aware synthesis and UX

Use the expanded canonical facts to improve:

- company brief;
- what changed;
- what is hiring / recent activity;
- explicit unknowns;
- source freshness;
- side-by-side company comparison;
- evidence verification on desktop and mobile.

Do not synthesize unsupported facts.

## Milestone 6 — Revision qualification and freeze

For every candidate revision:

- fresh 100-company smoke in evaluator shape;
- zero terminal drops;
- contract/evidence validation;
- request/runtime/cost report;
- manual audit of every newly published external fact type;
- zero-overlap transfer test;
- exact commit SHA freeze;
- only then submit the next Builderr revision.

## Revision strategy

V3 should be coverage-first. Do not submit tiny cosmetic revisions. Each submitted SHA should represent a measured step change:

1. V3: annual-report intelligence + any other zero-network exact facts that qualify;
2. V4: strongest broad official source and/or ML request ranking if qualified;
3. V5: evidence-bounded AI extraction + final synthesis/UX hardening.

The exact sequence may change only when measured results show a different feature has higher score-relevant return.
