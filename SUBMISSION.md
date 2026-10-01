# Signalpost V5 submission guide

Updated: 2026-10-01

This is the evaluator-facing source of truth for the current Signalpost revision. V5 preserves the certified V1 foundation and strict company-identity gates, keeps the V2 canonical/product layer, and adds the subsequently qualified V3–V5 intelligence improvements:

1. conservative annual-report company descriptions;
2. exact-org BRREG registered activity as a zero-network description fallback;
3. bounded exact-org BRREG registry-change history for dated currentness/change context.

Builderr remains authoritative for the private reference collection and official score. Repository qualification metrics below are engineering evidence, not a claimed Builderr score.

## 1. Revision identity

Submit Builderr the exact final merged `main` commit SHA:

```bash
git rev-parse HEAD
```

Immutable historical identities:

- V1 pinned submission SHA: `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`
- V1 base collector behavior SHA: `b14ef3c277d8f1512064f865d4028e23dcd8bacf`
- V1 runner Git blob: `9be89b9827135b1ed703318e1d189d5d3b8ca604`
- V1 output-adapter Git blob: `c163f493017e39252ef200e68d53bcebc12930b4`
- certified V1 release harness SHA: `550bba0cce64a0a26d878c3b7f41eb20a55dc10e`
- certified 1,000 replay: `35246833190`
- frozen 1,000 manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`
- certified V1 output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`

Current production milestone before submission-only packaging:

- V5 merged production SHA: `a0ca7bb1ab19de5c7c96b2e5e862763c27f8e34b`
- V5 production wrapper Git blob: `07cdd0f5f1edb6c425ac8b8c9ae90e6357c87643`
- V5 BRREG-change connector Git blob: `9d22bcaf494a356a47985fc731cef6c2e0ecd493`
- post-merge Baseline CI: `36894134314` — PASS

Submission-only documentation/verifier commits may come after the production SHA; they must not alter the production behavior above.

## 2. What the current evaluator path does

For each Norwegian organisation number, Signalpost:

1. resolves the exact legal entity from Brønnøysundregistrene;
2. collects official registry/accounting/roles/group/location evidence;
3. resolves a company website only through bounded candidates and exact-entity verification;
4. projects conservative first-party contact/social facts from retained verified company pages;
5. extracts official workforce evidence from the live registry or bounded annual-account copy when qualified;
6. extracts conservative company-description evidence from qualified annual reports;
7. falls back to literal exact-org BRREG `aktivitet` when no stronger published company description exists;
8. fetches recent exact-org BRREG update history in one bounded batch per 100 companies and publishes only semantically allowlisted registry changes;
9. projects source-backed claims into canonical facts and deterministic evidence-linked synthesis;
10. optionally renders a static HTML workspace directly from the final JSONL.

The V5 BRREG update feed is explicitly an **official registry-change source**. Its events are not labelled as company-authored news, hiring, social activity, or press releases.

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

If Poppler/Tesseract is unavailable, OCR-dependent annual-report extraction abstains instead of inventing a value.

## 4. One evaluator command

For a 100-company JSONL input:

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

`scripts/run_signalpost_v2.py` remains the single evaluator entrypoint. The name is retained for compatibility with the previously submitted revision; its current implementation includes the V3–V5 qualified layers described here.

## 5. Output contract and canonical mapping

The original envelope remains intact:

- `organisation_number`
- `run`
- `claims[]`
- `evidence[]`
- `changes[]`
- `errors[]`
- `operations`

The current wrapper additionally emits:

- `canonical_facts[]`
- `canonical_profile`
- `synthesis`

Canonical namespaces include `company.*`, `financial.*`, `people.*`, `locations.*`, `website.*`, `public.*` and `hiring.*`.

Important current facts include:

- `company.industry`
- `company.municipality_number`
- `company.workforce_snapshot`
- `company.registry_change`
- `financial.revenue`
- `people.role`
- `locations.registered_workplace`
- `website.official`
- `website.description`
- `website.contact_email`
- `public.social_profile`
- strict `hiring.job_posting`
- strict `public.company_update`

Every canonical fact retains its source field and source evidence IDs.

### Preserved V2 compatibility baseline

The V2 canonical/product layer remains part of the current evaluator path and its historical certified-corpus diagnostics are intentionally preserved for regression and audit continuity. The zero-network canonical audit over the immutable certified 1,000 produced **19,951 canonical facts** with zero canonical validation errors, including **3,932** current individual role facts.

The final fresh V2 projection replay also kept the strict activity boundary:

| V2 diagnostic | Result |
|---|---:|
| Strict job-posting facts | **0** |
| Strict dated company-update facts | **0** |

Those zeroes are not converted into negative business claims; they mean only that no retained page met the strict publication gates in that diagnostic cohort.

Compatibility claim boundaries remain unchanged:

- a generic careers page or section index is not a hiring fact;
- a company-declared social URL does not imply that Signalpost fetched the platform page, verified ownership/activity, or observed any follower count;
- a retained first-party contact email does not establish mailbox deliverability;
- missing public activity is not interpreted as proof that no activity exists.

## 6. Exact-company and publication boundaries

Signalpost does not trade precision for local fact count.

Website publication requires exact-company evidence. Parent, brand, franchise and namesake pages abstain unless the target legal entity is independently proven.

A strict job posting requires:

- same verified company-owned site;
- role/job detail URL rather than a generic section root;
- specific title;
- job-detail marker;
- explicit apply/application action.

A strict company update requires:

- same verified company-owned site;
- specific article/update detail URL;
- non-generic title;
- explicit publication date.

Company-declared social-profile facts mean only that a verified first-party page declared the URL. Social platforms themselves are not fetched. Contact-email facts require retained first-party evidence and domain agreement with the verified company site.

## 7. Company descriptions — V3 and V4

### V3 annual-report descriptions

V3 reuses exact-org BRREG annual-account copies and publishes only conservative company-scope descriptive phrases after false-positive guards. Annual-report extraction abstains rather than inferring from weak or group-only text.

### V4 exact-org BRREG registered activity fallback

V4 discovered that the exact-org registry row already retained literal `aktivitet` text for nearly every company. The zero-network registry-narrative projector uses that literal source text only when no stronger company description has already been published.

Certified 1,000 offline audit (`36884388934`):

- descriptions before: 85 / 1,000
- descriptions after: 998 / 1,000
- net-new companies: 913
- stronger descriptions preserved: 85 / 85
- registered-purpose companies: 961 / 1,000
- network requests added: 0
- contract/canonical/synthesis/evidence errors: 0

Fresh zero-overlap 100 (`36884650475`):

- terminal companies: 100 / 100
- description companies: 100 / 100
- registry-activity fallback: 85 / 100
- registered-purpose companies: 97 / 100
- conservative request charge: 1,380 / 2,000
- wall runtime: 422.647 s
- third-party cost: $0.00
- hard-check failures: 0

`vedtektsfestetFormaal` remains separately labelled `registered_purpose`; legal purpose is never silently substituted for registered activity.

## 8. Official registry changes — V5

V5 uses the official Enhetsregister update API:

`https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter`

Production behavior:

- exact organisation-number filter;
- up to 100 organisations/request;
- `includeChanges=true`;
- 365-day lookback;
- at most three newest qualified events/company;
- allowlisted, interpretable change paths only;
- unexpected organisations are integrity failures;
- BRREG event id/date/path/source/hash retained;
- canonical type `registry_change` / field `company.registry_change`;
- registry events remain outside `public_activity`;
- synthesis labels them `official BRREG registry change`.

The new shared request budget is reserved **before** invoking the base collector. For 100 companies, one logical BRREG change-feed request receives the same conservative multiplier of two, so the base runner gets 1,998 and the combined theoretical ceiling remains exactly 2,000.

Exact-production-head fresh qualification (`36892430561`, production SHA `2c745ed22232a443fe2c9e8fc3f49a66c725be0e`):

| Property | Result |
|---|---:|
| Fresh companies | 100 |
| Prior organisations excluded | 7,320 |
| Overlap | 0 |
| Registry-change companies | 100 / 100 |
| Published registry-change claims | 156 |
| BRREG change-feed requests | 1 |
| Integrity/evidence/contract/canonical/synthesis errors | 0 |
| Observed conservative charge | 1,382 / 2,000 |
| Theoretical conservative ceiling | 2,000 / 2,000 |
| Wall runtime | 414.534 s |
| Third-party cost | $0.00 |
| Search API requests | 0 |
| Qualification | PASS |

Fresh cohort SHA-256:

`a7a18aab77f9c7192ba5e55b31e5dd225718a20b6b0f6d036fb78a2a524d412d`

See `docs/V5_BRREG_CHANGE_PRODUCTION.md` for the full path-family audit and evidence boundary.

## 9. Certified V1 release remains immutable

Repository artifacts retained under `submission/`:

- `final-release-1000.jsonl`
- `final-release-1000-output.jsonl.gz`
- SHA sidecars
- `final-release-1000-summary.json`
- `signalpost-v2.html`

Certified baseline:

| Property | Result |
|---|---:|
| Companies | 1,000 / 1,000 |
| Terminal completed | 1,000 / 1,000 |
| Claims | 17,098 |
| Deduplicated evidence | 17,050 |
| Contract errors | 0 |
| Conservative requests | 13,628 total |
| Structural ceiling | 2,000 / 100 |
| Slowest chunk | 458.803 s |
| Third-party API cost | $0.00 |
| Search API requests | 0 |

The checked-in V2 HTML remains a deterministic historical/certified artifact. A compatibility regression ensures V5 does not mutate the old synthesis shape for contracts without registry-change facts.

## 10. Models, APIs, rights and secrets

Production uses:

1. Brønnøysundregistrene official bulk/API/account-copy/update services;
2. Wikidata only for bounded exact-org website-candidate nomination;
3. exact verified company-owned public pages for bounded first-party website/contact/social/job/update evidence.

Production invokes:

- no LLM API;
- no sentiment model;
- no paid API;
- no search API;
- no social-platform scraper/API.

Server-side secrets required: **none**.

Third-party API spend policy: **$0.00 per 100-company run**.

Source rights, attribution and retention boundaries are documented in `docs/SUBMISSION_SOURCE_RIGHTS.md`.

## 11. Refresh and change explanation

The original deterministic refresh replay remains valid:

```bash
uv run python scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json
```

V5 additionally exposes dated official registry-change facts for currentness/change context. These registry events do not pretend to contain a previous value when BRREG only provides the new patch value, so they are not forged into the existing `changes[]` refresh-diff contract. Instead they remain explicit evidence-backed `official_registry_change` claims/canonical facts and can support the synthesis `what_changed` section.

## 12. Product surface

`--product-output out/signalpost.html` builds a static workspace directly from the final JSONL. It exposes:

1. company record;
2. financials;
3. people & locations;
4. company website;
5. hiring & public activity;
6. deterministic company synthesis;
7. `what changed` and unknown boundaries;
8. source/evidence links.

The current renderer uses the final output, not a parallel demo dataset.

## 13. Verification before submission

Run:

```bash
uv run python scripts/verify_submission_bundle.py
uv run python scripts/audit_canonical_v2.py
uv run --with pytest pytest -q
```

The verifier checks the immutable V1 base identities and certified corpus, the current evaluator entrypoint/declarations, source/product files and manifest integrity. Baseline CI runs these checks on every revision.

Relevant green workflows:

- certified V1 replay: `35246833190`
- V4 certified 1,000 registry narrative audit: `36884388934`
- V4 fresh 100: `36884650475`
- V5 source screen: `36885512441`
- V5 fresh production qualification: `36890996638`
- V5 exact-production-head replay: `36892430561`
- V5 merged-main Baseline CI: `36894134314`

## 14. Remaining scoring uncertainty

Builderr owns the private reference set, matching logic, availability denominator and official score. The repository therefore does not claim that its local/fresh qualification proves the official 21/35 coverage gate, 60% weighted external-recall gate, 95% external-precision gate, or 65/100 total threshold.

The next engineering decision should be driven by the next concrete Builderr evaluation of the pinned V5 revision rather than by further speculative connector count.

## 15. Revision submission

Use `submission/EMAIL_TEMPLATE.md` after this finalization branch is merged. Replace `<FINAL_MAIN_SHA>` with the final merged `main` SHA and fill the contact placeholders before sending.
