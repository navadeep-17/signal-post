# Signalpost — evidence-backed Norwegian company intelligence

This repository is the final Signalpost submission implementation for exact-entity Norwegian company research. The production path resolves a Norwegian organisation number, gathers official and carefully qualified public evidence, emits one auditable output object per company, and refreshes material changes without silently filling missing values.

Start with **`SUBMISSION.md`** for the evaluator command, certified release identities, setup, source-rights declaration and known limitations.

## Final production principles

- Organisation number is the identity anchor.
- Official Brønnøysund sources are preferred for company facts and financials.
- Website/domain discovery only nominates candidates; publication requires exact-company page evidence.
- Company-owned pages may support bounded first-party contact/social-link claims.
- Social platforms themselves are not fetched by the production runner.
- Missing, blocked, ambiguous and failed states remain explicit.
- Financials and workforce values are never imputed.
- Third-party API spend policy is **$0 per 100-company run**.
- The production runner invokes **no LLM, paid search API, sentiment model or social-platform scraper**.

## Evaluator setup

Requires Python 3.12+, `uv`, Poppler and Tesseract OCR.

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
uv sync --locked

curl --fail --location --retry 3 --retry-delay 2 \
  'https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv' \
  --output brreg-enheter.csv
```

If the OCR executables are unavailable, OCR-dependent annual-report workforce extraction abstains; the terminal company record still completes.

## One production command

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

The final JSONL follows `OUTPUT_CONTRACT.md`: each input receives one terminal object containing `claims[]`, `evidence[]`, `changes[]`, `errors[]` and operation metrics.

## Certified 1,000-company release

The final release used a deterministic 1,000-company corpus with zero overlap against 5,900 previously touched companies.

- Frozen manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`
- Aggregate output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`
- Aggregate artifact digest: `sha256:8cdaad00c48f1d0af811fb947c97f258fdeb26d8336767f8c8e2db7d7f15e37e`
- 1,000 / 1,000 terminal `completed`
- 17,098 claims
- 17,050 deduplicated evidence records
- 0 canonical contract-validation errors
- 13,628 observed conservative requests across ten 100-company chunks
- 1,362.8 observed conservative requests per 100 on average
- 2,000 structural request ceiling per 100
- slowest 100-company chunk: 458.803 seconds
- $0 third-party API spend
- 0 search-API requests
- 990 / 1,000 companies with workforce evidence

The exact frozen manifest and completed certified output are preserved as immutable artifacts from GitHub Actions replay `35246833190`; their names, IDs and hashes are pinned in `SUBMISSION.md` and `submission/manifest.json`. The aggregate summary is also committed at `submission/final-release-1000-summary.json`. See `docs/FINAL_RELEASE_1000_AUDIT.md` for the complete audit. These results do not claim Builderr's hidden weighted external recall, coverage score or overall score; the hidden denominator and labels remain evaluator-owned.

## Submission-facing evidence workspace

Generate the static evidence UI from any final output-contract JSONL:

```bash
uv run python scripts/build_submission_prototype.py \
  --input out/final-output.jsonl \
  --output out/signalpost-workspace.html
```

The workspace exposes financial periods, workforce/effective-year evidence, verified website/contact/social declarations, leadership, locations, explicit unknowns, change history, source URLs, retrieval times, hashes and request/runtime/cost metadata. It deliberately does not infer sentiment, hiring activity, review scores, follower counts, engagement or missing values.

## Verify the submission bundle

```bash
uv run python scripts/verify_submission_bundle.py
uv run --with pytest pytest -q
```

To verify downloaded certified release artifacts:

```bash
gh run download 35246833190 --repo navadeep-17/signal-post \
  --name final-release-manifest-1000 --dir out/certified-manifest
gh run download 35246833190 --repo navadeep-17/signal-post \
  --name final-release-1000-aggregate --dir out/certified-aggregate

uv run python scripts/verify_submission_bundle.py \
  --release-manifest out/certified-manifest/final-release-1000.jsonl \
  --aggregate-output out/certified-aggregate/final-release-1000-output.jsonl
```

## Refresh proof

```bash
uv run python scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json
```

The saved replay is expected to detect exactly two material changes, no false changes, and no additional changes on an idempotent rerun.

## Final documentation map

- `SUBMISSION.md` — evaluator guide and final bundle identity
- `submission/manifest.json` — machine-readable submission declaration
- `submission/EMAIL_TEMPLATE.md` — ready-to-fill Builderr submission email
- `docs/SUBMISSION_SOURCE_RIGHTS.md` — source/licence/acquisition/cache/hosting declaration
- `docs/FINAL_RELEASE_1000_AUDIT.md` — certified release-scale evidence
- `docs/REQUIREMENTS_MATRIX.md` — final requirement/status mapping
- `docs/FINAL_SOURCE_LANDSCAPE_AUDIT.md` — source-landscape stop rule and rejected/deferred experiments
- `OUTPUT_CONTRACT.md` — final output schema

Historical research documents remain in the repository for auditability. They may discuss experiments that were later rejected or disabled. The authoritative final production path is defined by `SUBMISSION.md`, `submission/manifest.json`, `docs/SUBMISSION_SOURCE_RIGHTS.md` and `scripts/run_signalpost_final.py`.
