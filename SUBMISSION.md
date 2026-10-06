# Signalpost V8 qualified revision guide

Updated: 2026-10-06

This document distinguishes the revision currently submitted to Builderr from the newer repository revision that has now passed Signalpost's fresh release qualification. Builderr remains authoritative for the official evaluator result and score.

## 1. Release status

Current Builderr-submitted revision remains:

- submitted commit: `e7cbbcdd505596dbd5d819b5e8647602760a7aa3`
- frozen ref: `release/v8-final-2026-10-03`

New qualified release:

- production code qualified by Q8: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- qualified code ref: `release/v8-qualified-2026-10-06`
- qualified-code Baseline CI: `37403437730` — **PASS**
- final submission ref: `release/v8-submission-2026-10-06`
- evaluator entry point: `scripts/run_signalpost_v8.py`
- Q8 decision: **GO / RELEASE-QUALIFIED**

`release/v8-submission-2026-10-06` is the exact documentation-complete revision to submit after the final documentation-only PR and exact-SHA/post-merge Baseline CI are green. Its difference from the qualified code SHA is documentation/release metadata only. The exact final SHA and CI runs are recorded by the GitHub ref/checks and final release PR so this document does not create a self-referential SHA by embedding the commit that contains itself.

The Q8 qualification harness on PR #124 is intentionally closed without merge. Do not submit or merge its qualification-only head.

## 2. Evaluator command

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

Do not hard-code `--expected-count`. V8 validates the supplied organisation file and derives the evaluator batch size.

## 3. Clean-machine setup

Requirements:

- Python 3.12+
- `uv`
- Poppler
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

If OCR tooling is unavailable, OCR-dependent extraction abstains rather than fabricating facts.

## 4. Current production behavior

The qualified production path includes:

- exact BRREG legal-entity resolution by organisation number
- official registry, accounting, roles, people, locations and group context
- bounded exact-company website discovery and strict identity verification
- company-site contact email and company-declared social/profile evidence
- workforce evidence from registry and qualified annual reports
- conservative business descriptions from qualified official evidence
- exact-org BRREG registry-change history
- official Støtteregisteret support-award evidence using primary-recipient identity only
- conservative first-party careers/job and dated-activity extraction with fail-closed precision guards
- canonical fact projection, deterministic synthesis and evaluator workspace generation
- evidence/provenance visibility suitable for manual reopening

Production requires no model API, paid search API or social-platform scraper.

## 5. Identity and publication boundary

- organisation number is the legal-entity anchor
- discovery candidates never prove identity by themselves
- conflicting organisation numbers or explicit different site owners are hard negatives
- parent/group/subsidiary/franchise relation alone never authorizes inheritance
- missing, blocked or ambiguous evidence means abstention
- careers surface != active vacancy
- support-award evidence remains official support evidence and is never relabelled as company-authored news
- external publication remains subject to the final zero-network precision guard

## 6. Fresh Q8 qualification

Attempt #4 used a genuinely untouched 100-company cohort after excluding 8,723 previously touched companies.

Freshness:

- seed: `20261107`
- fresh companies: 100
- overlap: 0
- cohort SHA-256: `444304a8ac88154efceb121b61efecfa6541b16b4682f9f6bd5dc8f0b7c44b1b`

Execution:

- workflow: `37403982422` — **SUCCESS**
- qualification head: `93d3501fe5216f70f246c9ac97905bf2a1b14a4a`
- exact-head Baseline CI: `37403985583` — **PASS**
- artifact ID: `11386579108`
- artifact ZIP SHA-256: `74401ccf2e1c11832bc91563ce02c8cb4ff040491542c563052049205a1b995e`

Machine gate:

- 100/100 terminal outputs
- 4,600/4,600 core evidence complete
- 4,600/4,600 reopenable sources
- 164/164 identity-sensitive claims expose identity proof
- 164/164 expose extraction method
- 0 evidence-visibility issues
- 42 support claims across 12 companies
- 1,376/2,000 observed conservative request charge
- 629.722 s wall runtime
- $0 third-party API cost
- 0 contract/canonical/synthesis/dangling-evidence/support-projection errors

Manual gate:

- 20/20 evaluator-visible external publications reviewed
- 42/42 Støtteregisteret rows reviewed
- wrong-company publications: 0
- support audit anomalies: 0

See `docs/Q8_RELEASE_QUALIFICATION.md` for the frozen detailed record.

## 7. Release discipline

Release finalization is documentation/release-metadata only. The qualified production code remains frozen at `200f056a5a60cad23610a3958b6bec62dfb624a5`, and `release/v8-qualified-2026-10-06` must not move.

The final submission ref is `release/v8-submission-2026-10-06`; submit exactly the SHA it resolves to after the final post-merge Baseline CI passes. The only remaining external action is to submit that frozen revision to Builderr, then record the actual submitted SHA/ref and official result.

Do not consume another fresh cohort merely for bookkeeping. Any production-code change after the qualified candidate requires a new qualification decision.

## 8. Output contract and verification

Each terminal object preserves the existing claims/evidence/canonical/synthesis contract.

Repository verification:

```bash
uv run --with pytest pytest -q
uv run python scripts/audit_canonical_v2.py
uv run python scripts/verify_submission_bundle.py
```

The frozen V1 submission verifier remains immutable.

## 9. Preserved compatibility and publication boundaries

The current V8 evaluator continues to delegate through the certified compatibility path, including `scripts/run_signalpost_v2.py`. The immutable certified 1,000-company projection still contains **19,951** canonical facts with zero canonical validation errors, including **3,932** current individual role facts.

Historical strict-activity diagnostics remain preserved as compatibility evidence:

| Historical V2 diagnostic | Result |
|---|---:|
| Strict job-posting facts | **0** |
| Strict dated company-update facts | **0** |

Those historical zeroes are abstentions from the certified baseline, not claims that current companies have no jobs or updates. Current production may publish newer first-party activity only when its stricter evidence rules pass.

A strict job posting requires the same verified company-owned site, a role/job **detail URL**, a specific title, a job-detail marker, and an **explicit apply/application action**.

A strict dated company update requires the same verified company-owned site, a specific article/update **detail URL**, a non-generic title, and an **explicit publication date**.

A **generic careers** page remains a careers signal rather than proof of an active vacancy. A company-declared social profile means only that the verified company page declared that URL; Signalpost does not infer a current **follower** count from it. A retained contact email does not establish **mailbox deliverability**.

The evaluator workspace preserves descriptive **Compare companies** behavior without ranking companies.

Server-side secrets required: **none**.

The latest official Builderr result received by email on **2026-10-05** is **49.99/100** (Recall 8.99/50, Precision and evidence 21.00/30, Synthesis 12.00/12, UX 8.00/8). The public board snapshot reviewed on 2026-10-03 still lists Navadeep at **52.41/100**, so the board is behind the newer evaluator result. The challenge qualification threshold is **65/100 overall on an official run**. Recall/coverage, precision/evidence, synthesis and UX are score dimensions; they are **not separate qualification thresholds**. The newly qualified repository revision has not yet received an official Builderr score.

## 10. References

- `README.md`
- `docs/Q8_RELEASE_QUALIFICATION.md`
- `docs/CONTINUATION_STATE.md`
- `submission/V8_EVALUATOR_PATH.md`
- `OUTPUT_CONTRACT.md`
- `docs/REQUIREMENTS_MATRIX.md`
- `docs/SUBMISSION_SOURCE_RIGHTS.md`
- `submission/v8-qualified-2026-10-06.json` — current machine-readable Q8 qualification record
- `submission/manifest.json` — historical certified V5/V2 lineage manifest

The 49.99/100 evaluator result above is the latest official score communicated by Builderr until the newly qualified revision is explicitly submitted and evaluated.
