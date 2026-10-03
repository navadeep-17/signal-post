# Builderr Signalpost V8 revision email template

Replace every angle-bracket placeholder before sending.

**To:** submit@builderr.ai  
**Subject:** Signalpost V8 evaluator compatibility revision — navadeep-17/signal-post

Hi Builderr team,

I am submitting a revised pinned `main` commit for Signalpost.

Repository: https://github.com/navadeep-17/signal-post  
Exact final `main` commit SHA: `<FINAL_MAIN_SHA>`  
V1 pinned commit (unchanged): `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`  
Contact name: `<CONTACT_NAME>`  
Contact email: `<CONTACT_EMAIL>`  
Contact phone/other: `<CONTACT_PHONE_OR_OTHER>`

## Recommended evaluator command

Please use the batch-size-adaptive V8 entrypoint:

```bash
uv run python scripts/run_signalpost_v8.py \
  --organisations evaluator-companies.jsonl \
  --bulk brreg-enheter.csv \
  --output out/final-output.jsonl \
  --report out/final-report.json \
  --product-output out/signalpost.html \
  --work-dir out/final-work \
  --run-id builderr-eval-v8-001 \
  --workers 8 \
  --site-timeout 6 \
  --wikidata-timeout 8 \
  --max-third-party-cost-usd 0 \
  --annual-workforce-workers 4 \
  --annual-workforce-timeout 60 \
  --annual-workforce-min-start-interval 2.1 \
  --annual-workforce-ocr-pages 8 \
  --annual-workforce-ocr-dpi 110
```

V8 reads the organisation file supplied at evaluation time, derives its exact company count, validates any explicit count if one is provided, and then delegates to the already-qualified V7 evaluator/product path. This removes the previous evaluator-facing hard-coded 100-company assumption while leaving collection, exact-company identity gates, publication rules, canonical projection, synthesis and UI behavior unchanged.

When explicit internal limits are not supplied, V8 derives conservative internal request/runtime validation ceilings from the actual input size. For the existing 100-company smoke test, it resolves to the same previously qualified 2,000-request and 2,400-second settings. Explicit evaluator-provided limits remain authoritative and are preserved.

## V7/V8 product-surface improvements

The generated evaluator-facing workspace includes:

- global company search and discovery;
- evidence-backed company profiles;
- an evidence-linked six-question decision brief;
- reporting/effective/publication date context when already present in evidence;
- descriptive side-by-side comparison with differences-only filtering;
- recent canonical change history;
- evidence drawer and verify-all-evidence flow;
- deterministic evidence-bounded Ask Signalpost answers;
- explicit unknown/data-gap handling;
- careers-page discovery and grounded hiring answers;
- responsive/mobile and keyboard-accessibility behavior.

The careers-page boundary remains conservative: a verified company-owned careers page is a `hiring.careers_page` signal only. It does not establish an active vacancy unless a separate qualified `hiring.job_posting` fact exists.

## Qualified 100-company release-path evidence

The V7 production path underneath V8 has been exercised end-to-end on a reproducible 100-company cohort with:

- 100/100 terminal outputs;
- zero canonical validation errors;
- zero synthesis validation errors;
- decision briefs for 100/100 companies;
- 1,364 / 2,000 observed conservative request charge;
- 2,000 / 2,000 theoretical conservative request ceiling;
- 311.985 seconds wall runtime;
- $0.00 third-party API cost;
- zero search API requests;
- verified evaluator-facing V6 workspace generation.

V8 preserves those 100-company settings exactly while making the evaluator entrypoint batch-size adaptive.

Production invokes no LLM, sentiment model, paid API, search API, or social-platform scraper/API. Server-side secrets/API keys required: **none**. Expected third-party API cost: **$0.00**.

Evaluator-path addendum: `submission/V8_EVALUATOR_PATH.md`  
Previous V7 evaluator/product addendum: `submission/V7_EVALUATOR_PATH.md`  
Detailed certified V5 guide: `SUBMISSION.md`  
Machine-readable certified lineage: `submission/manifest.json`  
Source-rights declaration: `docs/SUBMISSION_SOURCE_RIGHTS.md`

The certified V5/V7 evidence lineage remains unchanged. Builderr remains authoritative for the supplied company batch, evaluator resource limits, checked collection and official score; no new official score is claimed here.

Best regards,  
`<CONTACT_NAME>`
