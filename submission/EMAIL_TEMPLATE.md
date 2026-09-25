# Builderr Signalpost V2 revision email template

Replace every angle-bracket placeholder before sending.

**To:** submit@builderr.ai  
**Subject:** Signalpost V2 revision — navadeep-17/signal-post

Hi Builderr team,

I am submitting a revised pinned commit for Signalpost.

Repository: https://github.com/navadeep-17/signal-post  
Exact V2 commit SHA: `<FINAL_MAIN_SHA>`  
V1 pinned commit (unchanged): `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`  
Contact name: `<CONTACT_NAME>`  
Contact email: `<CONTACT_EMAIL>`  
Contact phone/other: `<CONTACT_PHONE_OR_OTHER>`

V2 keeps the V1 collector/identity gates and adds a zero-network canonical mapping layer plus a data-linked product surface. It does not reselect or rewrite the certified V1 1,000-company corpus.

Evaluator command:

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

V2 output preserves the original `claims[]` / `evidence[]` contract and adds evidence-linked `canonical_facts[]` and `canonical_profile` fields. The same command writes `out/signalpost-v2.html` from the final V2 JSONL.

The reproducible zero-network mapping audit over the immutable certified V1 1,000-company output yields 20,003 canonical facts with zero canonical validation errors. This is a local mapping diagnostic, not a claimed official score.

Runtime: Python 3.12+, `uv`, `poppler-utils`, `tesseract-ocr`.

Models/APIs: the evaluator path invokes no LLM, no sentiment model, no paid API, no search API and no social-platform scraper/API. It uses official Brønnøysundregistrene sources, bounded Wikidata candidate lookup and independently verified company-owned public pages.

Server-side secrets/API keys required: **none**.

Expected third-party API cost per 100-company run: **$0.00**.

Hiring boundary: a generic careers page is not treated as a hiring fact. A hiring claim requires concrete source-backed role/job/apply evidence.

Certified V1 evidence baseline: the exact 1,000-company manifest and completed profiles remain committed under `submission/`. Frozen manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`. Uncompressed certified V1 output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`.

Full evaluator/setup/source-rights guide: `SUBMISSION.md`.

Best regards,  
`<CONTACT_NAME>`
