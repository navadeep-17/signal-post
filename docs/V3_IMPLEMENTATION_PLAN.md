# Signalpost V3 Implementation Plan — Historical Milestone Record

Date: 2026-10-01

> **Status:** historical milestone document. Do not use this file as the current implementation roadmap.
>
> Current source of truth:
>
> 1. `docs/CONTINUATION_STATE.md` — exact current state and NEXT action
> 2. `docs/70_PLUS_IMPLEMENTATION_PLAN.md` — current 70+ strategy and acceptance gates
> 3. `docs/IMPLEMENTATION_LOG.md` — append-only implementation history

This file is retained because it records the reasoning and qualification evidence behind V3-era milestones, especially annual-report intelligence reuse. Some score snapshots and future sequencing below have since been superseded.

Baseline leaderboard result at the time this plan was written: **42.21/100**

- Recall / coverage: **12.89 / 50**
- Precision / evidence: **18.92 / 30**
- Synthesis: **7.20 / 12**
- UX: **3.20 / 8**

The production branch already contained the V2 canonical projection and V2.1 deterministic synthesis/product surface. V3 therefore prioritized **new exact, evidence-backed facts**, not another output-shape rewrite.

## Historical objective

Develop toward a score with qualification margin, while preserving the strongest property of the system: exact-entity evidence and deterministic abstention.

Historical internal engineering target only:

- recall / coverage >= 30/50
- precision / evidence >= 24/30
- synthesis >= 9/12
- UX >= 5/8
- total >= 68/100

Stretch target: 75+.

## Rules that remain valid

1. Candidate discovery never proves identity.
2. No fact is published without source URL, retrieval time, content hash and evidence span where applicable.
3. Existing exact-company gates are never weakened for recall.
4. New network work must remain inside the official request/runtime envelope.
5. A source is screened cheaply before a full qualification run.
6. Every promoted feature must transfer to a zero-overlap cohort.
7. ML/AI may rank, extract or synthesize, but deterministic evidence validation decides publication.
8. A failed experiment is documented and dropped rather than merged for feature count.

## Milestone 1 — Annual-report intelligence reuse

**Goal:** turn BRREG annual-report OCR that was already paid for by H2g into additional exact official facts with zero additional network requests on reports already fetched.

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

**Promotion gate was satisfied for Milestone 1.**

## Historical later milestones

The following were the intended V3 sequence at the time. They are retained only for historical context; the current roadmap may sequence them differently based on later measurements.

### Milestone 2 — Broad official public-activity sources

Candidates considered:

- BRREG Støtteregisteret
- Doffin procurement data
- Patentstyret open data
- NAV / Arbeidsplassen jobs

### Milestone 3 — ML request ranking

Allowed role of ML:

- rank which domain/page to spend a request on;
- prioritize legal/contact/about/news/job pages;
- estimate expected evidence yield.

Forbidden role of ML:

- publish a company match solely from a model score;
- generate financial values;
- override deterministic identity/evidence gates.

### Milestone 4 — Evidence-bounded AI extraction

Historical intended rule:

> No supporting source span -> no published fact.

Identity remains deterministic and official numeric financial values remain non-generative.

### Milestone 5 — Recall-aware synthesis and UX

Historical targets included company briefs, changes, hiring/activity, unknowns, freshness, comparisons and evidence verification.

### Milestone 6 — Revision qualification and freeze

The enduring rule is still valid: fresh evaluator-shaped run, evidence validation, manual audit, zero-overlap transfer, exact SHA freeze, then submission.

## Supersession note

Subsequent C12 work added stronger exact first-party social provenance, dated news detail and bounded current first-party jobs. The next implementation decision must therefore start from current `main` and current measured family coverage, not from the old V3 sequence above.

See `docs/CONTINUATION_STATE.md` for the exact current NEXT action.
