# Signalpost final submission guide

This is the evaluator-facing source of truth for the final repository. The production collector is frozen; this package documents how to run it, verifies the exact certified 1,000-company submission corpus, and describes the source/secret boundaries without enabling experimental connectors.

## 1. Exact submission identity

When submitting, send Builderr the exact final `main` commit SHA from:

```bash
git rev-parse HEAD
```

Immutable implementation/release identities:

- production application behavior SHA: `b14ef3c277d8f1512064f865d4028e23dcd8bacf`
- certified release harness SHA: `550bba0cce64a0a26d878c3b7f41eb20a55dc10e`
- F4 evidence-workspace merge SHA: `13e0503be4208a36e7ff34a90bf89b87caf68e3d`
- certified replay: `35246833190`
- frozen 1,000 manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`
- certified uncompressed output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`
- certified Actions aggregate artifact digest: `sha256:8cdaad00c48f1d0af811fb947c97f258fdeb26d8336767f8c8e2db7d7f15e37e`

Machine-readable declaration: `submission/manifest.json`.

## 2. The exact 1,000 submitted profiles are in the repository

The submission no longer depends on temporary Actions retention for the required corpus:

- organisation-number manifest: `submission/final-release-1000.jsonl`
- completed profiles: `submission/final-release-1000-output.jsonl.gz`
- manifest digest sidecar: `submission/final-release-1000.sha256`
- uncompressed output digest sidecar: `submission/final-release-1000-output.sha256`
- compressed-file digest sidecar: `submission/final-release-1000-output.jsonl.gz.sha256`
- certified aggregate summary: `submission/final-release-1000-summary.json`

To inspect the profiles:

```bash
mkdir -p out
gzip -dc submission/final-release-1000-output.jsonl.gz > out/final-release-1000-output.jsonl
sha256sum out/final-release-1000-output.jsonl
```

Expected uncompressed SHA-256:

`00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`

`uv run python scripts/verify_submission_bundle.py` additionally checks that all 1,000 organisation numbers are unique, appear in the same order in manifest and output, are terminal `completed`, and pass the canonical output-contract validator.

## 3. Reproducible setup

Requirements:

- Python 3.12+
- `uv`
- Poppler `pdftoppm`
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

If Poppler/Tesseract is unavailable, annual-report OCR abstains. It does not invent a workforce value.

## 4. Evaluator command

For a 100-company JSONL input:

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

The runner emits one terminal object per input plus a machine-readable run report. Availability states are defined by `OUTPUT_CONTRACT.md`.

## 5. Certified release evidence

The frozen 1,000-company corpus was selected from the 411,160-company Builderr universe after excluding 5,900 previously touched companies. Overlap with prior cohorts was zero.

| Property | Certified result |
|---|---:|
| Companies | 1,000 / 1,000 |
| Unique organisation numbers | 1,000 |
| Terminal `completed` | 1,000 / 1,000 |
| Claims | 17,098 |
| Deduplicated evidence records | 17,050 |
| Canonical contract errors | 0 |
| Runner contract errors | 0 |
| Change errors | 0 |
| Observed conservative requests | 13,628 total |
| Structural request ceiling | 20,000 total / 2,000 per 100 |
| Slowest 100-company chunk | 458.803 s |
| Third-party API cost | $0.00 |
| Search API requests | 0 |
| Workforce companies | 990 / 1,000 |
| Verified website companies | 107 / 1,000 |
| Companies with declared social handles | 48 / 1,000 |
| Companies with qualifying contact email | 53 / 1,000 |

See `docs/FINAL_RELEASE_1000_AUDIT.md` for the full audit.

These measurements establish terminal completeness, evidence-contract validity and resource safety on the certified corpus. They do **not** claim Builderr's hidden weighted external company recall, coverage score or overall score are already met.

## 6. Models, APIs, licences, secrets and URL safety

Production invokes:

- **no LLM**;
- **no sentiment model**;
- **no paid API**;
- **no search API**;
- **no social-platform scraper/API**.

Server-side secrets required: **none**. No API key is required by the production runner.

Production sources:

1. Brønnøysundregistrene official bulk/API/account-copy services.
2. Wikidata structured data as a bounded exact-org-number website-candidate nominator only.
3. Exact verified company-owned public pages for bounded first-party website/contact/social-link evidence.

Source rights and retention boundaries are documented in `docs/SUBMISSION_SOURCE_RIGHTS.md`. Website retrieval uses the repository's hardened safe-URL/redirect path; private-network/unsafe targets are rejected. Company-page candidates never become published official websites without exact-company evidence.

## 7. Claim boundaries

- A declared social URL means only that the exact verified company page declared that URL; the platform itself was not fetched. It does not establish current ownership, activity, followers, engagement or platform verification.
- A contact email means the address was found in retained first-party company-page evidence and matched the verified website registered domain. Mailbox deliverability is not claimed.
- Missing website/job/review/activity/sentiment values are not converted to zero or inferred from absence.
- Annual-report workforce extraction abstains on missing or conflicting company-scope phrases.

## 8. Evidence workspace

```bash
uv run python scripts/build_submission_prototype.py \
  --input out/final-output.jsonl \
  --output out/signalpost-workspace.html
```

The static workspace shows period-aware financials, workforce/effective-year evidence, verified website/contact/social declarations, leadership, locations, explicit unknowns, change history and source provenance. It is deterministic over published output-contract claims.

## 9. Refresh proof

```bash
uv run python scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json
```

Expected result: two material changes, no false changes and no extra changes on an idempotent rerun.

## 10. Final verification

Run from the exact checkout that will be submitted:

```bash
uv run python scripts/verify_submission_bundle.py
uv run --with pytest pytest -q
```

Optional cross-check against the original certified Actions ZIP:

```bash
uv run python scripts/verify_submission_bundle.py \
  --aggregate-zip /path/to/final-release-1000-aggregate.zip
```

## 11. Known scoring risk

The largest unresolved issue is **hidden-evaluator coverage**, not a known correctness failure. Website/contact/social/public-activity breadth is intentionally conservative, and Builderr owns the checked external union and field weights. Do not weaken exact-company identity gates merely to increase local coverage.

The current challenge permits later revised commit hashes. The safest strategy is to submit this clean version, use Builderr's concrete admission/daily report to identify the actually missing weighted field family, and only then spend a revision on a measured connector improvement.

## 12. Submission email

Use `submission/EMAIL_TEMPLATE.md`. Before sending, replace:

- `<FINAL_MAIN_SHA>` with `git rev-parse HEAD`;
- `<CONTACT_NAME>` with the submitter/contact name;
- `<CONTACT_EMAIL>` with the contact email;
- `<CONTACT_PHONE_OR_OTHER>` if desired.
