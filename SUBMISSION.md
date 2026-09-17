# Signalpost submission guide

This is the evaluator-facing entry point for the final Signalpost repository. The production collector is frozen; this submission layer documents how to reproduce it, verify the certified release artifacts, and inspect the evidence-bounded UX without enabling experimental connectors.

## 1. Identity to record with the submission

The exact repository checkout is the Git commit SHA supplied to Builderr with the submission. A Git commit cannot safely embed its own final SHA, so the repository records immutable content/application identities instead and exposes the checkout SHA at verification time.

Run:

```bash
uv run python scripts/verify_submission_bundle.py
```

The verifier prints the current checkout SHA plus the frozen release identities below.

- Production application behavior SHA: `b14ef3c277d8f1512064f865d4028e23dcd8bacf`
- Certified release harness SHA: `550bba0cce64a0a26d878c3b7f41eb20a55dc10e`
- F4 evidence-workspace merge SHA: `13e0503be4208a36e7ff34a90bf89b87caf68e3d`
- Frozen 1,000-company manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`
- Certified aggregate output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`
- Certified aggregate artifact digest: `sha256:8cdaad00c48f1d0af811fb947c97f258fdeb26d8336767f8c8e2db7d7f15e37e`
- Certified GitHub Actions replay: `35246833190`

The machine-readable copy is `submission/manifest.json`; its sidecar is `submission/manifest.sha256`. The small certified aggregate summary is committed at `submission/final-release-1000-summary.json`. The exact manifest and completed 1,000-profile output are preserved as immutable GitHub Actions artifacts on certified replay `35246833190`, with names/IDs/digests pinned below.

## 2. Reproducible setup

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
```

The OCR fallback is optional for terminal completion. If `pdftoppm` or Tesseract is unavailable, annual-report workforce extraction abstains rather than fabricating a value.

Download the current BRREG bulk snapshot once for the run:

```bash
curl --fail --location --retry 3 --retry-delay 2 \
  'https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv' \
  --output brreg-enheter.csv
```

## 3. Evaluator command

Given an evaluator JSONL batch with 100 organisation numbers:

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

The command emits exactly one final output-contract object per input organisation and a machine-readable run report. Available claim states are defined in `OUTPUT_CONTRACT.md`.

The 100-company runner proves a structural conservative request ceiling of 2,000. The certified 1,000 replay used 13,628 conservative requests across ten 100-company chunks, or 1,362.8 per 100 on average. The project policy is $0 third-party API spend and zero search-API requests.

## 4. Certified release evidence

The immutable release corpus was selected from Builderr's 411,160-company universe after excluding 5,900 previously touched companies. The final 1,000 had zero overlap with those prior cohorts.

| Property | Certified value |
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

Full audit: `docs/FINAL_RELEASE_1000_AUDIT.md`.

This release evidence demonstrates terminal completeness, output-contract validity, bounded runtime/request use, $0 third-party API spend, exact-source workforce evidence, evidence-backed external observations and explicit abstention behavior. It does **not** claim that Builderr's hidden weighted external recall, coverage score or overall score has been proven; Builderr owns those denominators and labels.

## 5. Models, APIs, licences and source-rights assumptions

Production does not invoke an LLM, a paid API, a search API, a sentiment model or a social-platform scraping connector.

Production sources are:

1. Brønnøysundregistrene official bulk/API/account-copy services for identity, official company facts, financials, roles, locations, group structure and workforce evidence.
2. Wikidata structured data only as a bounded exact-organisation-number website-candidate nominator; the candidate is never sufficient for publication by itself.
3. Verified company-owned public web pages for exact-company website proof and bounded first-party contact/social-link evidence.

The detailed source/licence/acquisition/caching/hosting register is `docs/SUBMISSION_SOURCE_RIGHTS.md`. The machine-readable declaration is also embedded in `submission/manifest.json`.

## 6. Evidence-bounded UX

Build the submission-facing static workspace directly from final output-contract JSONL:

```bash
uv run python scripts/build_submission_prototype.py \
  --input out/final-output.jsonl \
  --output out/signalpost-workspace.html
```

Open `out/signalpost-workspace.html` in a browser. The workspace shows official identity, period-aware financials, workforce evidence and effective year, verified website/contact/social declarations, leadership, locations, explicit unknowns, change history, evidence URLs, retrieval timestamps, hashes and operations metadata.

The UI deliberately does not infer reviews, sentiment, hiring activity, follower counts, engagement, platform verification or missing values. A company-declared social URL means only that the exact verified company page declared that URL.

## 7. Refresh proof

The deterministic saved-response refresh replay is:

```bash
uv run python scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json
```

The fixture is expected to find exactly two material changes, no false changes, and zero additional changes when replayed idempotently.

## 8. Submission verification

Repository-only verification:

```bash
uv run python scripts/verify_submission_bundle.py
uv run --with pytest pytest -q
```

Repository-only verification checks the submission declaration, sidecar hash, required files and certified summary. To retrieve and verify the exact frozen manifest and completed 1,000-profile output, download the certified Actions artifacts and pass them to the verifier:

```bash
gh run download 35246833190 --repo navadeep-17/signal-post \
  --name final-release-manifest-1000 --dir out/certified-manifest
gh run download 35246833190 --repo navadeep-17/signal-post \
  --name final-release-1000-aggregate --dir out/certified-aggregate

uv run python scripts/verify_submission_bundle.py \
  --release-manifest out/certified-manifest/final-release-1000.jsonl \
  --aggregate-output out/certified-aggregate/final-release-1000-output.jsonl
```

The verifier checks the machine-readable submission declaration, its sidecar hash, required repository files, optional release artifact hashes/counts/terminal states and final-output contract references.

## 9. Known limitations

- Builderr's external availability denominator and official score remain hidden; no local proxy is presented as the official result.
- Website/contact/social coverage is intentionally conservative because exact-company identity is required before publication.
- Annual-report workforce extraction abstains when a company-scope employee/FTE phrase is absent or conflicting.
- Social profile pages are not fetched, so activity, followers, ownership continuity and platform verification are not claimed.
- Published contact emails are evidence-backed same-domain addresses; mailbox deliverability is not claimed.
- Experimental review, NAV-job, sentiment, paid-search and platform-scraping paths are not part of the production runner.

## 10. What to send Builderr

Use `submission/EMAIL_TEMPLATE.md` after replacing `<FINAL_MAIN_SHA>` with the output of:

```bash
git rev-parse HEAD
```

The email should include the repository URL, exact commit SHA, evaluator command, model/API declaration and expected third-party API cost per 100-company run.
