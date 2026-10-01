# Signalpost V5 submission guide

Updated: 2026-10-01

This is the evaluator-facing source of truth for the current Signalpost revision. Builderr remains authoritative for the checked collection and official score; all repository metrics below are engineering evidence, not a claimed competition score.

## 1. Current revision and identity

Submit Builderr the exact final merged `main` commit SHA:

```bash
git rev-parse HEAD
```

The production-code lineage is pinned separately from later documentation-only cleanup:

- V1 pinned submission SHA: `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`
- V1 base collector behavior SHA: `b14ef3c277d8f1512064f865d4028e23dcd8bacf`
- V1 runner Git blob: `9be89b9827135b1ed703318e1d189d5d3b8ca604`
- V1 output-adapter Git blob: `c163f493017e39252ef200e68d53bcebc12930b4`
- V5 merged production SHA: `a0ca7bb1ab19de5c7c96b2e5e862763c27f8e34b`
- V5 production wrapper Git blob: `07cdd0f5f1edb6c425ac8b8c9ae90e6357c87643`
- V5 BRREG-change connector Git blob: `9d22bcaf494a356a47985fc731cef6c2e0ecd493`

The final repository SHA may be newer because documentation, smoke evidence, and verification metadata can be improved without changing those production files.

## 2. What the evaluator path does

For every supplied Norwegian organisation number, Signalpost:

1. resolves the exact legal entity from Brønnøysundregistrene;
2. collects official registry, accounting, roles, group and location evidence;
3. resolves a company website only through bounded candidates and exact-entity verification;
4. projects conservative first-party contact-email and company-declared social-profile facts;
5. extracts workforce evidence from the registry or a qualified annual-account copy;
6. extracts conservative company-scope description evidence from qualified annual reports;
7. falls back to literal exact-org BRREG `aktivitet` when no stronger description exists;
8. fetches recent exact-org BRREG update history in one bounded batch and publishes only semantically allowlisted registry changes;
9. projects source-backed claims into canonical facts and deterministic evidence-linked synthesis;
10. optionally renders a static HTML workspace from the exact final JSONL.

The V5 change feed is explicitly an **official registry-change source**. It is never relabelled as company-authored news, hiring, social activity or a press release.

## 3. Clean-machine setup

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

If OCR tooling is unavailable, OCR-dependent extraction abstains rather than fabricating a value.

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

`scripts/run_signalpost_v2.py` remains the single evaluator entrypoint. Its filename is retained for backward compatibility; its current implementation includes the qualified V3–V5 layers.

## 5. Current 100-company smoke-test evidence

The current committed smoke-test report is:

`submission/v5-smoke-100-run-report.json`

It is derived from exact-production-head workflow `36892430561` and the retained Actions artifact `v5-brreg-change-production-qualification`.

| Property | Result |
|---|---:|
| Input companies | 100 |
| Final result objects | 100 |
| Zero-overlap against prior internal cohorts | yes |
| Terminal-result check | PASS |
| Contract validation errors | 0 |
| Canonical validation errors | 0 |
| Synthesis validation errors | 0 |
| Registry-change integrity errors | 0 |
| Observed conservative request charge | 1,382 / 2,000 |
| Theoretical conservative ceiling | 2,000 / 2,000 |
| Wall runtime | 414.534 s / 2,400 s |
| Third-party API cost | $0.00 |
| Search API requests | 0 |

Fresh selection SHA-256:

`a7a18aab77f9c7192ba5e55b31e5dd225718a20b6b0f6d036fb78a2a524d412d`

This smoke test proves reproducibility and terminal-output behavior for that cohort. It is not an official Builderr score.

## 6. Output contract and canonical mapping

The original source envelope remains authoritative:

- `organisation_number`
- `run`
- `claims[]`
- `evidence[]`
- `changes[]`
- `errors[]`
- `operations`

The evaluator wrapper additionally emits:

- `canonical_facts[]`
- `canonical_profile`
- `synthesis`

Canonical namespaces include `company.*`, `financial.*`, `people.*`, `locations.*`, `website.*`, `public.*` and `hiring.*`. Every canonical fact retains its source field and source evidence IDs.

Important current facts include `company.industry`, `company.workforce_snapshot`, `company.registry_change`, `financial.revenue`, `people.role`, `locations.registered_workplace`, `website.official`, `website.description`, `website.contact_email`, `public.social_profile`, strict `hiring.job_posting` and strict `public.company_update`.

### Preserved V2 compatibility evidence

The V2 canonical/product layer is still part of V5. The immutable certified 1,000-company projection contains **19,951 canonical facts** with zero canonical validation errors, including **3,932 current individual role facts**.

The historical fresh V2 diagnostic retained the strict activity boundary:

| V2 diagnostic | Result |
|---|---:|
| Strict job-posting facts | **0** |
| Strict dated company-update facts | **0** |

Those zeroes do not mean the companies had no jobs or updates. They mean only that no retained page in that historical diagnostic met the strict publication gate.

## 7. Exact-company and publication boundaries

Signalpost does not trade exact-company precision for local fact count. Parent, brand, franchise and namesake pages abstain unless the target legal entity is independently proven.

A strict job posting requires:

- the same verified company-owned site;
- a role/job detail URL rather than a generic section root;
- a specific title;
- a job-detail marker;
- an explicit apply/application action.

A strict company update requires:

- the same verified company-owned site;
- a specific article/update detail URL;
- a non-generic title;
- an explicit publication date.

A generic careers page or section index is not a hiring fact. A company-declared social URL means only that an exact verified company page declared the URL; it does not imply that Signalpost fetched the platform, verified current ownership, or observed any follower count. A retained first-party contact email does not establish mailbox deliverability. Missing public activity is never converted into proof that no activity exists.

## 8. Company descriptions — V3 and V4

V3 reuses exact-org BRREG annual-account copies and publishes only conservative company-scope descriptive phrases after false-positive and group-only guards.

V4 adds literal exact-org BRREG `aktivitet` as a zero-network fallback only when no stronger company description is already published. `vedtektsfestetFormaal` remains separately labelled `registered_purpose`; legal purpose is never silently substituted for operating activity.

Certified 1,000 offline audit (`36884388934`):

- descriptions before: 85 / 1,000
- descriptions after: 998 / 1,000
- net-new companies: 913
- stronger descriptions preserved: 85 / 85
- network requests added: 0
- contract/canonical/synthesis/evidence errors: 0

Fresh zero-overlap 100 (`36884650475`):

- terminal companies: 100 / 100
- description companies: 100 / 100
- registry-activity fallback: 85 / 100
- conservative request charge: 1,380 / 2,000
- wall runtime: 422.647 s
- third-party cost: $0.00
- hard-check failures: 0

## 9. Official registry changes — V5

Production endpoint:

`https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter`

V5 behavior:

- exact organisation-number filtering;
- up to 100 organisations/request;
- `includeChanges=true`;
- 365-day lookback;
- at most three newest qualified events/company;
- allowlisted stable change paths only;
- unexpected organisations are integrity failures;
- BRREG event id/date/path/source/hash retained;
- canonical type `registry_change` / field `company.registry_change`;
- registry events remain outside `public_activity`.

The shared request budget is reserved before the base collector runs. For 100 companies, one logical BRREG change-feed request has a conservative charge of two, leaving 1,998 for the base runner and keeping the combined theoretical ceiling at exactly 2,000.

The current fresh V5 smoke test published 156 qualified registry-change claims across 100/100 companies with one BRREG change-feed request and zero integrity/evidence/contract/canonical/synthesis errors.

See `docs/V5_BRREG_CHANGE_PRODUCTION.md` for the full path-family audit and evidence boundary.

## 10. Certified historical baseline

The immutable certified V1 evidence baseline remains committed under `submission/`:

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
| Slowest 100-company chunk | 458.803 s |
| Third-party API cost | $0.00 |
| Search API requests | 0 |

The checked-in `submission/signalpost-v2.html` is historical/certified evidence. Current evaluator runs generate their product surface from the current final JSONL via `--product-output`.

## 11. Models, APIs, rights and secrets

Production uses:

1. Brønnøysundregistrene official bulk/API/account-copy/update services;
2. Wikidata only for bounded exact-org official-website candidate nomination;
3. exact verified company-owned public pages for bounded first-party website/contact/social/job/update evidence.

Production invokes:

- no LLM API;
- no sentiment model;
- no paid API;
- no search API;
- no social-platform scraper/API.

Server-side secrets required: **none**.

Third-party API spend policy: **$0.00 per 100-company run**.

Source rights, attribution, safe URL handling and retention boundaries are documented in `docs/SUBMISSION_SOURCE_RIGHTS.md`.

## 12. Refresh, currentness and idempotency

The deterministic refresh replay remains available:

```bash
uv run python scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json
```

Validated source diffs remain in `changes[]`. V5 also exposes dated official registry-change facts for currentness context. BRREG registry events do not invent a previous value when the API only supplies a new patch value, so they are not forged into `changes[]`; they remain explicit evidence-backed `official_registry_change` claims/canonical facts and can support the synthesis `what_changed` section.

## 13. Product surface

`--product-output out/signalpost.html` builds a static workspace directly from the final output. It exposes:

1. company record;
2. financials;
3. people & locations;
4. company website;
5. hiring & public activity;
6. deterministic company synthesis;
7. what changed and unknown boundaries;
8. source/evidence links.

The renderer uses the final output rather than a parallel demo dataset, and the layout has desktop/mobile regression coverage.

## 14. Current Builderr scoring boundary

The current public challenge rule is **65/100 overall on an official run**. The score consists of:

- recall and coverage: 50 points;
- precision and evidence: 30 points;
- synthesis: 12 points;
- UX: 8 points.

These score dimensions are **not separate qualification thresholds**. Builderr owns the checked collection, official matching and official score. Repository smoke tests and local audits therefore do not prove qualification.

A material wrong-company match remains more serious than an ordinary factual miss, so the production policy continues to abstain when exact-company attribution is uncertain.

## 15. Verification before submission

Run:

```bash
uv run python scripts/verify_submission_bundle.py
uv run python scripts/audit_canonical_v2.py
uv run --with pytest pytest -q
```

The verifier checks immutable V1 evidence identities, current V5 production blobs, the committed V5 smoke report, manifest integrity, certified release hashes and the preserved evidence-linked product artifact.

Relevant green qualification runs before this final audit:

- certified V1 replay: `35246833190`
- V4 certified 1,000 registry narrative audit: `36884388934`
- V4 fresh 100: `36884650475`
- V5 fresh production qualification: `36890996638`
- V5 exact-production-head replay: `36892430561`
- V5 merged-production Baseline CI: `36894134314`

The exact final audit/merge CI is recorded in the pull request that finalizes this submission metadata.

## 16. Revision submission

Use `submission/EMAIL_TEMPLATE.md` after the final pre-submission audit is merged. Replace `<FINAL_MAIN_SHA>` with the resulting exact `main` SHA and fill the contact placeholders before sending the revision to Builderr.
