# Signalpost V2 submission guide

This is the evaluator-facing source of truth for the current revision. V2 keeps the qualified V1 collector as the base collection path and adds an evidence-linked canonical projection plus a data-linked product surface. The original V1 submission remains immutable.

## 1. Revision identity

When submitting this revision, send Builderr the exact final `main` commit SHA from:

```bash
git rev-parse HEAD
```

Important historical identities:

- V1 pinned submission SHA: `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`
- V1 base collector behavior SHA: `b14ef3c277d8f1512064f865d4028e23dcd8bacf`
- certified V1 release harness SHA: `550bba0cce64a0a26d878c3b7f41eb20a55dc10e`
- certified replay: `35246833190`
- frozen 1,000 manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`
- certified V1 uncompressed output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`

V2 does not reselect or rewrite that certified corpus.

## 2. Why V2 exists

Evaluator feedback on the first submission indicated that complete output objects were returned, but relatively little already-collected registry/accounts information was recovered into the evaluator's canonical fields and no data-linked product surface was submitted.

V2 therefore prioritizes **mapping before new crawling**:

1. preserve the original `claims[]` and `evidence[]` envelope;
2. add flat typed `canonical_facts[]` that reuse the same evidence IDs;
3. group those facts in `canonical_profile` under company record, financials, people, locations, company website, jobs and public activity;
4. emit a static HTML product from the exact same final JSONL;
5. keep identity thresholds, request budgets and source-rights boundaries unchanged.

A generic careers page is never a hiring fact. V2 only reserves `hiring.job_posting` for a future source-backed real job card/feed/apply fact.

## 3. Reproducible setup

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

curl --fail --location --retry 3 --retry-delay 2 \
  'https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv' \
  --output brreg-enheter.csv
```

If Poppler/Tesseract is unavailable, annual-report OCR abstains instead of inventing a workforce value.

## 4. One V2 evaluator command

For a 100-company JSONL input:

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

The wrapper runs the existing final collector first, then performs a zero-network canonical projection, validates it, writes the V2 JSONL/report and builds the HTML product. `--product-output` is a V2-only flag and is not forwarded to the base collector.

## 5. V2 output mapping

The original output contract remains intact. V2 additionally emits:

- `canonical_facts[]`
- `canonical_profile`

Canonical namespaces:

- `company.*`
- `financial.*`
- `people.*`
- `locations.*`
- `website.*`
- `public.*`
- reserved `hiring.*`

Examples include `company.industry`, `financial.revenue`, `people.role`, `locations.registered_workplace`, `website.official`, `website.contact_email`, `public.social_profile` and `company.workforce_snapshot`.

Every canonical fact records its `source_field` and reuses the original claim's `evidence_ids`. The projection performs no network access and cannot introduce a fact unsupported by the source envelope.

## 6. Measured canonical recovery on the immutable certified 1,000

The command below projects the committed certified V1 output without crawling:

```bash
uv run python scripts/audit_canonical_v2.py
```

Current reproducible result:

| V2 mapping property | Result |
|---|---:|
| Companies | 1,000 |
| Unique organisation numbers | 1,000 |
| Canonical facts | 20,003 |
| Canonical validation errors | 0 |
| Company record area | 998 / 1,000 |
| Financials area | 998 / 1,000 |
| People / locations area | 999 / 1,000 |
| Verified company-website area | 107 / 1,000 |
| Hiring / public-activity area | 48 / 1,000 |
| Individual role facts | 3,984 |
| Registered-location facts | 971 |
| Revenue facts | 792 |
| Operating-result facts | 976 |
| Workforce facts | 990 |
| Validated social-profile facts | 82 |

These are **mapping diagnostics over the immutable certified V1 corpus**, not an official Builderr score and not proof of hidden recall/coverage thresholds.

## 7. Certified V1 evidence baseline remains unchanged

The exact certified manifest and completed V1 profiles remain in the repository:

- `submission/final-release-1000.jsonl`
- `submission/final-release-1000-output.jsonl.gz`
- `submission/final-release-1000.sha256`
- `submission/final-release-1000-output.sha256`
- `submission/final-release-1000-output.jsonl.gz.sha256`
- `submission/final-release-1000-summary.json`

Certified baseline:

| Property | Result |
|---|---:|
| Companies | 1,000 / 1,000 |
| Terminal `completed` | 1,000 / 1,000 |
| Source claims | 17,098 |
| Deduplicated evidence records | 17,050 |
| Contract errors | 0 |
| Observed conservative requests | 13,628 total |
| Structural ceiling | 2,000 / 100 |
| Slowest 100-company chunk | 458.803 s |
| Third-party API cost | $0.00 |
| Search API requests | 0 |

See `docs/FINAL_RELEASE_1000_AUDIT.md` for full V1 certification evidence.

## 8. Models, APIs, rights, secrets and safety

The V2 evaluator path invokes:

- **no LLM**;
- **no sentiment model**;
- **no paid API**;
- **no search API**;
- **no social-platform scraper/API**.

Server-side secrets required: **none**.

Sources remain:

1. Brønnøysundregistrene official bulk/API/account-copy services.
2. Wikidata only as a bounded exact-org-number website-candidate nominator.
3. Exact verified company-owned public pages for bounded website/contact/social declaration evidence.

Source rights and retention boundaries are documented in `docs/SUBMISSION_SOURCE_RIGHTS.md`. Unsafe/private network targets are rejected. Candidate domains do not become official websites without exact-company proof.

## 9. Claim boundaries

- A social-profile fact means the exact verified company page declared the URL. The social platform itself was not fetched; current ownership, activity, followers, engagement and platform verification are not claimed.
- A contact email means it appeared in bounded first-party company-page evidence and matched the verified website registered domain. Mailbox deliverability is not claimed.
- A generic careers page, careers keyword or navigation link is not a job. A future hiring claim requires a concrete role card, job-feed item or apply action with evidence.
- Missing website/job/review/news/activity/sentiment values are not converted to zero or inferred from absence.
- Workforce extraction abstains on missing or conflicting company-scope phrases.

## 10. Data-linked product surface

`--product-output out/signalpost-v2.html` builds the static workspace directly from the final V2 output generated in the same invocation. The UI is therefore linked to the submitted data rather than a separate mockup.

It exposes company identity, period-aware financials, workforce, people, locations, verified first-party external facts, explicit gaps, changes and source provenance.

## 11. Refresh proof

```bash
uv run python scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json
```

Expected result: exactly two material changes, zero false positives/negatives and no additional changes on an idempotent rerun.

## 12. Verification

Before pinning the V2 revision:

```bash
uv run python scripts/verify_submission_bundle.py
uv run python scripts/audit_canonical_v2.py
uv run --with pytest pytest -q
```

The submission verifier checks the immutable V1 certified corpus plus the current V2 entrypoint/declaration. CI also runs the canonical audit over the committed certified 1,000.

## 13. Remaining scoring uncertainty

The V2 mapping audit demonstrates that substantially more official information is exposed in explicit evaluator-friendly facts than V1 did. Builderr still owns the reference collection, matching logic, availability denominator and official score. No local count is presented as proof of an official score or qualification result.

Identity precision remains the priority: do not weaken exact-company gates merely to increase breadth.

## 14. Revision submission

Use `submission/EMAIL_TEMPLATE.md` after V2 is merged. Replace:

- `<FINAL_MAIN_SHA>` with the final merged V2 SHA;
- `<CONTACT_NAME>` with the submitter/contact name;
- `<CONTACT_EMAIL>` with the contact email;
- `<CONTACT_PHONE_OR_OTHER>` if desired.