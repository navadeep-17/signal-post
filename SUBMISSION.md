# Signalpost V8 submission guide

Updated: 2026-10-06

This document describes the **next Builderr revision candidate** after the completed Q8 fresh qualification. Builderr remains authoritative for the checked company collection, infrastructure limits and official score. Repository metrics below are engineering qualification evidence only.

## 1. Exact revision to submit

Use exactly:

- repository: `navadeep-17/signal-post`;
- production commit: `200f056a5a60cad23610a3958b6bec62dfb624a5`;
- frozen release ref: `release/v8-qualified-2026-10-06`;
- evaluator entry point: `scripts/run_signalpost_v8.py`.

Do **not** submit the Q8 qualification branch SHA. The qualification branch contained only test/harness files and was intentionally not merged into production.

The earlier October 3 release `release/v8-final-2026-10-03` is historical and is superseded for the next revision by the qualified release above.

## 2. Evaluator command

```bash
uv run python scripts/run_signalpost_v8.py \
  --organisations evaluator-companies.jsonl \
  --bulk brreg-enheter.csv \
  --output out/final-output.jsonl \
  --report out/final-report.json \
  --product-output out/signalpost.html \
  --work-dir out/final-work \
  --run-id builderr-eval-v8 \
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

Do not hard-code `--expected-count` in the normal evaluator command. V8 derives the exact input size and forwards it through the qualified path.

## 3. Clean-machine setup

Requirements:

- Python 3.12+
- `uv`
- Poppler (`pdftoppm`)
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

OCR-dependent extraction abstains if OCR tooling is unavailable.

## 4. Production behavior

For each supplied Norwegian organisation number, Signalpost:

1. resolves the exact legal entity from Brønnøysundregistrene;
2. gathers registry, accounting, role, group and location evidence;
3. gathers bounded official registry-change history;
4. gathers recent official support awards from Støtteregisteret using the **primary recipient organisation number only**;
5. resolves a website through bounded candidates and exact-entity verification;
6. publishes first-party contact/social facts only from an exact verified company site;
7. gathers registry/annual-report workforce and conservative company descriptions;
8. may publish strict first-party jobs or dated company activity only when page-local publication rules pass;
9. applies final zero-network precision guards before canonical projection;
10. builds canonical facts, deterministic evidence-linked synthesis and the static evaluator workspace.

Candidate generation never proves identity. Parent/group/subsidiary relationship alone never authorizes publication. Ambiguous identity abstains.

## 5. Evidence contract

Every available claim remains linked to evaluator-visible evidence containing the required provenance boundary, including source URL, retrieval time, supporting span and content hash where applicable.

Identity-sensitive external/official-support claims additionally expose exact-company identity proof and an extraction method.

The Q8 fresh qualification verified:

- 4,600 / 4,600 available claims with complete core evidence;
- 4,600 / 4,600 with reopenable sources;
- 164 / 164 identity-sensitive claims with visible identity proof;
- 164 / 164 with visible extraction method;
- zero evidence visibility issues.

## 6. Fresh qualification

Final fresh qualification record:

- workflow run: `37403982422`;
- qualification head: `93d3501fe5216f70f246c9ac97905bf2a1b14a4a`;
- production SHA under qualification: `200f056a5a60cad23610a3958b6bec62dfb624a5`;
- seed: `20261107`;
- prior touched exclusion: 8,723 companies;
- fresh cohort: 100 companies;
- overlap: 0;
- artifact ID: `11386579108`;
- artifact digest: `sha256:74401ccf2e1c11832bc91563ce02c8cb4ff040491542c563052049205a1b995e`.

Measured machine result:

| Property | Result |
|---|---:|
| Terminal outputs | 100 / 100 |
| Available claims | 4,600 |
| Core evidence complete | 4,600 / 4,600 |
| Reopenable sources | 4,600 / 4,600 |
| Identity proof visible | 164 / 164 |
| Extraction method visible | 164 / 164 |
| Precision-guard residuals | 0 |
| Contract errors | 0 |
| Canonical errors | 0 |
| Synthesis errors | 0 |
| Dangling evidence refs | 0 |
| Support projection errors | 0 |
| Observed conservative request charge | 1,376 / 2,000 |
| Theoretical conservative ceiling | 2,000 |
| Wall runtime | 629.722 s |
| Third-party API cost | $0.00 |
| Search API requests | 0 |

Manual audit also passed:

- 20 external publication rows across 5 companies; no wrong-company publication found;
- 42 official support rows across 12 companies; exact recipient org/name matches and 42 unique source-row keys;
- all frozen deliverable hashes reverified successfully.

See `docs/Q8_FRESH_QUALIFICATION_2026-10-06.md` and `submission/v8-qualified-2026-10-06.json`.

## 7. Request and cost boundary

For 100 companies, the production structural theorem remains exactly **2,000 conservative challenge-request charge**.

The fresh qualified run observed **1,376 / 2,000**.

Production requires:

- no LLM API;
- no paid search API;
- no social-platform scraper/API;
- no server-side secret;
- $0.00 third-party API cost in the qualified path.

## 8. Output model

Each terminal company object preserves:

- `organisation_number`;
- `run`;
- `claims[]`;
- `evidence[]`;
- `changes[]`;
- `errors[]`;
- `operations`;
- `canonical_facts[]`;
- `canonical_profile`;
- `synthesis`.

Canonical facts reference source fields and evidence IDs rather than replacing provenance.

## 9. Evaluator-facing workspace

The generated workspace includes:

- global company search;
- evidence-backed company profiles;
- decision briefs;
- source/date context;
- recent changes;
- evidence drawer / verification;
- descriptive side-by-side company comparison;
- deterministic grounded Ask Signalpost;
- explicit unknown/data-gap handling;
- responsive and keyboard-accessible interactions.

Signalpost does not rank companies or invent a winner.


## 10. Preserved compatibility baseline

The current top-level evaluator is V8, but the certified compatibility lineage remains explicit beneath it:

- V8 delegates through `scripts/run_signalpost_v7.py`;
- the certified data/evidence wrapper remains `scripts/run_signalpost_v2.py`;
- the historical V2 canonical projection contains **19,951** canonical facts with zero canonical validation errors;
- the same compatibility corpus contains **3,932** current individual role facts.

Historical strict-activity diagnostics are deliberately preserved:

| Compatibility diagnostic | Result |
|---|---:|
| Strict job-posting facts | **0** |
| Strict dated company-update facts | **0** |

Those zeroes are abstentions, not claims that the companies had no jobs or updates.

A strict job posting requires the same verified company-owned site, a role/job **detail URL**, a specific title, a job-detail marker, and an **explicit apply/application action**.

A strict dated company update requires the same verified company-owned site, a specific article/update **detail URL**, a non-generic title, and an **explicit publication date**.

A **generic careers** page or section index is not an active-job fact. A company-declared social profile means only that the exact verified company page declared that URL; no platform **follower** count is inferred or fetched. A retained contact email does not establish **mailbox deliverability**.

Server-side secrets required: **none**.

The four Builderr score dimensions are weighted components of the **65/100** overall qualification rule; they are **not separate qualification thresholds**.

## 11. Publication boundaries

- a careers page is not an active vacancy;
- a generic news/blog index is not a dated activity fact;
- tenant/profile/listing pages are not careers/news evidence;
- future publication dates are rejected;
- default CMS placeholder posts are rejected;
- a company-declared social URL means only that the exact verified company page declared it;
- a contact email must be present in retained first-party evidence and satisfy the verified-site domain rule;
- official support remains typed official support and is never relabelled as company-authored activity.

## 12. Verification

Repository baseline:

```bash
uv run --with pytest pytest -q
uv run python scripts/audit_canonical_v2.py
uv run python scripts/verify_submission_bundle.py
```

The immutable V1/V5 historical release artifacts remain preserved for compatibility and auditability. They are not the current fresh qualification record.

## 13. Builderr status

The repository release is **ready for the next Builderr revision submission**.

No new official score is claimed in this repository. Builderr's next official evaluation decides whether the revision crosses the 65/100 qualification line and provides the category breakdown for any subsequent optimization.
