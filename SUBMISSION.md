# Signalpost V8 submission guide

Updated: 2026-10-03

This document describes the evaluator-facing Signalpost release currently submitted to Builderr. Builderr remains authoritative for the checked company collection, infrastructure limits and official score. Repository metrics below are engineering qualification evidence only.

## 1. Submitted revision

Official submitted evaluator revision:

- repository: `navadeep-17/signal-post`;
- submitted commit: `e7cbbcdd505596dbd5d819b5e8647602760a7aa3`;
- frozen release ref: `release/v8-final-2026-10-03`;
- evaluator entry point: `scripts/run_signalpost_v8.py`.

The default branch may receive documentation-only repository-hygiene commits after this release. Those do not change the evaluator SHA already supplied to Builderr unless a new revision is explicitly submitted.

## 2. Release lineage

Signalpost intentionally preserves its certified evidence-collection lineage:

- V1 pinned submission SHA: `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`;
- V1 runner Git blob: `9be89b9827135b1ed703318e1d189d5d3b8ca604`;
- V1 output-adapter Git blob: `c163f493017e39252ef200e68d53bcebc12930b4`;
- certified V5 machine-readable lineage: `submission/manifest.json`;
- certified V5/V2 data wrapper: `scripts/run_signalpost_v2.py`;
- V7 evaluator/product path: `scripts/run_signalpost_v7.py`;
- V8 compatibility wrapper: `scripts/run_signalpost_v8.py`.

V8 does not introduce a new collector, source, identity heuristic, publication rule, model or UI behavior. It derives the actual evaluator batch size from the supplied organisation file, validates it, applies internal safety ceilings, and delegates once through V7 to the already-qualified V5/V2 path.

## 3. Evaluator command

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

Do **not** hard-code `--expected-count` in the normal evaluator command.

V8 reads and validates the supplied organisation file, derives the exact company count, and passes that count through V7 → V2 → the pinned base runner and final workspace builder. If an explicit expected count is supplied and does not match the input file, V8 fails before research begins.

See `submission/V8_EVALUATOR_PATH.md` for the wrapper contract.

## 4. Clean-machine setup

Requirements:

- Python 3.12+;
- `uv`;
- Poppler (`pdftoppm`);
- Tesseract OCR.

Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
uv sync --locked

curl --fail --location --retry 3 --retry-delay 2 \
  'https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv' \
  --output brreg-enheter.csv
```

If OCR tooling is unavailable, OCR-dependent extraction abstains instead of fabricating a value.

## 5. What the production evaluator does

For each supplied Norwegian organisation number, Signalpost:

1. resolves the exact legal entity from Brønnøysundregistrene;
2. gathers official registry, accounting, role, group and location evidence;
3. resolves a company website only through bounded candidates and exact-entity verification;
4. projects conservative first-party contact email and company-declared social-profile facts;
5. extracts workforce evidence from the registry or qualified annual-account copies;
6. extracts conservative company-scope description evidence from qualified annual reports or exact-org registry activity text;
7. fetches bounded exact-org BRREG update history and publishes only qualified registry changes;
8. projects source-backed claims into canonical facts;
9. builds deterministic evidence-linked synthesis and decision briefs;
10. builds the evaluator-facing static HTML workspace from the exact final JSONL.

A registry change is never relabelled as company-authored news. A company-owned careers page remains a `hiring.careers_page` signal and does not establish an active vacancy unless a separately qualified `hiring.job_posting` fact exists.

## 6. Identity and evidence boundary

Signalpost's publication rules are intentionally conservative:

- organisation number is the legal-entity anchor;
- discovery candidates never prove identity by themselves;
- conflicting explicit organisation numbers are rejected;
- parent companies, namesakes and directories cannot be substituted for the target company;
- published facts keep source evidence and provenance;
- missing, blocked and ambiguous states remain explicit;
- deterministic synthesis cannot create facts that are absent from canonical evidence.

## 7. Qualified release-path evidence

The underlying V7 production path was exercised end to end on a reproducible 100-company release cohort at qualified head `80a0ff2e75fa31db4c5c3a195d245b5c04593dbe`.

Successful release-qualification run: `37107505656`.

Measured result:

| Property | Result |
|---|---:|
| Input companies | 100 |
| Terminal outputs | 100 / 100 |
| Unique organisation numbers | 100 |
| Canonical validation errors | 0 |
| Synthesis validation errors | 0 |
| Companies with decision brief | 100 / 100 |
| Observed conservative request charge | 1,364 / 2,000 |
| Wall runtime | 311.985 s |
| Third-party API cost | $0.00 |
| Search API requests | 0 |
| Generated workspace bytes | 3,377,839 |

The successful qualification artifact is `v7-release-qualification-100` (artifact ID `11268806967`).

The V8 wrapper then added arbitrary evaluator-batch handling without changing the qualified evidence/product behavior. V8 regression coverage includes 1, 17, 100, 250, 1,000, 1,200 and 1,350-company input sizes.

These are engineering qualification results, not a claimed Builderr score.

## 8. Production dependencies and cost

Production V8:

- requires no API key or secret;
- uses no LLM API;
- uses no paid search API;
- uses no social-platform API/scraper;
- declares $0.00 third-party API cost for the qualified release path.

Server-side secrets required: **none**.

Any post-V8 model/search experimentation is isolated from the submitted evaluator and is not part of this release unless a later revision is separately qualified and submitted.

## 9. Output contract

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

Canonical facts remain linked to their original source fields and evidence IDs.

See `OUTPUT_CONTRACT.md` for the complete contract.

## 10. Evaluator-facing workspace

The generated workspace includes:

- global company search;
- evidence-backed company profiles;
- evidence-linked decision briefs;
- source/date context;
- recent official changes;
- evidence drawer and verify-all flow;
- **Compare companies** descriptive side-by-side view;
- deterministic grounded Ask Signalpost answers;
- explicit unknown/data-gap handling;
- careers-surface discovery with conservative vacancy semantics;
- responsive and keyboard-accessible interactions.

Comparison is descriptive only. Signalpost does not rank companies or select a winner.

## 11. Preserved compatibility and publication boundaries

The V2 canonical/product layer remains part of the certified lineage beneath V8. The immutable certified 1,000-company projection contains **19,951 canonical facts** with zero canonical validation errors, including **3,932 current individual role facts**.

Historical strict-activity diagnostics intentionally preserve the following result:

| V2 diagnostic | Result |
|---|---:|
| Strict job-posting facts | **0** |
| Strict dated company-update facts | **0** |

Those zeroes are abstentions, not claims that the companies had no jobs or updates.

A strict job posting requires the same verified company-owned site, a role/job **detail URL**, a specific title, a job-detail marker, and an **explicit apply/application action**.

A strict company update requires the same verified company-owned site, a specific article/update **detail URL**, a non-generic title, and an **explicit publication date**.

A **generic careers** page or section index is not an active-job fact. A company-declared social profile means only that the exact verified company page declared that URL; it does not imply that Signalpost fetched the platform or observed a current **follower** count. A retained contact email does not establish **mailbox deliverability**.

The current public challenge qualification line is **65/100 overall on an official run**. Recall/coverage, precision/evidence, synthesis and UX are score dimensions; they are **not separate qualification thresholds**. Builderr owns the official matching and score.

## 12. Verification

Repository baseline:

```bash
uv run --with pytest pytest -q
uv run python scripts/audit_canonical_v2.py
uv run python scripts/verify_submission_bundle.py
```

Baseline CI additionally runs deterministic refresh replay and refresh-output verification.

The frozen V1 bundle verifier must remain unchanged and continue to reject drift in the pinned V1 runner/output-adapter blobs.

## 13. Important repository references

- `README.md` — concise project overview and quick start;
- `submission/V8_EVALUATOR_PATH.md` — current evaluator-wrapper contract;
- `submission/V7_EVALUATOR_PATH.md` — qualified underlying evaluator/product path;
- `submission/manifest.json` — certified V5 machine-readable lineage;
- `OUTPUT_CONTRACT.md` — output/evidence contract;
- `docs/REQUIREMENTS_MATRIX.md` — challenge requirement coverage;
- `docs/SUBMISSION_SOURCE_RIGHTS.md` — source rights/acquisition policy;
- `docs/FINAL_RELEASE_1000_AUDIT.md` — certified large-batch baseline audit.

Builderr remains authoritative for the official scoring result and evaluation environment.
