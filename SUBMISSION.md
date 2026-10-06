# Signalpost — current Builderr revision guide

Updated: 2026-10-06

This is the evaluator-facing guide for the next Signalpost revision. Builderr remains authoritative for the official company batch, run limits, checked collection and score.

## 1. Version to evaluate

Repository:

`https://github.com/navadeep-17/signal-post`

Qualified evaluator semantics:

- production main under fresh qualification: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- evaluator entrypoint: `scripts/run_signalpost_v8.py`
- Q8 fresh qualification: **GO**
- qualification report: `docs/Q8_FRESH_RELEASE_QUALIFICATION.md`
- machine-readable release record: `submission/current-qualified-revision.json`

The final submission email must name the exact repository commit Builderr should clone. Q9 release-documentation commits may advance repository HEAD, but the evaluator blobs must remain byte-identical to the Q8-qualified blobs recorded in `submission/current-qualified-revision.json`.

## 2. One-command evaluator path

After dependencies and the BRREG bulk file are available:

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

Do not hard-code `--expected-count` in the normal evaluator command. V8 reads Builderr's supplied organisation file and derives the exact batch size.

## 3. Clean-machine setup

Requirements:

- Python 3.12+
- `uv`
- Poppler / `pdftoppm`
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

OCR-dependent enrichment abstains when OCR tooling or qualified evidence is unavailable.

## 4. Current production behavior

For every supplied Norwegian organisation number Signalpost:

1. resolves the exact legal entity from Brønnøysundregistrene;
2. collects registry, accounting, roles, locations and group evidence;
3. verifies company websites through bounded candidate generation plus exact-company identity gates;
4. extracts company-declared social profiles and same-domain contact email only from a verified company site;
5. extracts workforce/company-scope intelligence from qualified annual-account evidence when available;
6. records bounded official BRREG registry changes;
7. projects recent exact-recipient Brønnøysundregistrene Støtteregisteret awards as typed official support facts;
8. can use a spare verified-site request slot for bounded same-site RSS/Atom activity, with current-date and placeholder guards;
9. applies a final zero-network external precision guard before canonical/synthesis output;
10. exposes evaluator-visible URL, retrieval time, content hash, supporting span, identity proof and extraction method for identity-sensitive evidence;
11. projects canonical facts and deterministic evidence-linked synthesis;
12. builds the static evaluator workspace from the exact final JSONL.

Signalpost abstains when company attribution, date semantics or source evidence is insufficient.

## 5. Exact-company precision boundary

Non-negotiable rules:

- organisation number is the legal-entity anchor;
- candidate generation is never publication proof;
- parent/group/subsidiary/franchise relation alone cannot authorize inheritance;
- an explicit different site owner is a hard negative unless exact target proof overrides it;
- multi-entity/shared pages are quarantined when exact ownership is unclear;
- social URLs are published only when declared by an exact verified company page and the handle passes the identity guard;
- generic service/profile/listing pages cannot become careers or company activity;
- future publication dates are rejected;
- generic CMS placeholder posts are rejected;
- missing or ambiguous evidence remains missing/ambiguous rather than becoming zero or a guessed fact.

A careers surface does not establish an active vacancy. Official support awards remain official support awards and are never relabelled as company-authored news.

## 6. Fresh 100-company smoke / qualification evidence

Q8 attempt 4 used an untouched 100-company cohort after excluding **8,723** previously touched companies.

- selection seed: `20261107`
- overlap: **0**
- workflow: `37403982422`
- artifact: `11386579108`
- artifact digest: `sha256:74401ccf2e1c11832bc91563ce02c8cb4ff040491542c563052049205a1b995e`
- terminal outputs: **100 / 100**
- available claims: **4,600**
- core evidence complete: **4,600 / 4,600**
- reopenable sources: **4,600 / 4,600**
- identity proof visible: **164 / 164**
- extraction method visible: **164 / 164**
- evidence issues: **0**
- support claims: **42 across 12 companies**
- contract/canonical/synthesis/support projection errors: **0**
- observed conservative request charge: **1,376 / 2,000**
- theoretical conservative request ceiling: **2,000 / 2,000**
- wall runtime: **629.722 s**
- third-party API cost: **$0.00**
- search API requests: **0**

The independent manual audit reviewed all 20 evaluator-visible external publications and all 42 support rows and found **0 known wrong-company publications** and **0 support anomalies**.

This is engineering smoke/qualification evidence. Builderr's official run determines the competition score.

## 7. Models, APIs, licences and cost

Production evaluator:

- LLM/model APIs: **none**
- paid search APIs: **none**
- social-platform APIs/scrapers: **none**
- required server-side secrets: **none**
- declared third-party API cost: **$0.00 per 100-company qualified run**

Primary source classes:

- Brønnøysundregistrene open data / official APIs — NLOD 2.0 where applicable;
- Brønnøysundregistrene Støtteregisteret — official exact-recipient public data;
- Brønnøysundregistrene annual-account copies — bounded filing evidence, not redistributed;
- Wikidata structured data — CC0, candidate nomination only;
- verified company-owned public pages — bounded factual extraction with source provenance; no blanket page-content redistribution is assumed.

See `docs/SUBMISSION_SOURCE_RIGHTS.md`.

## 8. Output

One terminal output object is returned for every input organisation, including companies where evidence is missing or blocked.

Each object preserves:

- `organisation_number`
- `run`
- `claims[]`
- `evidence[]`
- `changes[]`
- `errors[]`
- `operations`
- `canonical_facts[]`
- `canonical_profile`
- `synthesis`

See `OUTPUT_CONTRACT.md`.

## 9. Evaluator-facing UX

The generated workspace includes:

- global company search;
- evidence-backed profiles;
- evidence-linked decision briefs;
- source/date/reporting context;
- recent official changes;
- evidence drawer and verify-all flow;
- descriptive company comparison;
- deterministic grounded Ask Signalpost answers;
- explicit unknown/data-gap handling;
- responsive/mobile and keyboard-accessible interactions.

Comparison is descriptive only; Signalpost does not infer a winner or company ranking.

## 10. Historical certified artifacts

`submission/manifest.json` and `submission/final-release-1000-*` preserve the earlier certified V5/V2 1,000-company compatibility lineage.

They are intentionally retained and immutable, but they are **not** the current scoring input and should not be presented as the Q8 smoke run. Builderr supplies the official company batch at evaluation time.

## 11. Verification

```bash
uv run --with pytest pytest -q
uv run python scripts/audit_canonical_v2.py
uv run python scripts/verify_submission_bundle.py
```

Baseline CI also checks the frozen historical bundle and deterministic refresh behavior. The current-release manifest has regression coverage that pins the qualified evaluator blobs and Q8 metrics.

## 12. Current Builderr contract snapshot

Checked 2026-10-06:

- qualification: **65 / 100** on an official run;
- weights: **50 recall/coverage, 30 precision/evidence, 12 synthesis, 8 UX**;
- submit a **100-company smoke-test result/run report**, repository, exact commit and one run command;
- declare models/APIs/licences, expected cost and contact details;
- Builderr supplies the official company batch; precomputed profiles are not used for ranking.

If Builderr's challenge page changes, its current published rules override this repository summary.

## 13. Submission checklist

Before emailing the revision:

- [ ] Q9 exact-head Baseline CI is green.
- [ ] Q9 merge/post-merge CI is green.
- [ ] Exact final repository commit SHA is copied into the email.
- [ ] Evaluator blobs still match `submission/current-qualified-revision.json`.
- [ ] Q8 workflow/artifact IDs and digest are unchanged.
- [ ] No secrets or credentials are committed.
- [ ] Contact placeholders in `submission/EMAIL_TEMPLATE.md` are filled.
- [ ] The revision is submitted only if it is within Builderr's allowed revision count/cutoff.

Builderr remains authoritative for official scoring, revision eligibility and evaluator resource limits.
