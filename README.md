# Signalpost — evidence-backed Norwegian company intelligence

This repository is the final Signalpost submission implementation. Given a Norwegian organisation number, the production runner resolves the exact legal entity, gathers official and carefully qualified public evidence, and emits one terminal, auditable output object per company.

**Evaluator entry point:** read `SUBMISSION.md` first.

## Production guarantees

- Organisation number is the identity anchor.
- Missing, blocked, ambiguous, not-applicable and failed states remain explicit; missing values are never silently zeroed.
- Official Brønnøysund sources are preferred for registry facts, financials, roles, locations, group structure and workforce evidence.
- Website/domain discovery nominates candidates; publication requires exact-company page evidence.
- Social platforms are not fetched by production. A social-handle claim only means an exact verified company page declared that URL.
- The production runner invokes no LLM, paid API, search API, sentiment model or social-platform scraper.
- Third-party API spend policy is **$0 per 100-company run**.
- Production requires **no server-side secrets or API keys**.

## Setup

Requires Python 3.12+, `uv`, Poppler and Tesseract OCR.

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
uv sync --locked

curl --fail --location --retry 3 --retry-delay 2 \
  'https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv' \
  --output brreg-enheter.csv
```

If the OCR executables are unavailable, OCR-dependent annual-report workforce extraction abstains instead of fabricating a value; the terminal company result can still complete.

## One evaluator command

For a 100-company evaluator JSONL batch:

```bash
uv run python scripts/run_signalpost_final.py \
  --organisations evaluator-100.jsonl \
  --bulk brreg-enheter.csv \
  --output out/final-output.jsonl \
  --report out/final-report.json \
  --work-dir out/final-work \
  --run-id builderr-eval-001 \
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

The output follows `OUTPUT_CONTRACT.md`: `claims[]`, `evidence[]`, `changes[]`, `errors[]` and operations metadata.

## Certified 1,000-company submission corpus

The **exact submitted manifest and completed certified profiles are committed in this repository**:

- `submission/final-release-1000.jsonl`
- `submission/final-release-1000-output.jsonl.gz`

The output is gzip-compressed only to keep the repository compact. Decompress it without changing its certified bytes:

```bash
mkdir -p out
gzip -dc submission/final-release-1000-output.jsonl.gz > out/final-release-1000-output.jsonl
```

Certified identities:

- frozen manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`
- uncompressed aggregate output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`
- certified replay: `35246833190`
- 1,000 / 1,000 terminal `completed`
- 17,098 claims / 17,050 deduplicated evidence records
- 0 canonical contract errors
- 13,628 observed conservative requests across ten 100-company chunks
- slowest chunk: 458.803 seconds
- $0 third-party API spend / 0 search-API requests

The full audit is `docs/FINAL_RELEASE_1000_AUDIT.md`. These diagnostics do **not** claim Builderr's hidden coverage, weighted external recall or total score are already satisfied.

## Verify before submission

```bash
uv run python scripts/verify_submission_bundle.py
uv run --with pytest pytest -q
```

The submission verifier validates the machine manifest, the committed 1,000-company manifest, the compressed certified output, the exact uncompressed output digest, organisation-number order, terminal states, output-contract references and certified summary.

## Evidence workspace

```bash
uv run python scripts/build_submission_prototype.py \
  --input out/final-output.jsonl \
  --output out/signalpost-workspace.html
```

The static workspace exposes period-aware financials, workforce/effective-year evidence, verified website/contact/social declarations, leadership, locations, unknowns, changes, source URLs, timestamps, hashes and request/runtime/cost metadata. It does not infer reviews, sentiment, hiring activity, followers, engagement or missing values.

## Refresh proof

```bash
uv run python scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json
```

The saved replay is expected to detect exactly two material changes, no false changes, and no additional changes on an idempotent rerun.

## Final documentation

- `SUBMISSION.md` — evaluator guide and exact submission checklist
- `submission/manifest.json` — machine-readable final declaration
- `submission/EMAIL_TEMPLATE.md` — submission email template with contact placeholders
- `docs/SUBMISSION_SOURCE_RIGHTS.md` — source/licence/acquisition/retention policy
- `docs/FINAL_RELEASE_1000_AUDIT.md` — certified release-scale evidence
- `docs/REQUIREMENTS_MATRIX.md` — final requirement mapping
- `docs/SCORING_READINESS_AUDIT.md` — final pre-submission risk assessment
- `OUTPUT_CONTRACT.md` — output schema

Historical experiment scripts and documents are retained for auditability. They are not enabled by `scripts/run_signalpost_final.py` unless the final submission documents explicitly say otherwise.
