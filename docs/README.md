# Signalpost documentation

This directory contains the engineering evidence and design history behind Signalpost. The repository intentionally keeps **current evaluator guidance**, **qualified production evidence**, and **historical experiments** separate so reviewers can find the active path quickly without losing auditability.

## Start here

1. [`../README.md`](../README.md) — concise project overview, architecture and quick start.
2. [`../SUBMISSION.md`](../SUBMISSION.md) — evaluator-facing guide for the submitted V8 release.
3. [`../submission/V8_EVALUATOR_PATH.md`](../submission/V8_EVALUATOR_PATH.md) — current batch-adaptive evaluator wrapper.
4. [`../OUTPUT_CONTRACT.md`](../OUTPUT_CONTRACT.md) — source envelope, canonical projection and evidence contract.
5. [`REQUIREMENTS_MATRIX.md`](REQUIREMENTS_MATRIX.md) — challenge requirements mapped to implementation/evidence.
6. [`SUBMISSION_SOURCE_RIGHTS.md`](SUBMISSION_SOURCE_RIGHTS.md) — source, licence, acquisition and retention boundaries.
7. [`FINAL_RELEASE_1000_AUDIT.md`](FINAL_RELEASE_1000_AUDIT.md) — certified large-batch historical baseline.

The Builderr-submitted V8 evaluator revision remains pinned separately from later documentation-only cleanup commits. See `../SUBMISSION.md` for the exact release SHA and release ref.

## Current production lineage

Signalpost evolved incrementally. The current V8 path delegates to previously qualified evidence/product layers rather than replacing them:

- V1 — frozen certified source/output baseline;
- V2 — canonical/product compatibility layer;
- V3/V4 — conservative company-description improvements;
- V5 — exact-org BRREG registry-change production layer;
- V6 — evidence workspace and zero-network recovery work;
- V7 — decision brief, careers semantics and evaluator-facing product qualification;
- V8 — dynamic evaluator-batch wrapper over the qualified V7/V5 path.

Relevant production/qualification records include:

- [`V3_IMPLEMENTATION_PLAN.md`](V3_IMPLEMENTATION_PLAN.md)
- [`V4_OFFICIAL_SOURCE_SCREEN.md`](V4_OFFICIAL_SOURCE_SCREEN.md)
- [`V5_BRREG_CHANGE_SCREEN.md`](V5_BRREG_CHANGE_SCREEN.md)
- [`V5_BRREG_CHANGE_PRODUCTION.md`](V5_BRREG_CHANGE_PRODUCTION.md)
- [`FINAL_RELEASE_AUDIT.md`](FINAL_RELEASE_AUDIT.md)
- [`FINAL_RELEASE_1000_AUDIT.md`](FINAL_RELEASE_1000_AUDIT.md)

## Historical experiments and audit trail

Documents prefixed `H1*`, `H2*`, older V6/V7 source screens, and source-landscape/design notes record experiments that informed current precision, provenance and source-selection rules. They are retained for reproducibility and **are not separate production entry points**.

Examples:

- [`H1_DOMAIN_DISCOVERY.md`](H1_DOMAIN_DISCOVERY.md)
- [`H1C_SECONDARY_IDENTITY.md`](H1C_SECONDARY_IDENTITY.md)
- [`H2A_SOCIAL_QUALIFICATION.md`](H2A_SOCIAL_QUALIFICATION.md)
- [`H2C_CONTACT_EMAIL_QUALIFICATION.md`](H2C_CONTACT_EMAIL_QUALIFICATION.md)
- [`H2G_ANNUAL_REPORT_WORKFORCE.md`](H2G_ANNUAL_REPORT_WORKFORCE.md)
- [`FINAL_SOURCE_LANDSCAPE_AUDIT.md`](FINAL_SOURCE_LANDSCAPE_AUDIT.md)

Low-yield or failed experiments are deliberately preserved when they explain why a source/strategy was not promoted.

## Current V9 R&D boundary

Post-V8 score-expansion work is isolated from the submitted evaluator until it passes explicit GO/NO-GO gates.

The active high-impact experiment is Website Discovery 2.0. Model/search-assisted nomination is not part of V8 production and remains blocked on evaluator-reproducible provider/key/budget confirmation plus fresh-cohort precision/coverage qualification.

Supporting V9 experiments for structured first-party discovery, ATS jobs, dated updates and zero-network contact recovery have been measured separately and are not productionized merely because code exists.

## Workflows

See [`../.github/workflows/README.md`](../.github/workflows/README.md) for the workflow inventory and the distinction between baseline CI and retained qualification/replay workflows.

## Source-of-truth order

When older documents differ because the project evolved, use this order:

1. the current Builderr challenge/evaluator contract for official rules;
2. `../SUBMISSION.md` for this repository's submitted evaluator instructions;
3. `../submission/V8_EVALUATOR_PATH.md` for V8 wrapper behavior;
4. `../OUTPUT_CONTRACT.md` and `../submission/manifest.json` for contract/lineage details;
5. `REQUIREMENTS_MATRIX.md` and current qualification documents;
6. certified historical release audits;
7. historical experiment/design notes.

Builderr remains authoritative for the checked company collection, infrastructure limits and official score.
