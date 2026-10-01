# Builderr Signalpost V5 revision email template

Replace every angle-bracket placeholder before sending.

**To:** submit@builderr.ai  
**Subject:** Signalpost V5 revision — navadeep-17/signal-post

Hi Builderr team,

I am submitting a revised pinned commit for Signalpost.

Repository: https://github.com/navadeep-17/signal-post  
Exact V5 commit SHA: `<FINAL_MAIN_SHA>`  
V1 pinned commit (unchanged): `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`  
Contact name: `<CONTACT_NAME>`  
Contact email: `<CONTACT_EMAIL>`  
Contact phone/other: `<CONTACT_PHONE_OR_OTHER>`

The evaluator command remains `scripts/run_signalpost_v2.py` for backward compatibility, but the current production path now includes the qualified V3–V5 improvements while preserving the certified V1 foundation and strict exact-company gates.

Evaluator command:

```bash
uv run python scripts/run_signalpost_v2.py \
  --organisations evaluator-100.jsonl \
  --bulk brreg-enheter.csv \
  --output out/final-output.jsonl \
  --report out/final-report.json \
  --product-output out/signalpost.html \
  --work-dir out/final-work \
  --run-id builderr-eval-v5-001 \
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

Main changes since the previous revision:

1. **Annual-report company descriptions (V3).** Exact-org BRREG annual-account evidence is reused for conservative company-scope description facts with false-positive/group guards.
2. **BRREG registered-activity description fallback (V4).** Literal exact-org `aktivitet` is projected only when no stronger description exists. `vedtektsfestetFormaal` remains separately labelled as registered purpose.
3. **Official BRREG registry changes (V5).** The exact-org Enhetsregister update feed is queried in bounded batches and publishes only semantically allowlisted dated registry changes. These facts are explicitly `company.registry_change`; they are never labelled as company-authored news, social activity or hiring.
4. Existing evidence-linked canonical facts, deterministic synthesis and data-linked product rendering remain in place.

V4 description qualification:

- certified 1,000 offline audit: company-description coverage increased from 85/1,000 to 998/1,000 with 85/85 stronger descriptions preserved and zero added network requests;
- fresh 100-company confirmation: 100/100 descriptions, 1,380/2,000 conservative request charge, 422.647 s wall time, $0 third-party API cost, zero contract/canonical/synthesis/evidence errors.

V5 registry-change qualification:

- exact-production-head workflow: `36892430561`;
- fresh deterministic 100 after excluding 7,320 previously touched organisations;
- overlap: 0;
- registry-change companies: 100/100;
- published registry-change claims: 156;
- BRREG change-feed requests: 1;
- observed conservative request charge: 1,382/2,000;
- theoretical conservative ceiling: 2,000/2,000;
- wall runtime: 414.534 s;
- third-party API cost: $0.00;
- source-integrity/evidence/output-contract/canonical/synthesis errors: 0;
- all qualification checks passed.

The V5 request is reserved before base execution, so the combined theoretical challenge ceiling remains exactly 2,000 conservative requests/100 rather than silently exceeding the budget.

The registry-change claim boundary is intentionally narrow: it means Brønnøysundregistrene recorded a dated exact-org registry update. It does not mean the company authored a news announcement, social post or hiring signal. Unknown change paths abstain.

Production still invokes no LLM, no sentiment model, no paid API, no search API and no social-platform scraper/API. Server-side secrets/API keys required: **none**. Expected third-party API cost per 100-company run: **$0.00**.

The immutable certified V1 evidence baseline remains committed under `submission/`. Frozen manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`. Uncompressed certified V1 output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`.

Important validation runs:

- V4 certified registry-narrative audit: `36884388934` — PASS
- V4 fresh 100: `36884650475` — PASS
- V5 exact-production-head fresh 100: `36892430561` — PASS
- V5 merged-main Baseline CI: `36894134314` — PASS

Full evaluator/setup guide: `SUBMISSION.md`  
Source-rights declaration: `docs/SUBMISSION_SOURCE_RIGHTS.md`  
V5 production qualification: `docs/V5_BRREG_CHANGE_PRODUCTION.md`

These repository qualifications are not presented as an official Builderr score; Builderr remains authoritative for its private reference set and scoring.

Best regards,  
`<CONTACT_NAME>`
