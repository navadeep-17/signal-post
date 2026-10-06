# Signalpost documentation

This directory separates current release guidance, qualification evidence and historical experiments.

## Start here

1. [`../README.md`](../README.md) — project overview and evaluator command.
2. [`../SUBMISSION.md`](../SUBMISSION.md) — current submitted-vs-qualified revision status.
3. [`Q8_RELEASE_QUALIFICATION.md`](Q8_RELEASE_QUALIFICATION.md) — final fresh 100-company machine + manual release gate.
4. [`CONTINUATION_STATE.md`](CONTINUATION_STATE.md) — exact live handoff and next action.
5. [`70_PLUS_IMPLEMENTATION_PLAN.md`](70_PLUS_IMPLEMENTATION_PLAN.md) — score-improvement roadmap and closure state.
6. [`../submission/V8_EVALUATOR_PATH.md`](../submission/V8_EVALUATOR_PATH.md) — evaluator wrapper contract.
7. [`../OUTPUT_CONTRACT.md`](../OUTPUT_CONTRACT.md) — claims/evidence/canonical output contract.
8. [`REQUIREMENTS_MATRIX.md`](REQUIREMENTS_MATRIX.md) — challenge requirements mapping.
9. [`SUBMISSION_SOURCE_RIGHTS.md`](SUBMISSION_SOURCE_RIGHTS.md) — source/licence/acquisition policy.

## Current release state

The previously submitted Builderr revision remains `e7cbbcdd505596dbd5d819b5e8647602760a7aa3` until a replacement is explicitly submitted.

The newer production line at `main@200f056a5a60cad23610a3958b6bec62dfb624a5` passed Q8 fresh release qualification attempt #4. The qualification-only PR #124 was closed without merge. Release work is now documentation-only finalization, exact-head CI, release-ref freeze and Builderr submission.

No new source experiment or fresh cohort is on the critical path before submission.

## Production lineage

The evaluator entry point remains `scripts/run_signalpost_v8.py`, which delegates through the qualified V7/V2/V1 lineage while preserving the certified immutable baseline.

Current production additionally includes the qualified post-V8 improvements recorded in the roadmap and implementation log, including exact-org support awards, precision-hardened first-party external evidence, and final evaluator-visible provenance/precision guards.

## Historical experiments

Documents and branches for H1/H2, Website Discovery 2.0, Common Crawl, NAV, OSM/Norid and other source screens remain part of the audit trail. They are not productionized merely because experimental code or results exist.

## Source-of-truth order

When older documents differ:

1. live Builderr challenge/evaluator contract;
2. `../SUBMISSION.md`;
3. `Q8_RELEASE_QUALIFICATION.md`;
4. `CONTINUATION_STATE.md`;
5. `../submission/V8_EVALUATOR_PATH.md`;
6. `../OUTPUT_CONTRACT.md` and `../submission/manifest.json`;
7. current roadmap/requirements/source-rights docs;
8. historical experiments.

Builderr remains authoritative for the official evaluator result and score.
