# Signalpost documentation

This directory separates current release guidance, qualification evidence and historical experiments.

## Start here

1. [`../README.md`](../README.md) — project overview and evaluator command.
2. [`../SUBMISSION.md`](../SUBMISSION.md) — current submitted-vs-qualified revision status.
3. [`Q8_RELEASE_QUALIFICATION.md`](Q8_RELEASE_QUALIFICATION.md) — final fresh 100-company machine + manual release gate.
4. [`../submission/v8-qualified-2026-10-06.json`](../submission/v8-qualified-2026-10-06.json) — machine-readable Q8 release qualification record.
5. [`CONTINUATION_STATE.md`](CONTINUATION_STATE.md) — exact live handoff and next action.
6. [`70_PLUS_IMPLEMENTATION_PLAN.md`](70_PLUS_IMPLEMENTATION_PLAN.md) — score-improvement roadmap and closure state.
7. [`../submission/V8_EVALUATOR_PATH.md`](../submission/V8_EVALUATOR_PATH.md) — evaluator wrapper contract.
8. [`../OUTPUT_CONTRACT.md`](../OUTPUT_CONTRACT.md) — claims/evidence/canonical output contract.
9. [`REQUIREMENTS_MATRIX.md`](REQUIREMENTS_MATRIX.md) — challenge requirements mapping.
10. [`SUBMISSION_SOURCE_RIGHTS.md`](SUBMISSION_SOURCE_RIGHTS.md) — source/licence/acquisition policy.

## Current release state

The previously submitted Builderr revision remains `e7cbbcdd505596dbd5d819b5e8647602760a7aa3` until a replacement is explicitly submitted.

The production code at `200f056a5a60cad23610a3958b6bec62dfb624a5` passed Q8 fresh release qualification attempt #4 and is permanently anchored by `release/v8-qualified-2026-10-06`. The documentation-complete Builderr submission revision is anchored separately by `release/v8-submission-2026-10-06`; post-qualification differences are documentation/release metadata only.

No new source experiment or fresh cohort is on the critical path before submission. The newly qualified revision has not yet received an official Builderr score.

## Production lineage

The evaluator entry point remains `scripts/run_signalpost_v8.py`, which delegates through the qualified V7/V2/V1 lineage while preserving the certified immutable baseline.

Current production additionally includes the qualified post-V8 improvements recorded in the roadmap and implementation log, including exact-org support awards, precision-hardened first-party external evidence, and final evaluator-visible provenance/precision guards.

## Historical experiments

Documents and branches for H1/H2, Website Discovery 2.0, Common Crawl, NAV, OSM/Norid and other source screens remain part of the audit trail. They are not productionized merely because experimental code or results exist.

## Source-of-truth order

When older documents differ:

1. live Builderr challenge/evaluator contract and official result;
2. `../SUBMISSION.md` — current release/submission guide;
3. `Q8_RELEASE_QUALIFICATION.md` — frozen human-readable fresh qualification record;
4. `../submission/v8-qualified-2026-10-06.json` — frozen machine-readable current qualification record;
5. `CONTINUATION_STATE.md` — current handoff/next action;
6. `../submission/V8_EVALUATOR_PATH.md` and `../OUTPUT_CONTRACT.md` — current evaluator/output contract;
7. `SUBMISSION_SOURCE_RIGHTS.md` and `REQUIREMENTS_MATRIX.md` — current source/acquisition and requirements declarations;
8. `../submission/manifest.json` — historical certified V5/V2 lineage/audit manifest, not the current V8 release-state authority;
9. historical experiments.

`release/v8-submission-2026-10-06` is the exact final submission ref. Builderr remains authoritative for the official evaluator result and score.
