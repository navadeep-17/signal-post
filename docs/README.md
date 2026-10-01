# Signalpost documentation

This directory contains the engineering evidence behind the current Signalpost submission. The documents are intentionally split between **current evaluator-facing material**, **qualification evidence**, and **historical experiments** so the production path remains easy to review without losing auditability.

## Start here

- `../SUBMISSION.md` — current evaluator guide, run command, production boundaries and qualification evidence.
- `../submission/manifest.json` — machine-readable current V5 submission declaration and pinned production lineage.
- `../submission/v5-smoke-100-run-report.json` — concise current 100-company smoke-test result required for evaluator handoff.
- `REQUIREMENTS_MATRIX.md` — current challenge requirements mapped to implementation and evidence.
- `SUBMISSION_SOURCE_RIGHTS.md` — source, licence, acquisition and retention boundaries.
- `V5_BRREG_CHANGE_PRODUCTION.md` — current BRREG registry-change production qualification.
- `FINAL_RELEASE_1000_AUDIT.md` — certified 1,000-company historical evidence baseline.

## Current production lineage

- `V3_IMPLEMENTATION_PLAN.md` — score-driven V3 implementation plan.
- `V4_OFFICIAL_SOURCE_SCREEN.md` — measured source-screen results and rejected connectors.
- `V4_KEYED_SOURCE_ACCESS.md` — keyed-source access findings.
- `V5_BRREG_CHANGE_SCREEN.md` — BRREG change-feed source screen.
- `V5_BRREG_CHANGE_PRODUCTION.md` — promoted V5 implementation and fresh qualification.

## Historical audit material

Documents prefixed `H1*` and `H2*`, together with the earlier baseline/source-landscape/design notes, record experiments that informed the current precision and source-selection rules. They are retained for reproducibility and audit history; they are **not separate production entry points**.

Key historical records include:

- `BASELINE_100.md`
- `H1_DOMAIN_DISCOVERY.md`
- `H1C_SECONDARY_IDENTITY.md`
- `H2A_SOCIAL_QUALIFICATION.md`
- `H2C_CONTACT_EMAIL_QUALIFICATION.md`
- `H2G_ANNUAL_REPORT_WORKFORCE.md`
- `ZERO_OVERLAP_VALIDATION.md`
- `FINAL_SOURCE_LANDSCAPE_AUDIT.md`

## Workflow cleanup policy

The active `.github/workflows/` directory is intentionally limited to current CI, evaluator/release validation, refresh/snapshot regressions and the qualified V3–V5 production checks. Early H1/H2 experiment and source-screen workflow definitions were retired from the default branch after their conclusions were captured in these documents and immutable Git history.

Past GitHub Actions run IDs cited in qualification documents remain part of the repository's audit trail even when the original experimental workflow file is no longer active on `main`.

## Source-of-truth order

When documents differ because the project evolved, use this order:

1. the current Builderr challenge page for official rules and scoring;
2. `../SUBMISSION.md` for this repository's evaluator instructions;
3. `../submission/manifest.json` and `../submission/v5-smoke-100-run-report.json` for machine-readable revision/run evidence;
4. `REQUIREMENTS_MATRIX.md`;
5. current V5 qualification documents;
6. certified historical release audits;
7. historical experiment/design notes.

Builderr's checked collection and evaluator remain authoritative for the official score.
