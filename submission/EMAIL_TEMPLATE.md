# Builderr Signalpost V2 revision email template

Replace every angle-bracket placeholder before sending.

**To:** submit@builderr.ai  
**Subject:** Signalpost V2 revision — navadeep-17/signal-post

Hi Builderr team,

I am submitting a revised pinned commit for Signalpost in response to the private technical diagnostic.

Repository: https://github.com/navadeep-17/signal-post  
Exact V2 commit SHA: `<FINAL_MAIN_SHA>`  
V1 pinned commit (unchanged): `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`  
Contact name: `<CONTACT_NAME>`  
Contact email: `<CONTACT_EMAIL>`  
Contact phone/other: `<CONTACT_PHONE_OR_OTHER>`

V2 keeps the V1 collector, output adapter and identity gates unchanged, and adds zero-network evaluator-facing registry/canonical projections plus a data-linked five-area product surface. It does not reselect or rewrite the certified V1 1,000-company corpus.

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

V2 output preserves the original `claims[]` / `evidence[]` contract and adds evidence-linked `canonical_facts[]` and `canonical_profile`. The same command can emit the data-linked HTML product from the final V2 JSONL.

The reproducible zero-network mapping audit over the immutable certified V1 1,000-company output yields **19,951 canonical facts with zero canonical validation errors**. This is an engineering mapping diagnostic, not a claimed official score.

I also ran a deterministic 300-company V2 validation after excluding 6,900 known internal development/certification companies. It completed 300/300 companies with 4,052 conservative requests against a 6,000 normalized ceiling, 1,105.442 seconds wall time, $0 third-party API cost, 0 search-API requests, 0 contract errors and 0 canonical errors. Because Builderr's private 700-company capture is not available to the repository, I am not claiming that this 300 is disjoint from that private set.

The retained fresh capture was replayed through the final stricter V2 projections with zero network requests. The final replay produced 7,165 canonical facts with zero contract/canonical errors. It produced **0 strict job-posting facts and 0 strict dated company-update facts**, so I am not claiming a jobs/news coverage improvement from the bounded first-party activity layer.

Hiring/activity boundary: a generic careers page or news index is never published as a hiring/activity fact. A job requires a same-site role detail URL, specific title, job-detail marker and explicit apply/application action. A company update requires a same-site article/update detail URL, specific title and explicit date.

Runtime: Python 3.12+, `uv`, `poppler-utils`, `tesseract-ocr`.

Models/APIs: the evaluator path invokes no LLM, no sentiment model, no paid API, no search API and no social-platform scraper/API. It uses official Brønnøysundregistrene sources, bounded Wikidata candidate lookup and independently verified company-owned public pages.

Server-side secrets/API keys required: **none**.  
Expected third-party API cost per 100-company run: **$0.00**.

Certified V1 evidence baseline remains committed under `submission/`. Frozen manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`. Uncompressed certified V1 output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`.

Checked-in data-linked product: `submission/signalpost-v2.html`.  
Full evaluator/setup/source-rights guide: `SUBMISSION.md`.

Best regards,  
`<CONTACT_NAME>`
