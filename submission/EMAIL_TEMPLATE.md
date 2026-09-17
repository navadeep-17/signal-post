# Builderr Signalpost submission email template

Replace every angle-bracket placeholder before sending.

**To:** submit@builderr.ai  
**Subject:** Signalpost submission — navadeep-17/signal-post

Repository: https://github.com/navadeep-17/signal-post  
Exact commit SHA: `<FINAL_MAIN_SHA>`  
Contact name: `<CONTACT_NAME>`  
Contact email: `<CONTACT_EMAIL>`  
Contact phone/other: `<CONTACT_PHONE_OR_OTHER>`

Evaluator command:

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

Runtime: Python 3.12+, `uv`, `poppler-utils`, `tesseract-ocr`.

Models/APIs: production invokes no LLM, no sentiment model, no paid API, no search API and no social-platform scraper/API. It uses official Brønnøysundregistrene sources, bounded Wikidata candidate lookup and independently verified company-owned public pages.

Server-side secrets/API keys required: **none**.

Expected third-party API cost per 100-company run: **$0.00**.

Submitted corpus: exact 1,000-company manifest and certified completed profiles are committed under `submission/`. Frozen manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`. Uncompressed certified output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`.

Full evaluator/setup/source-rights guide: `SUBMISSION.md`.
