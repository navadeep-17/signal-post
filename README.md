# Signalpost — evidence-backed Norwegian company intelligence

Signalpost resolves Norwegian companies by organisation number, gathers official and carefully qualified public evidence, and emits one terminal, auditable output object per company.

**Evaluator entry point:** read `SUBMISSION.md` first.  
**Current revision:** V2 canonical mapping + data-linked product surface.  
**V1 pinned submission:** `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa` remains immutable.

## What changed in V2

Builderr diagnostic feedback indicated that the first submission returned complete company objects but too little of the already-collected registry/accounts information was recovered into canonical fields, and that no data-linked product surface was submitted.

V2 addresses that without weakening identity controls:

- the certified V1 collector remains the base collection path;
- a zero-network canonical projection exposes explicit `company.*`, `financial.*`, `people.*`, `locations.*`, `website.*`, `public.*` and reserved `hiring.*` facts;
- aggregate role and location payloads are flattened into individual evidence-linked facts;
- financial values retain reporting period and currency;
- verified first-party social/contact/workforce observations become explicit canonical facts;
- the same evaluator command can emit a data-linked static HTML product;
- generic careers pages are **not** treated as hiring.

The original `claims[]` and `evidence[]` remain the source of truth. V2 only projects already-published evidence into an evaluator-friendly shape.

## Production guarantees

- Organisation number is the identity anchor.
- Missing, blocked, ambiguous, not-applicable and failed states remain explicit; missing values are never silently zeroed.
- Official Brønnøysund sources are preferred for registry facts, financials, roles, locations, group structure and workforce evidence.
- Website/domain discovery nominates candidates; publication requires exact-company page evidence.
- Social platforms are not fetched. A social-profile fact only means an exact verified company page declared that URL.
- No generic careers keyword/page is published as a hiring fact.
- No LLM, paid API, search API, sentiment model or social-platform scraper is invoked by the evaluator path.
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

If OCR executables are unavailable, annual-report workforce extraction abstains instead of fabricating a value; the terminal company result can still complete.

## One V2 evaluator command

For a 100-company evaluator JSONL batch:

```bash
uv run python scripts/run_signalpost_v2.py \
  --organisations evaluator-100.jsonl \
  --bulk brreg-enheter.csv \
  --output out/final-output-v2.jsonl \
  --report out/final-report-v2.json \
  --product-output out/signalpost-v2.html \
  --work-dir out/final-work \
  --run-id builderr-eval-v2-001 \
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

The V2 output keeps the original `OUTPUT_CONTRACT.md` envelope and adds `canonical_facts[]` plus `canonical_profile`. The HTML file is generated from the same final JSONL, so the product surface is data-linked rather than a separate mockup.

## Measured V2 canonical recovery on the immutable certified corpus

`uv run python scripts/audit_canonical_v2.py` projects the already-certified V1 1,000-company output without making any network request. This is a mapping diagnostic, not a new qualification run.

Latest CI measurement:

- 1,000 companies / 1,000 unique organisation numbers;
- **20,003 canonical facts**;
- 0 canonical validation errors;
- company record available on 998 / 1,000;
- financials on 998 / 1,000;
- people or registered locations on 999 / 1,000;
- verified company-website area on 107 / 1,000;
- hiring/public-activity area on 48 / 1,000 through validated company-declared social profiles;
- 3,984 individual role facts;
- 971 registered-location facts;
- 792 revenue facts;
- 976 operating-result facts;
- 990 workforce facts;
- 82 validated social-profile facts.

These counts show what V2 can expose from existing evidence. They do **not** predict or claim an official Builderr score.

## Certified V1 1,000-company evidence baseline

The exact certified manifest and completed V1 profiles remain committed unchanged:

- `submission/final-release-1000.jsonl`
- `submission/final-release-1000-output.jsonl.gz`

Certified identities:

- frozen manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`
- uncompressed aggregate output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`
- certified replay: `35246833190`
- 1,000 / 1,000 terminal `completed`
- 17,098 source claims / 17,050 deduplicated evidence records
- 13,628 observed conservative requests across ten 100-company chunks
- slowest chunk: 458.803 seconds
- $0 third-party API spend / 0 search-API requests

V2 does not rewrite or reselect this corpus.

## Verify this revision

```bash
uv run python scripts/verify_submission_bundle.py
uv run python scripts/audit_canonical_v2.py
uv run --with pytest pytest -q
```

## Product surface

A V2 evaluator run produces `out/signalpost-v2.html` when `--product-output` is supplied. The workspace is deterministic over the same JSONL and exposes financials, workforce, leadership, locations, verified website/contact/social facts, explicit unknowns, changes and provenance.

The product must not imply social-platform activity, followers, mailbox deliverability, reviews, sentiment or hiring unless a source-backed fact explicitly establishes it.

## Refresh proof

```bash
uv run python scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json
```

Expected result: two material changes, no false changes and no additional changes on an idempotent rerun.

## Documentation

- `SUBMISSION.md` — V2 evaluator guide and revision boundary
- `OUTPUT_CONTRACT.md` — source envelope + V2 canonical projection
- `submission/manifest.json` — machine-readable submission declaration
- `submission/EMAIL_TEMPLATE.md` — revision email template
- `docs/SUBMISSION_SOURCE_RIGHTS.md` — source/licence/acquisition policy
- `docs/FINAL_RELEASE_1000_AUDIT.md` — certified V1 evidence baseline
- `scripts/audit_canonical_v2.py` — reproducible V2 mapping audit

Historical experiment scripts/documents remain for auditability. They are not enabled by the V2 evaluator entry point unless the current submission documentation explicitly says otherwise.