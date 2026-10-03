# Builderr Signalpost V7 revision email template

Replace every angle-bracket placeholder before sending.

**To:** submit@builderr.ai  
**Subject:** Signalpost V7 evaluator/product revision — navadeep-17/signal-post

Hi Builderr team,

I am submitting a revised pinned `main` commit for Signalpost.

Repository: https://github.com/navadeep-17/signal-post  
Exact final `main` commit SHA: `<FINAL_MAIN_SHA>`  
V1 pinned commit (unchanged): `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`  
Contact name: `<CONTACT_NAME>`  
Contact email: `<CONTACT_EMAIL>`  
Contact phone/other: `<CONTACT_PHONE_OR_OTHER>`

## Recommended evaluator command

The recommended one-command evaluator path is now `scripts/run_signalpost_v7.py`:

```bash
uv run python scripts/run_signalpost_v7.py \
  --organisations evaluator-100.jsonl \
  --bulk brreg-enheter.csv \
  --output out/final-output.jsonl \
  --report out/final-report.json \
  --product-output out/signalpost.html \
  --work-dir out/final-work \
  --run-id builderr-eval-v7-001 \
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

The V7 wrapper preserves the certified V5 evaluator/data runner. It first runs `scripts/run_signalpost_v2.py` with the original arguments unchanged. Only after that succeeds, it deterministically rebuilds `--product-output` from the emitted final JSONL using `scripts/build_v6_ui.py`. The V6 build is local and adds no network requests or third-party API cost.

## V7 product-surface improvements

The generated evaluator-facing workspace now includes:

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

## Certified data lineage

The certified V5 evidence/data lineage remains unchanged. The existing evaluator/data runner, collector behavior, canonical projection, request ceilings, source-rights declarations, immutable certified release artifacts, and V5 smoke-test evidence are not rewritten by the V7 wrapper.

Current committed smoke-test report: `submission/v5-smoke-100-run-report.json`.

That report records 100 inputs / 100 terminal outputs, zero contract/canonical/synthesis/registry-integrity errors, 1,382/2,000 observed conservative request charge, a 2,000/2,000 theoretical ceiling, 414.534 seconds wall time, $0.00 third-party API cost, and zero search-API requests. It is engineering evidence, not a claimed Builderr score.

Production invokes no LLM, sentiment model, paid API, search API, or social-platform scraper/API. Server-side secrets/API keys required: **none**. Expected third-party API cost per 100-company run: **$0.00**.

Evaluator-path addendum: `submission/V7_EVALUATOR_PATH.md`  
Detailed certified V5 guide: `SUBMISSION.md`  
Machine-readable certified lineage: `submission/manifest.json`  
Source-rights declaration: `docs/SUBMISSION_SOURCE_RIGHTS.md`

Builderr remains authoritative for the checked collection and official score; no official score is claimed here.

Best regards,  
`<CONTACT_NAME>`
