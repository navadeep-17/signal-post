# GitHub Actions workflow index

Signalpost keeps a small always-relevant CI path plus several retained qualification/replay workflows. Historical qualification workflows remain in Git so cited run IDs and release evidence stay auditable; they are **not alternative production entry points**.

## Baseline / ongoing repository checks

- `ci.yml` — primary Baseline CI. Runs the full regression suite, certified 1,000-company canonical audit, frozen submission-bundle verifier, deterministic refresh replay and refresh-output verification.
- `refresh-contract.yml` — refresh-contract focused regression/qualification checks for refresh-specific paths.
- `registry-snapshot-drift-smoke.yml` — checks current BRREG snapshot compatibility/drift behavior without redefining the submitted evaluator path.

## Retained release / qualification workflows

These workflows document or replay specific historical qualification milestones. They are kept for auditability and should not be interpreted as separate evaluator commands:

- `final-evaluator-100.yml` — historical bounded evaluator smoke path.
- `final-release-1000-v2.yml` — certified 1,000-company release/audit workflow.
- `v3-annual-description-qualification.yml` — V3 annual-report description qualification.
- `v4-registry-narrative-audit.yml` — V4 registry-narrative audit.
- `v4-registry-narrative-fresh.yml` — fresh-cohort V4 qualification.
- `v5-brreg-change-production-qualification.yml` — V5 BRREG registry-change production qualification.
- `v6e-zero-network-social-transfer.yml` — zero-network social transfer qualification.
- `v7-release-qualification.yml` — one-command V7 release-path qualification that underlies the V8 wrapper.
- `zero-overlap-validation.yml` — historical fresh-cohort/overlap validation support.

## Production evaluator path

The production/evaluator entry point is documented in:

- `../../SUBMISSION.md`
- `../../submission/V8_EVALUATOR_PATH.md`

Do not infer the current evaluator from workflow filenames alone. V8 is a thin batch-adaptive wrapper over the already-qualified V7/V5 path.

## Workflow policy

1. `ci.yml` is the required baseline gate for repository changes.
2. Product/collector changes require the relevant dedicated qualification workflow in addition to Baseline CI.
3. Documentation-only changes still run Baseline CI because submission wording and frozen compatibility boundaries are regression-tested.
4. Experiment workflows live on experiment branches until a milestone is promoted; low-yield experiments are closed rather than merged into `main`.
5. Historical run IDs cited in qualification documents remain part of the audit trail even when the corresponding feature is no longer active development.
