# Signalpost

Evidence-backed Norwegian company intelligence for the Builderr Signalpost challenge.

Signalpost resolves Norwegian companies by organisation number, gathers official and conservatively qualified public evidence, and emits one terminal, auditable result per company. The system is designed around **exact-entity attribution, explicit provenance, bounded cost, deterministic canonical facts, and abstention when evidence is insufficient**.

> **Evaluator entry point:** `scripts/run_signalpost_v2.py`  
> The filename is retained for backward compatibility; the current production path includes the qualified V3–V5 data layers plus the current evidence-linked explorer/compare product documented in `SUBMISSION.md`.

## Current production revision

The current system combines:

- exact-company BRREG registry, accounting, roles, locations and group evidence;
- deterministic website discovery with strict identity verification;
- first-party contact email and company-declared social-profile facts;
- registry and annual-report workforce evidence;
- conservative annual-report company descriptions;
- exact-org BRREG registered activity as a description fallback;
- bounded exact-org BRREG registry-change history;
- evidence-linked canonical facts and deterministic synthesis;
- a static data-linked HTML workspace generated from the same final JSONL;
- an evidence-linked side-by-side company comparison view covering company snapshot, financials, workforce, leadership, locations, website/public signals and recent official changes.

The comparison surface is descriptive only. Signalpost does not rank companies, choose a winner or infer missing values.

Production invokes **no LLM API, paid API, search API, sentiment model, or social-platform scraper**. Server-side secrets are not required and the third-party API spend policy is **$0.00 per 100-company run**.

## Design principles

1. **Organisation number is the identity anchor.** Candidate discovery never proves identity.
2. **Evidence before publication.** Published facts retain source URLs, evidence IDs, retrieval metadata and hashes where applicable.
3. **Abstain instead of guessing.** Missing, blocked, ambiguous, not-applicable and failed states remain explicit.
4. **AI/ML cannot override evidence gates.** The current production evaluator path is deterministic.
5. **Bounded execution.** A 100-company evaluator run is constrained to the challenge request/runtime envelope.
6. **Exact semantics.** Registry changes are labelled as registry changes; they are not presented as company-authored news, hiring or social activity.
7. **Comparison is non-ranking.** The UX places source-backed facts side by side without creating a best/worst verdict.

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
        │      └── declared social profiles
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
deterministic synthesis
        │
        ├── JSONL output
        └── current HTML product
               ├── company explorer
               ├── evidence verification
               └── side-by-side compare
```

The original `claims[]` / `evidence[]` envelope remains the source of truth. Canonical facts reference the underlying source fields and evidence IDs rather than replacing provenance.

## Quick start

Requirements:

- Python 3.12+
- `uv`
- Poppler (`pdftoppm`)
- Tesseract OCR

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

For a 100-company JSONL input:

```bash
uv run python scripts/run_signalpost_v2.py \
  --organisations evaluator-100.jsonl \
  --bulk brreg-enheter.csv \
  --output out/final-output.jsonl \
  --report out/final-report.json \
  --product-output out/signalpost.html \
  --work-dir out/final-work \
  --run-id builderr-eval-v5-001 \
  --expected-count 100 \
  --workers 8 \
  --site-timeout 6 \
  --wikidata-timeout 8 \
  --max-challenge-requests 2000 \
  --max-third-party-cost-usd 0 \
  --max-wall-runtime-seconds 2400 \
  --annual-workforce-workers 4 \
  --annual-workforce-timeout 60 \
  --annual-workforce-min-start-interval 2.1 \
  --annual-workforce-ocr-pages 8 \
  --annual-workforce-ocr-dpi 110
```

See `SUBMISSION.md` for the evaluator-facing source of truth and current qualification evidence.

## Current qualified improvements

### Company descriptions

V3 reuses exact-org BRREG annual-account copies for conservative company-scope descriptions. V4 then adds literal exact-org BRREG `aktivitet` as a zero-network fallback when no stronger description exists.

On the certified 1,000-company audit, description coverage increased from **85/1,000 to 998/1,000** while preserving all 85 stronger descriptions and adding zero network requests.

### Official registry changes

V5 adds the official Enhetsregister update feed with strict exact-org attribution, a 365-day lookback, a conservative path allowlist and at most three recent qualified events per company.

A fresh zero-overlap 100-company qualification produced:

- 100/100 terminal company results;
- 100/100 companies with qualified registry-change facts;
- 156 published registry-change claims;
- one BRREG change-feed request;
- 1,382 / 2,000 observed conservative request charge;
- zero integrity/evidence/output-contract/canonical/synthesis errors;
- $0.00 third-party API cost.

These are repository engineering results, not a claimed Builderr score.

## Output

Each company output preserves the source contract:

- `organisation_number`
- `run`
- `claims[]`
- `evidence[]`
- `changes[]`
- `errors[]`
- `operations`

The evaluator wrapper additionally emits:

- `canonical_facts[]`
- `canonical_profile`
- `synthesis`

Canonical namespaces include `company.*`, `financial.*`, `people.*`, `locations.*`, `website.*`, `public.*` and `hiring.*`.

## Product surface

Passing `--product-output` now generates the current Signalpost workspace directly from the final JSONL through `scripts/build_current_product.py`.

The **Explore** view exposes company record, financials, people and locations, website facts, public/hiring signals, changes, unknowns and source evidence. The **Compare companies** view places two records side by side across company description/industry/location/legal form, financials, workforce, leadership, registered locations, official website/contact/social facts, strict job/update facts and recent official BRREG changes. Every published comparison value keeps source links next to the cell, and unavailable values remain “Not published” rather than being inferred.

The comparison is descriptive only and deliberately does not rank companies or choose a winner.

The historical checked-in `submission/signalpost-v2.html` remains unchanged as the certified V2 artifact. Current evaluator runs generate the newer product at the `--product-output` path without mutating that historical artifact.

## Verification

```bash
uv run --with pytest pytest -q
uv run python scripts/audit_canonical_v2.py
uv run python scripts/verify_submission_bundle.py
```

Baseline CI runs the regression suite, certified canonical audit, submission-bundle verification and deterministic refresh replay.

## Repository layout

```text
src/norway_company_agent/   production collectors, validators and projections
scripts/                    evaluator, current product, audits and reproducible tooling
tests/                      deterministic regression and contract tests
submission/                 certified artifacts and submission declarations
docs/                       qualification evidence, source rights and design records
data/                       small committed metadata required for reproducibility
.github/workflows/           active CI and qualification workflows
```

Historical experiment documents are retained where they support auditability, but they are not enabled by the current evaluator path unless `SUBMISSION.md` explicitly says otherwise.

## Documentation

- `SUBMISSION.md` — current evaluator guide and qualification boundary
- `OUTPUT_CONTRACT.md` — source envelope and canonical projection contract
- `docs/REQUIREMENTS_MATRIX.md` — challenge requirement coverage
- `docs/SUBMISSION_SOURCE_RIGHTS.md` — source/licence/acquisition policy
- `docs/V5_BRREG_CHANGE_PRODUCTION.md` — current registry-change qualification
- `docs/FINAL_RELEASE_1000_AUDIT.md` — certified V1 evidence baseline
- `submission/manifest.json` — machine-readable submission declaration
- `submission/EMAIL_TEMPLATE.md` — revision submission template

## Historical certified baseline

The immutable certified V1 corpus remains committed under `submission/`:

- 1,000 / 1,000 terminal companies;
- 17,098 source claims;
- 17,050 deduplicated evidence records;
- 13,628 observed conservative requests across ten 100-company chunks;
- $0 third-party API spend and 0 search-API requests.

V1 pinned submission SHA: `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`.
