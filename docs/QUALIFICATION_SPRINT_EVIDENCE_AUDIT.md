# Qualification Sprint Evidence Audit

Last updated: 2026-10-05

## Purpose

Measure what an evaluator can actually see in the final Signalpost contract before spending new requests or consuming another fresh Phase-11 cohort.

This audit is intentionally zero-network. It inspects only final `claims[]` and `evidence[]` output and therefore distinguishes:

- proof that is already visible to an evaluator;
- proof retained internally but dropped before final projection;
- genuinely missing evidence.

## Audited artifact

Consumed-only Phase-11 owner-veto replay:

- workflow run: `37314396820`
- artifact: `phase11-owner-veto-consumed-replay`
- artifact ID: `11347753450`
- artifact ZIP SHA-256: `ff03b78a41372f368ace904a009e82eda5c42fd5aa3d74d37a91ccaee0684e01`
- companies: 100
- this cohort was already consumed and is **not** fresh qualification evidence

The replay was chosen because it exercised the actual V8 path after the PR #99 owner-veto fix while avoiding any new cohort consumption.

## Final-contract evidence result

Across the 100-company replay output:

- available claims: **4,611**
- core-evidence-complete claims: **4,611 / 4,611 (100%)**
- claims with reopenable HTTP(S) source URLs: **4,611 / 4,611 (100%)**
- claims with a visible date/effective/reporting field: **2,241**
- identity-sensitive claims: **169**
- identity-sensitive claims with evaluator-visible identity proof: **0 / 169**
- identity-sensitive claims with evaluator-visible extraction method: **0 / 169**

The 169 identity-sensitive claims are:

| Field | Claims | Identity proof visible | Extraction method visible |
|---|---:|---:|---:|
| `external.workforce_snapshot` | 99 | 0 | 0 |
| `official.support_award` | 48 | 0 | 0 |
| `official_website` | 6 | 0 | 0 |
| `external.contact_email` | 6 | 0 | 0 |
| `external.profile_handle` | 5 | 0 | 0 |
| `social_links` | 4 | 0 | 0 |
| company-owned `company_description` | 1 | 0 | 0 |

There were **zero** missing URL/date/hash/span core-evidence defects in these published claims. The gap is specifically provenance visibility.

## Internal-retention cross-check

The retained `work/profiles.jsonl` contains 123 external observations:

- workforce snapshots: 99
- company-profile/contact observations: 19
- social profile-handle observations: 5

All **123 / 123** retained observations contain non-empty `identity_proof`.

Those observations also retain a deterministic collector/extractor `strategy`, including examples such as:

- `official_registry_employee_count_v1`
- `annual_report_workforce_snapshot_brreg_ocr_exact_org_v5`
- `verified_company_page_same_domain_email_v1`
- `verified_company_homepage_declaration_c12_v1`

Verified website records separately retain `value.identity_assessment`, including exact-company status, score, reasons and deterministic identity method.

Therefore the principal Q1 finding is:

> Signalpost already retains materially stronger provenance internally than the final evaluator-facing evidence exposes.

## Q2 implementation decision

**PROMOTE provenance projection.**

Q2 adds a deterministic, zero-network projection layer that copies already-retained provenance into the exact final evidence row that backs the claim:

- observation `identity_proof` -> final evidence `identity_proof`;
- observation `strategy` -> final evidence `extraction_method`;
- verified website `identity_assessment` -> website-backed final evidence `identity_proof`;
- website identity-assessment `method` -> final evidence `extraction_method`.

Join rules are deliberately strict:

1. observation-backed claims join only by exact `observation_id`;
2. website-backed claims join only when both source URL and content SHA-256 match the retained verified website;
3. existing visible provenance is never overwritten;
4. no claim value, confidence, availability, identity threshold, evidence ID, source URL, hash or request accounting changes;
5. no network access is added.

## Fresh-cohort policy

Do **not** consume seed `20261105` or another untouched cohort for this change yet.

First require:

1. focused provenance regressions;
2. exact-head Baseline CI;
3. consumed/dev replay proving the final visible-provenance counts increase monotonically without claim-set changes;
4. only then continue to the next qualification milestone.
