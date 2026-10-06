# Signalpost documentation

This directory separates current evaluator guidance, qualified production evidence and historical experiments.

## Start here

1. [`../SUBMISSION.md`](../SUBMISSION.md) — exact revision/evaluator command for the next Builderr submission.
2. [`Q8_FRESH_QUALIFICATION_2026-10-06.md`](Q8_FRESH_QUALIFICATION_2026-10-06.md) — final fresh 100-company Q8 qualification.
3. [`../submission/v8-qualified-2026-10-06.json`](../submission/v8-qualified-2026-10-06.json) — machine-readable qualification/release record.
4. [`../submission/V8_EVALUATOR_PATH.md`](../submission/V8_EVALUATOR_PATH.md) — batch-adaptive evaluator wrapper.
5. [`../OUTPUT_CONTRACT.md`](../OUTPUT_CONTRACT.md) — output/evidence contract.
6. [`REQUIREMENTS_MATRIX.md`](REQUIREMENTS_MATRIX.md) — current requirements/gates.
7. [`SUBMISSION_SOURCE_RIGHTS.md`](SUBMISSION_SOURCE_RIGHTS.md) — source/licence/acquisition boundaries.
8. [`FINAL_RELEASE_1000_AUDIT.md`](FINAL_RELEASE_1000_AUDIT.md) — historical certified large-batch baseline.

## Current release

- production SHA: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- frozen release ref: `release/v8-qualified-2026-10-06`
- evaluator: `scripts/run_signalpost_v8.py`
- Q8 fresh decision: **GO**
- official Builderr score for this revision: not yet claimed

The qualification harness is not production code and was deliberately closed without merge.

## Current production lineage

Signalpost retains its historical V1/V2/V5 compatibility layers under the current V8 evaluator path. Later production hardening adds Støtteregisteret support, evaluator-visible identity/extraction provenance, bounded first-party feed activity, wrong-owner/site guards and final external precision guards.

Historical experiments remain in `docs/` and Git history for auditability. A failed or low-yield experiment is not a production source merely because its code or document exists.

## Source-of-truth order

1. Builderr's live challenge/evaluator contract.
2. `../SUBMISSION.md`.
3. `Q8_FRESH_QUALIFICATION_2026-10-06.md`.
4. `../submission/v8-qualified-2026-10-06.json`.
5. `../submission/V8_EVALUATOR_PATH.md`.
6. `../OUTPUT_CONTRACT.md` and current requirements/source-rights docs.
7. historical certified audits and experiment notes.

Builderr remains authoritative for the official checked collection and score.
