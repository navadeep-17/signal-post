# Signalpost V8 evaluator-path addendum

Updated: 2026-10-03

This addendum supersedes the V7 evaluator command only. The qualified V7/V5 data and product pipeline remains unchanged underneath it.

## Why V8 exists

Builderr supplies the evaluator company file at run time and requires one terminal result per supplied organisation, including when the official batch grows beyond the 100-company local smoke test.

V8 removes the evaluator-facing hard-coded batch-size assumption without changing collection, identity, publication, canonical, synthesis or UI logic.

## Recommended one-command evaluator path

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

Do not hard-code `--expected-count` in the normal evaluator command. V8 reads Builderr's supplied organisation file, validates it, derives the exact company count and injects that count into the already-qualified V7 path.

## Internal budget compatibility

When no explicit internal limits are supplied, V8 derives conservative validation ceilings from the actual evaluator batch:

- request ceiling: `max(2000, 20 × company_count)`;
- wall-runtime validation ceiling: `max(2400, 3 × company_count)` seconds.

These are Signalpost's internal safety/validation ceilings, not a claim about Builderr infrastructure limits. Builderr's evaluator/harness remains authoritative for the actual run-time and resource budget.

For the existing 100-company smoke test, V8 derives exactly the previously qualified settings:

- expected count: 100;
- conservative request ceiling: 2,000;
- wall-runtime validation ceiling: 2,400 seconds.

For a 1,200-company input, V8 derives 1,200 rather than 100 and passes the exact count through V7 → V2 → the pinned base runner and V6 product builder.

If an explicit `--expected-count` is supplied and does not match the input file, V8 fails before research begins rather than silently dropping or inventing rows.

Explicit `--max-challenge-requests` and `--max-wall-runtime-seconds` values are still honored when the evaluator provides them.

## Delegation path

V8 is intentionally thin:

1. parse and validate Builderr's supplied organisation file;
2. derive/validate the exact input count;
3. derive internal validation ceilings only when the caller did not provide them;
4. invoke `scripts/run_signalpost_v7.py` once with those explicit settings;
5. V7 runs the qualified V5/V2 evidence path and deterministically builds the V6 evaluator-facing workspace.

No new source, network connector, model, claim type, identity heuristic or publication rule is introduced by V8.

## Existing V7 product behavior remains unchanged

The final workspace still includes global search, evidence-backed profiles, evidence-linked decision briefs, dates, descriptive comparison, recent canonical changes, evidence drawer, verify-all flow, deterministic Ask Signalpost, data-gap handling, conservative careers-page semantics, responsive/mobile behavior and keyboard accessibility.

A verified company-owned careers page remains only a `hiring.careers_page` signal. It does not establish an active vacancy without a separately qualified `hiring.job_posting` fact.

Builderr remains authoritative for the checked collection, actual evaluator resource limits and official score. Repository qualification results are engineering evidence only.
