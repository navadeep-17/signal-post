# Signalpost V2 submission guide

This is the evaluator-facing source of truth for the current revision. V2 keeps the qualified V1 collector and output adapter unchanged, then adds evidence-linked registry/canonical projections, a strict zero-network first-party activity projection, and a data-linked product surface. The original V1 submission remains immutable.

## 1. Revision identity

When submitting this revision, send Builderr the exact final `main` commit SHA from:

```bash
git rev-parse HEAD
```

Important historical identities:

- V1 pinned submission SHA: `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`
- V1 base collector behavior SHA: `b14ef3c277d8f1512064f865d4028e23dcd8bacf`
- unchanged V1 runner Git blob: `9be89b9827135b1ed703318e1d189d5d3b8ca604`
- unchanged V1 output-adapter Git blob: `c163f493017e39252ef200e68d53bcebc12930b4`
- certified V1 release harness SHA: `550bba0cce64a0a26d878c3b7f41eb20a55dc10e`
- certified replay: `35246833190`
- frozen 1,000 manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`
- certified V1 uncompressed output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`

`scripts/verify_submission_bundle.py` machine-checks the two V1 Git blobs above. V2 does not reselect or rewrite the certified V1 corpus.

## 2. Why V2 exists

Private Builderr diagnostic feedback on the first submission indicated that complete company outputs were returned, but relatively little already-collected registry/accounts information was recovered into canonical fields and no data-linked product surface was submitted. It also clarified that a generic careers page must not count as hiring.

V2 therefore prioritizes **mapping and product exposure before new crawling**:

1. preserve the original `claims[]` and `evidence[]` envelope;
2. recover additional official registry facts from the exact-org profile retained by the unchanged base collector;
3. add flat typed `canonical_facts[]` that reuse evidence IDs;
4. group facts into company record, financials, people & locations, company website, and hiring & public activity;
5. project only strict first-party job/update facts from pages already retained by the exact verified-company crawl;
6. emit a static HTML product from the exact same final JSONL;
7. keep identity thresholds, source connectors and collection request budgets unchanged.

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

The wrapper runs the unchanged final collector first. It then reads retained exact-org profiles/page snapshots from the work directory, performs V2 registry and strict first-party activity projections with **zero additional network requests**, canonicalizes the source-backed claims, validates the result, writes the V2 JSONL/report and optionally builds the HTML product. `--product-output` is V2-only and is not forwarded to the base collector.

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
- `hiring.*`

Examples include `company.industry`, `company.municipality_number`, `company.bankrupt`, `financial.revenue`, `people.role`, `locations.registered_workplace`, `website.official`, `website.contact_email`, `public.social_profile`, `hiring.job_posting`, `public.company_update` and `company.workforce_snapshot`.

Every canonical fact records its `source_field` and reuses source evidence IDs. The V2 registry/activity/canonical projections perform no network access. Inactive/departed BRREG role rows remain available in the source claim for audit/history but are excluded from current `people.role` facts.

## 6. Strict first-party hiring and public activity

`src/norway_company_agent/first_party_activity.py` operates only on pages already retained from a website whose exact-company identity assessment is publishable.

A job can be published only when all of the following hold:

- same verified company-owned site;
- job/career/stilling/vacancy-like **detail URL**, not a section root;
- specific non-generic title;
- job-detail marker;
- explicit apply/application action.

An explicit role-ID query such as `jobid` can identify a detail page; generic filter queries do not.

A company update can be published only when:

- same verified company-owned site;
- news/blog/press/aktuelt-like **detail URL**, not a section root;
- specific non-generic title;
- explicit publication date.

Generic careers pages, generic news indexes, cross-domain pages and undated updates are rejected. No platform activity, current social ownership, sentiment, follower count or generic hiring inference is created.

## 7. Canonical recovery on the immutable certified 1,000

```bash
uv run python scripts/audit_canonical_v2.py
```

This zero-network mapping audit over the committed V1 output produces:

| V2 mapping property | Result |
|---|---:|
| Companies | 1,000 |
| Unique organisation numbers | 1,000 |
| Canonical facts | 19,951 |
| Canonical validation errors | 0 |
| Company record area | 998 / 1,000 |
| Financials area | 998 / 1,000 |
| People / locations area | 999 / 1,000 |
| Verified company-website area | 107 / 1,000 |
| Hiring / public-activity area | 48 / 1,000 |
| Current individual role facts | 3,932 |
| Registered-location facts | 971 |
| Revenue facts | 792 |
| Operating-result facts | 976 |
| Workforce facts | 990 |
| Validated social-profile facts | 82 |
| First-party contact-email observations | 57 |

The 48-company hiring/public-activity area here is driven by already-certified social-profile facts; it is **not** a claim that those companies have job postings or dated updates. Live V2 runs can additionally recover official industry/municipality-number/status fields from retained exact-org profiles through `v2_registry_projection.py`.

These are engineering diagnostics, not an official Builderr score.

## 8. Fresh V2 300-company validation

A fresh engineering validation was run after implementing the canonical/product/activity revision.

Capture identity:

- workflow run: `36148292559`
- capture head: `7be47b5577c70f34a0891408c3a5cc5f0991c751`
- artifact ID: `10871337704`
- artifact digest: `sha256:f3ec8250743df3d1b09f4ec13602257702e5c40d8fdee4ee211ecf1113d2d244`
- deterministic seed: `20261003`
- selection SHA-256: `6aefc6aef2562538273f845e2734409f92fbbe3862deaed3b4e4eaa7ceadef99`

The 300 companies had zero overlap with **6,900 known internal companies**: the repository's 5,900 prior development/qualification companies plus the immutable V1 1,000. Builderr's private 700-company technical-review capture is not available to the repository, so no disjointness claim is made against that private set.

Live capture resource/result checks:

| Property | Result |
|---|---:|
| Companies completed | 300 / 300 |
| Observed conservative request charge | 4,052 |
| Structural request ceiling | 6,000 |
| Wall runtime | 1,105.442 s |
| Third-party API cost | $0.00 |
| Search API requests | 0 |
| Contract validation errors | 0 |
| Canonical validation errors | 0 |

Because final registry-isolation/detail-URL hardening was completed after the live capture began, the retained fresh capture was replayed through the final V2 projections with **zero network requests**:

- replay workflow run: `36151163094`
- replay head: `c06a9bbb192f2bb03d630dc80c21e208133fbedf`
- replay artifact ID: `10871866988`
- replay artifact digest: `sha256:ca6b46bb12524e44bcceb7d6ae8ad6d5b7701163af71f50fd1665c82b50587d8`
- replay output SHA-256: `e9542031767a97d79ab271330061c2d2e0cdaf7655a7211d37ec09725d6af63a`

Final replay result:

| V2 property | Result |
|---|---:|
| Companies | 300 |
| Canonical facts | 7,165 |
| Company record area | 299 / 300 |
| Financials area | 300 / 300 |
| People / locations area | 299 / 300 |
| Company website area | 30 / 300 |
| Hiring / public-activity area | 12 / 300 |
| Current person-role facts | 1,206 |
| Registered-location facts | 261 |
| Revenue facts | 239 |
| Operating-result facts | 296 |
| Workforce facts | 297 |
| Social-profile facts | 19 |
| Contact-email facts | 18 |
| Strict job-posting facts | **0** |
| Strict dated company-update facts | **0** |
| Contract validation errors | 0 |
| Canonical validation errors | 0 |

The strict activity audit file is empty. Therefore **V2 does not claim a jobs/news coverage improvement** from this bounded retained-page layer. Its demonstrated improvements are canonical exposure, evidence linkage and product usability while preserving conservative publication boundaries.

## 9. Certified V1 evidence baseline remains unchanged

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

## 10. Models, APIs, rights, secrets and safety

The V2 evaluator path invokes **no LLM, sentiment model, paid API, search API or social-platform scraper/API**. Server-side secrets required: **none**.

Sources remain:

1. Brønnøysundregistrene official bulk/API/account-copy services.
2. Wikidata only as a bounded exact-org-number website-candidate nominator.
3. Exact verified company-owned public pages for bounded website/contact/social/job/update evidence.

Source rights and retention boundaries are documented in `docs/SUBMISSION_SOURCE_RIGHTS.md`.

## 11. Claim boundaries

- Social-profile fact: exact verified company page declared the URL; platform ownership/activity/followers are not claimed.
- Contact email: appeared in bounded first-party evidence and matched the verified website registered domain; mailbox deliverability is not claimed.
- Generic careers/news indexes are not jobs/updates.
- Strict job: specific same-site detail page + job detail + explicit apply/application evidence.
- Strict company update: specific same-site dated article/update detail page.
- Missing website/job/review/news/activity/sentiment values are not converted to zero or inferred from absence.
- Workforce extraction abstains on missing/conflicting company-scope phrases.

## 12. Data-linked product surface

`--product-output out/signalpost-v2.html` builds a static workspace directly from the final V2 JSONL. The renderer is `scripts/build_v2_product.py` and is organized around:

1. Company record
2. Financials
3. People & locations
4. Company website
5. Hiring & public activity

The checked-in `submission/signalpost-v2.html` is deterministically rebuilt from the immutable certified corpus and regression-tested byte-for-byte. Every rendered fact links to evidence/provenance.

## 13. Refresh proof

```bash
uv run python scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json
```

Expected result: exactly two material changes, zero false positives/negatives and no additional changes on an idempotent rerun.

## 14. Verification

Before pinning V2:

```bash
uv run python scripts/verify_submission_bundle.py
uv run python scripts/audit_canonical_v2.py
uv run --with pytest pytest -q
```

The submission verifier also checks the immutable V1 base runner/output-adapter Git blobs, frozen V1 corpus, V2 entrypoints/declarations and checked-in product surface.

## 15. Remaining scoring uncertainty

Builderr owns the reference collection, matching logic, availability denominator and official score. Neither the immutable-corpus audit nor the fresh 300 diagnostic is presented as proof of an official score or qualification result.

Identity precision remains the priority: do not weaken exact-company gates merely to increase breadth.

## 16. Revision submission

Use `submission/EMAIL_TEMPLATE.md` after V2 is merged. Replace:

- `<FINAL_MAIN_SHA>` with the final merged V2 SHA;
- `<CONTACT_NAME>` with the submitter/contact name;
- `<CONTACT_EMAIL>` with the contact email;
- `<CONTACT_PHONE_OR_OTHER>` if desired.
