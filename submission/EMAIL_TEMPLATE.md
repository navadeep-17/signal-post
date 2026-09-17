# Builderr submission email template

Replace `<FINAL_MAIN_SHA>` with `git rev-parse HEAD` from the exact submitted checkout.

**To:** submit@builderr.ai  
**Subject:** Signalpost submission — navadeep-17/signal-post

Repository: https://github.com/navadeep-17/signal-post  
Commit SHA: `<FINAL_MAIN_SHA>`

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

Models/APIs: the production runner invokes no LLM, no sentiment model, no paid API and no search API. It uses official Brønnøysundregistrene sources, bounded Wikidata candidate lookup, and independently verified company-owned public pages. Social platforms are not fetched; only profile URLs declared by verified company pages may be published.

Expected third-party API cost per 100-company run: **$0.00**.

Certified release evidence: 1,000/1,000 terminal completed, 0 contract errors, frozen manifest SHA-256 `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`, aggregate output SHA-256 `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`.

Evaluator/setup/source-rights details: `SUBMISSION.md`.
