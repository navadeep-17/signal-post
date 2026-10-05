# Signalpost Qualification Sprint — Small-Milestone Plan

Last updated: 2026-10-05

## Objective

Raise the next Builderr revision above the qualification threshold without weakening exact-company precision. Recall remains the main bottleneck; evidence visibility has now been materially hardened. Synthesis and UX are already strong and should not be redesigned casually.

Guiding rule:

> ATTEMPT MORE -> VERIFY STRICTLY -> PUBLISH CONSERVATIVELY

## Live state

- production `main`: `fec192cc5d4c9e38260168d2c29156288e224b48` after PR #100;
- PR #99 owner-veto hardening: merged + post-merge CI green;
- PR #100 Q1/Q2 evidence audit/provenance projection: merged + post-merge CI green;
- Q3 search-assisted website discovery: retained as draft experiment, **production HOLD** after 1/20 consumed proxy transfer;
- failed fresh Phase-11 cohort seed `20261104`: permanently consumed;
- theoretical conservative request ceiling: **2,000 / 2,000** for 100 companies;
- no new fresh Phase-11 cohort should be consumed until consumed/dev transfer is materially stronger.

## Milestone map

### Q0 — precision safety closure

Status: **COMPLETE**.

- wrong explicit site owner is a hard negative unless exact target org-number evidence overrides it;
- consumed replay removed only the four contaminated Interiørkupp-derived publications;
- 0 other external publications changed;
- PR #99 merged and post-merge CI passed.

### Q1 — evaluator-visible evidence audit

Status: **COMPLETE**.

Consumed Phase-11 owner-veto replay:

- 100 companies;
- 4,611 available claims;
- 4,611 / 4,611 core-evidence-complete;
- 4,611 / 4,611 reopenable HTTP(S) sources;
- 169 identity-sensitive claims;
- pre-Q2: 0 / 169 evaluator-visible identity proof and extraction method;
- retained profiles already contained the proof.

Conclusion: the immediate evidence gap was projection visibility, not missing core evidence.

### Q2 — evidence projection hardening

Status: **COMPLETE / MERGED / POST-MERGE GREEN**.

Implemented:

- deterministic zero-network provenance projection;
- observation `identity_proof` -> final evidence;
- retained observation `strategy` -> `extraction_method`;
- verified website `identity_assessment` -> website-backed `identity_proof`;
- website identity method -> `extraction_method`;
- observation joins require exact `observation_id`;
- website joins require exact source URL + content SHA-256;
- existing visible provenance is never overwritten.

Consumed monotonic validation:

- 0 claim changes;
- 0 evidence-ID changes;
- 0 core-evidence changes;
- only provenance fields added.

PR #100 merged as `fec192cc5d4c9e38260168d2c29156288e224b48`; post-merge Baseline CI `37322738569`: PASS.

### Q3 — website reach recovery

Status: **EXPERIMENT VALIDATED / PRODUCTION HOLD**.

A guarded OpenAI web-search nominator was rebased as an experiment. Provider output is URL nomination only; independently fetched destination-page evidence remains the sole publication authority.

Precision hardening added:

- one hosted search-call ceiling;
- explicit provider dollar-budget preflight;
- max two independently crawled candidates;
- wrong-org and multi-entity organisation-number veto;
- quarantined candidate pages never persisted.

Consumed replay:

- adversarial set: 1/4 accepted, 3/4 safely quarantined;
- deterministic 20-company public-search proxy: 1/20 accepted, 3/20 quarantined, 16/20 no candidate;
- accepted proxy company: PREG BARNEHAGER ÅLESUND AS;
- wrong-company publications: 0;
- Q3 replay workflow `37328342354`: PASS;
- artifact `11352149982`, digest `sha256:5611c946e0349c0bf2ababf2b33816f81525fd7b2ff212f6e1f25c98045256e7`.

Decision: 5% consumed transfer is below the earlier provisional >=5/20 target. Keep PR #101 as a reusable draft experiment; do not integrate or consume a fresh Q3 cohort.

### Q4 — social/contact coverage

Status: **MEASUREMENT COMPLETE / SOURCE-REACH BLOCKED**.

Consumed external-gap audit:

- verified company sites: 6/100;
- profile handles: 4/100 overall, **4/6 = 66.7% conditional on a verified site**;
- first-party contact email: 6/100 overall, **6/6 = 100% conditional on a verified site**.

Decision: current social/contact extraction already works when an exact site exists. The primary bottleneck is upstream verified-site reach, not the Q4 extractors. Do not spend another milestone retuning them without new evidence.

### Q5 — hiring coverage

Status: **UNCHANGED DESIGN HOLD**.

Among the six verified consumed sites:

- careers links: 0/6;
- active-hiring markers: 0/6;
- job-listing candidates: 0/6;
- final `external.careers_page`: 0/100;
- final `external.job_posting`: 0/100.

Decision: the existing first-party Q5 path has no measured consumed transfer surface. Do not consume a fresh cohort for the unchanged design.

### Q6 — dated first-party news/activity

Status: **UNCHANGED DESIGN HOLD**.

Among the six verified consumed sites:

- retained news-detail links: 0/6;
- final `external.company_update`: 0/100.

Decision: the existing first-party Q6 path has no measured consumed transfer surface. Official support awards remain typed official events and must not be relabelled as company-authored news.

### Q6.1 — request-budget reality check

Status: **MEASURED**.

Consumed run:

- observed logical requests: 682;
- observed conservative charge: 1,364 / 2,000;
- observed unused charge: 636.

But the structural theorem remains:

- theoretical conservative ceiling: 2,000 / 2,000;
- structural headroom: **NONE PROVEN**.

Low-yield discovery currently occupying theorem capacity includes:

- H1g attempted 74, verified 0;
- Wikidata candidate count 0;
- site sources: 4 registry + 2 deterministic-domain + 94 none.

Observed spare capacity cannot justify adding an unconditional production request family. Any new recall path must reallocate or re-prove the worst-case theorem.

### Q7 — consumed/dev transfer measurement

Status: **NEXT**.

Before another fresh cohort, compare current production and all sprint candidates on already-consumed/dev material:

- verified website companies;
- social companies;
- hiring companies;
- concrete job companies;
- dated activity companies;
- evidence-complete external claims;
- known wrong-company publications;
- logical/conservative requests;
- runtime and third-party cost;
- synthesis/UX regressions.

Given Q3-Q6 results, Q7 must also identify whether any currently proven low-yield request allocation can be replaced by a materially stronger recall mechanism without raising the worst-case 2,000-request ceiling.

Proceed only if the bundle is materially stronger.

### Q8 — fresh Phase-11 attempt #2

Status: **BLOCKED** until Q7 demonstrates material consumed/dev transfer.

When eligible:

- build all-touched exclusion set including seed `20261104` cohort;
- freeze exclusion count/SHA, seed and cohort SHA before results;
- use actual evaluator path;
- require 100/100 terminal and all machine integrity gates;
- manually audit every new external-family publication and all support awards;
- inspect evidence reopenability;
- freeze output/report/product/artifact hashes;
- decide GO / NO-GO.

### Q9 — Builderr revision

Submit only a materially stronger qualified bundle. Internal target remains:

- recall trajectory: 18-20+;
- evidence: 28+;
- synthesis: 12;
- UX: 8;
- 0 known material wrong-company publications.

## Current action

Q0-Q2 are production-complete. Q3 is retained but held. Q4-Q6 are measurement-closed without collector changes. The active task is **Q7: identify and measure a genuinely different recall improvement, including structural request reallocation, before any fresh qualification cohort is spent**.
