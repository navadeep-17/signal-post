# Signalpost

[![Baseline CI](https://github.com/navadeep-17/signal-post/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/navadeep-17/signal-post/actions/workflows/ci.yml)

Evidence-backed Norwegian company intelligence for the Builderr Signalpost challenge.

Signalpost resolves companies by Norwegian organisation number, gathers official and conservatively qualified public evidence, and returns one terminal, auditable result per supplied company. The system is built around **exact-entity attribution, explicit provenance, bounded execution, deterministic canonical facts, and abstention when evidence is insufficient**.

> **Current evaluator entry point:** `scripts/run_signalpost_v8.py`
>
> V8 derives the evaluator batch size from the supplied organisation file and delegates to the already-qualified V7/V5 evidence and product pipeline. It does not weaken any identity or publication gate.

Compatibility lineage remains explicit: V8 delegates through `scripts/run_signalpost_v7.py` to the certified `scripts/run_signalpost_v2.py` data/evidence wrapper and the pinned V1 base runner. The older filenames are retained intentionally for reproducibility; they are not the recommended top-level evaluator command.

## What Signalpost provides

- exact-company resolution anchored on organisation number;
- BRREG registry, accounting, roles, group and location evidence;
- deterministic website discovery with strict legal-entity verification;
- qualified first-party contact email and company-declared social profiles;
- registry and annual-report workforce evidence;
- conservative annual-report and registry-backed company descriptions;
- bounded official BRREG registry-change history;
- canonical facts linked back to source evidence;
- deterministic evidence-linked decision briefs;
- a static evaluator workspace with company search, evidence inspection, recent changes, **Compare companies**, and grounded Ask Signalpost answers;
- conservative careers-page semantics that never equate a careers surface with an active vacancy.

Production V8 uses **no LLM API, paid search API, sentiment model or social-platform scraper** and requires **no API secrets**.

## Design principles

1. **Organisation number is the identity anchor.** Candidate discovery never proves identity.
2. **Evidence before publication.** Published facts retain source URLs, evidence IDs, retrieval metadata and hashes where applicable.
3. **Abstain instead of guessing.** Missing, blocked and ambiguous states remain explicit.
4. **Wrong-company prevention outranks recall.** Parent companies, namesakes and conflicting organisation numbers are rejected or quarantined.
5. **Bounded execution.** Request, runtime and third-party-cost accounting are explicit.
6. **Exact semantics.** Registry changes stay registry changes; a careers page stays a careers page unless a separately qualified job posting exists.
7. **Descriptive comparison only.** Signalpost presents evidence side by side without ranking companies.

## Architecture

```text
Evaluator company list
        │
        ▼
Exact BRREG entity resolution
        │
        ├── registry / accounting / roles / locations / group
        ├── verified company website
        │      ├── contact email
        │      ├── declared social profiles
        │      └── qualified careers surface
        ├── annual-report intelligence
        │      ├── workforce
        │      └── company description
        └── BRREG update history
               └── bounded official registry changes
        │
        ▼
claims[] + evidence[]
        │
        ▼
canonical_facts[] + canonical_profile
        │
        ▼
deterministic synthesis / decision brief
        │
        ├── JSONL output
        └── static evaluator workspace
               ├── company explorer
               ├── evidence drawer / verification
               ├── recent changes
               ├── Compare companies
               └── grounded Ask Signalpost
```

The original `claims[]` / `evidence[]` envelope remains the source of truth. Canonical facts reference source fields and evidence IDs rather than replacing provenance.

## Quick start

### Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- Poppler (`pdftoppm`)
- Tesseract OCR

Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
uv sync --locked

curl --fail --location --retry 3 --retry-delay 2 \
  'https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv' \
  --output brreg-enheter.csv
```

If OCR tooling is unavailable, OCR-dependent extraction abstains rather than fabricating a value.

## Evaluator command

```bash
uv run python scripts/run_signalpost_v8.py \
  --organisations evaluator-companies.jsonl \
  --bulk brreg-enheter.csv \
  --output out/final-output.jsonl \
  --report out/final-report.json \
  --product-output out/signalpost.html \
  --work-dir out/final-work \
  --run-id builderr-eval-v8-001 \
  --workers 8 \
  --site-timeout 6 \
  --wikidata-timeout 8 \
  --max-third-party-cost-usd 0 \
  --annual-workforce-workers 4 \
  --annual-workforce-timeout 60 \
  --annual-workforce-min-start-interval 2.1 \
  --annual-workforce-ocr-pages 8 \
  --annual-workforce-ocr-dpi 110
```

Do **not** hard-code `--expected-count` in the normal evaluator command. V8 reads the supplied organisation file and derives the exact batch size before delegating to the qualified evaluator pipeline.

See [`submission/V8_EVALUATOR_PATH.md`](submission/V8_EVALUATOR_PATH.md) and [`SUBMISSION.md`](SUBMISSION.md) for the evaluator-facing contract and release details.

## Release integrity

Current submitted V8 revision:

- release commit: `e7cbbcdd505596dbd5d819b5e8647602760a7aa3`;
- release ref: `release/v8-final-2026-10-03`;
- frozen V1 submission SHA: `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`.

The certified V5 machine-readable lineage in `submission/manifest.json` is intentionally preserved. V8 is an evaluator-compatibility wrapper over the already-qualified evidence/product path, not a rewrite of the certified collector lineage.

## Qualification evidence

The underlying V7 production path has been exercised end to end on a reproducible 100-company release cohort with:

- 100/100 terminal company outputs;
- zero canonical validation errors;
- zero synthesis validation errors;
- decision briefs for 100/100 companies;
- 1,364 / 2,000 observed conservative request charge;
- 311.985 seconds wall runtime;
- $0.00 third-party API cost;
- zero search-API requests;
- successful generation of the evaluator-facing workspace.

V8 additionally has regression coverage for arbitrary evaluator batch sizes and rejects explicit expected-count mismatches before research begins.

These are repository engineering results, **not a claimed Builderr score**.

## Output model

Each terminal company result preserves:

- `organisation_number`;
- `run`;
- `claims[]`;
- `evidence[]`;
- `changes[]`;
- `errors[]`;
- `operations`;
- `canonical_facts[]`;
- `canonical_profile`;
- `synthesis`.

Canonical namespaces include `company.*`, `financial.*`, `people.*`, `locations.*`, `website.*`, `public.*` and `hiring.*`.

## Verification

```bash
uv run --with pytest pytest -q
uv run python scripts/audit_canonical_v2.py
uv run python scripts/verify_submission_bundle.py
```

Baseline CI runs the full regression suite, the certified 1,000-company canonical audit, the frozen submission-bundle verifier, and deterministic refresh replay/output verification.

## Repository layout

```text
src/norway_company_agent/   collectors, identity gates, validators and projections
scripts/                    evaluator wrappers, UI builders, audits and tooling
tests/                      deterministic regression and contract tests
submission/                 certified artifacts and evaluator/release declarations
docs/                       qualification evidence, source rights and design records
data/                       small committed reproducibility inputs
.github/workflows/          CI and qualification workflows
```

Historical qualification material is retained for auditability but is not part of the production evaluator path unless the submission documentation says otherwise.

## Current R&D boundary

Post-V8 score-expansion work is intentionally isolated from production. Website Discovery 2.0 remains an experiment until its provider credential/budget contract is evaluator-reproducible and fresh-cohort precision/coverage gates pass. The submitted V8 release is therefore stable while the next recall improvements are being qualified.

## Key documentation

- [`SUBMISSION.md`](SUBMISSION.md) — current evaluator/release guide
- [`docs/README.md`](docs/README.md) — documentation map: current vs qualification vs historical
- [`OUTPUT_CONTRACT.md`](OUTPUT_CONTRACT.md) — output and evidence contract
- [`submission/V8_EVALUATOR_PATH.md`](submission/V8_EVALUATOR_PATH.md) — V8 batch-adaptive wrapper
- [`submission/V7_EVALUATOR_PATH.md`](submission/V7_EVALUATOR_PATH.md) — qualified V7 evidence/product delegation path
- [`.github/workflows/README.md`](.github/workflows/README.md) — workflow inventory and qualification policy
- [`docs/REQUIREMENTS_MATRIX.md`](docs/REQUIREMENTS_MATRIX.md) — challenge requirement coverage
- [`docs/SUBMISSION_SOURCE_RIGHTS.md`](docs/SUBMISSION_SOURCE_RIGHTS.md) — source/licence/acquisition policy
- [`submission/manifest.json`](submission/manifest.json) — certified machine-readable lineage
