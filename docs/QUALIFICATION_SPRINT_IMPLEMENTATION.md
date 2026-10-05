# Signalpost Qualification Sprint — Small-Milestone Plan

Last updated: 2026-10-05

## Objective

Raise the next Builderr revision above the 65 qualification threshold without weakening exact-company precision. The latest official result is recall-limited and evidence-limited; synthesis and UX are already strong and should not be redesigned casually.

Guiding rule:

> ATTEMPT MORE -> VERIFY STRICTLY -> PUBLISH CONSERVATIVELY

## Live starting point

- `main`: `f80c485fe65684db7dea8401e483a544bb0bb773`
- PR #99 owner-veto hardening: merged
- post-merge Baseline CI `37317529054`: PASS
- failed fresh Phase-11 cohort seed `20261104`: permanently consumed
- theoretical conservative request ceiling: 2,000 / 2,000 for 100 companies
- no new fresh Phase-11 cohort should be consumed until the qualification sprint shows meaningful improvement

## Milestone map

### Q0 — precision safety closure

Status: COMPLETE.

- wrong explicit site owner is a hard negative unless exact target org-number evidence overrides it;
- consumed replay removed only the four contaminated Interiørkupp-derived publications;
- 0 other external publications changed;
- PR #99 merged and post-merge CI passed.

### Q1 — evaluator-visible evidence audit

Goal: measure what an evaluator can actually reopen from the final JSONL/product.

Small deliverables:

1. Add an offline evidence-visibility auditor.
2. For every available claim verify visible URL, retrieval time, supporting span and content hash.
3. For company-owned/external claims separately report whether exact-company identity proof and extraction method are visible.
4. Report field-level completeness and issue rows.
5. Run against consumed/dev artifacts only; do not consume a fresh cohort.
6. Use the audit to decide whether the next change is projection-only or data-collection work.

Promotion gate:

- no collection semantics change;
- no request-budget change;
- deterministic tests green;
- baseline CI green;
- audit output identifies concrete evaluator-facing gaps.

### Q2 — evidence projection hardening

Only if Q1 confirms gaps.

- expose exact-company identity proof alongside company-owned evidence;
- expose extraction method where already known;
- preserve URL / retrieval time / content hash / supporting text;
- preserve publication/effective/reporting dates where relevant;
- add validation that projected metadata matches backing evidence;
- no invented provenance and no duplicated source fetches.

### Q3 — website reach recovery

Goal: materially increase exact verified-site companies without weakening identity.

- use consumed/dev cohorts first;
- candidate nomination is never proof;
- search snippets/domain guesses cannot become evidence;
- independent first-party fetch + current identity gate remains mandatory;
- do not repeat previously exhausted deterministic-domain/Common-Crawl approaches unchanged.

Promotion gate: meaningful company-level gain, 0 known wrong-company publications, evidence complete, request theorem re-proved if allocation changes.

### Q4 — social profile coverage

Goal: make social no longer structurally zero.

- reuse already-fetched verified first-party pages;
- publish only explicitly declared profile URLs;
- no social-platform scraping required;
- keep the narrow claim that the verified company page declared the profile.

### Q5 — hiring coverage

Goal: separate a verified hiring/recruitment surface from concrete vacancies.

- careers/recruitment surface may support a hiring signal;
- careers page alone must not become a specific job posting;
- concrete jobs require role/application evidence and current-job semantics;
- reuse existing page budget wherever possible.

### Q6 — dated first-party news/activity

Goal: make dated activity no longer structurally zero while preserving Phase-4 date precision.

- reuse discovered same-domain news/activity links and existing fetched pages first;
- exact page URL + date evidence + span + hash required;
- generic CMS placeholders remain rejected;
- support awards stay typed as official support, never relabelled as company news.

### Q7 — consumed/dev transfer measurement

Before another fresh cohort, compare current production vs sprint candidate on already-consumed/dev material:

- verified website companies;
- social companies;
- hiring companies;
- concrete job companies;
- dated activity companies;
- evidence-complete external claims;
- known wrong-company publications;
- logical/conservative requests;
- runtime and $ cost;
- synthesis/UX regressions.

Proceed only if the bundle is materially stronger.

### Q8 — fresh Phase-11 attempt #2

Only after Q1-Q7 are green.

- build all-touched exclusion set including the failed seed `20261104` cohort;
- freeze exclusion count/SHA, seed and cohort SHA before results;
- use actual V8 evaluator path;
- require 100/100 terminal and all machine integrity gates;
- manually audit every new external-family publication and all support awards;
- inspect evidence reopenability;
- freeze output/report/product/artifact hashes;
- decide GO / NO-GO.

### Q9 — Builderr revision

Submit only a materially stronger qualified bundle. Internal release target:

- recall trajectory: 18-20+
- evidence: 28+
- synthesis: 12
- UX: 8
- 0 known material wrong-company publications

## Current action

Q1 is active. The first implementation is an offline evidence-visibility audit so we can distinguish “we already have the fact but hide proof” from “we do not collect the fact at all.”
