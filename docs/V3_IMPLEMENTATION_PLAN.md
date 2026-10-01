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
6. [x] implement a single-fetch annual-report intelligence collector that derives workforce + description from the same PDF/OCR text;
7. [x] prove in focused tests that one annual-report request can produce both observations and that the V3 batch retains the exact H2g eligibility/request class;
8. [ ] wire the validated collector into `run_signalpost_final.py` and project the description in the final contract;
9. [ ] run a fresh qualification and measure company-description reach, precision and runtime.

Offline Baseline CI is green through step 7. The production runner remains unchanged until the runner-integration gate is tested.

Promotion gate: no wrong-entity descriptions in manual audit and meaningful net-new company coverage.

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
