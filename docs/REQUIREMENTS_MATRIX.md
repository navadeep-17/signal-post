# Signalpost V8 requirements matrix

Updated: 2026-10-06

This matrix separates repository-verifiable engineering properties from Builderr-owned scoring outcomes. `PASS` means reproduced by tests or qualification evidence. `OPEN` means only Builderr's official evaluator can decide the result.

## Current release boundary

- production code SHA: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- qualified code ref: `release/v8-qualified-2026-10-06`
- final submission ref: `release/v8-submission-2026-10-06`
- evaluator: `scripts/run_signalpost_v8.py`
- final fresh qualification: workflow `37403982422`
- artifact: `11386579108`
- Q8 engineering decision: **GO**
- official Builderr score for this revision: **OPEN**

The public qualification line is **65/100 overall**. Recall/coverage, precision/evidence, synthesis and UX are weighted score dimensions and are **not separate qualification thresholds**.

The latest official Builderr result for the previously evaluated revision is **49.99/100**; the older public-board snapshot may still show **52.41/100**. The newly qualified revision has not yet received an official Builderr score.

| Requirement | Current evidence | Status |
|---|---|---|
| Organisation number is the legal-entity anchor | exact-org BRREG resolution and source-specific exact-recipient rules | PASS |
| One terminal result per input | Q8 fresh 100 / 100 | PASS |
| Fresh generalization | 8,723 prior companies excluded; seed 20261107; overlap 0 | PASS observed |
| Original source envelope preserved | `claims[]`, `evidence[]`, `changes[]`, `errors[]`, `operations` | PASS |
| Current evaluator entry | `scripts/run_signalpost_v8.py` | PASS |
| Dynamic evaluator batch handling | V8 derives exact input count before delegation | PASS |
| Historical V2/V5 compatibility preserved | certified V1/V2/V5 artifacts and verifier unchanged | PASS |
| Evidence-linked canonical mapping | canonical facts retain source/evidence references | PASS |
| Deterministic synthesis | cannot create unsupported facts | PASS |
| Exact-company website publication | discovery candidates never substitute for identity proof | PASS |
| Explicit wrong-site-owner veto | different named site owner quarantines publication | PASS |
| Multi-entity/shared-domain protection | conflicting/multiple org evidence abstains | PASS |
| Social claim boundary | exact verified company page must declare the profile URL | PASS |
| Social identity hardening | derived social publication remains bound to exact verified entity | PASS |
| Contact-email boundary | retained first-party evidence + verified-site domain agreement | PASS |
| Careers precision | tenant/profile/listing/service text cannot become careers through ambiguous wording | PASS |
| Active-job precision | company-owned role detail + role marker + explicit apply/application action | PASS |
| Dated activity precision | specific first-party detail + explicit non-future publication date | PASS |
| Generic CMS placeholder rejection | default posts such as Hello world / Hei verden are rejected | PASS |
| Feed precision | same verified site + bounded RSS/Atom + valid non-future date | PASS |
| Final external precision guard | zero-network and idempotent | PASS |
| Official registry changes | exact-org BRREG update feed; registry semantics retained | PASS |
| Official support | Støtteregisteret primary recipient organisation number only | PASS |
| Support provenance | exact recipient proof + source-row key/hash/retrieval metadata | PASS |
| Core evidence completeness | 4,600 / 4,600 Q8 fresh | PASS observed |
| Evidence reopenability | 4,600 / 4,600 Q8 fresh | PASS observed |
| Identity proof visibility | 164 / 164 identity-sensitive claims | PASS observed |
| Extraction-method visibility | 164 / 164 identity-sensitive claims | PASS observed |
| Evidence visibility issues | 0 Q8 fresh | PASS |
| Precision-guard residuals | 0 Q8 fresh | PASS |
| Contract validation | 0 errors Q8 fresh | PASS |
| Canonical validation | 0 errors Q8 fresh | PASS |
| Synthesis validation | 0 errors Q8 fresh | PASS |
| Dangling evidence references | 0 Q8 fresh | PASS |
| Support projection integrity | 0 errors Q8 fresh | PASS |
| Refresh / idempotency | deterministic replay and projection regressions | PASS |
| Requests <=2,000 / 100 | observed 1,376; structural ceiling exactly 2,000 | PASS |
| Runtime <=45 min / 100 | 629.722 s / 2,400 s | PASS observed |
| Third-party API spend <=$10 / 100 | $0.00 | PASS |
| Search API dependency | 0 production search API requests | PASS |
| Server-side secrets | none required | PASS |
| Data-linked product | HTML workspace generated from exact final JSONL | PASS |
| Explore / Compare | same evidence-linked payload; descriptive comparison only | PASS |
| Missing values | explicit unknown/not-published; no imputation | PASS |
| Source rights documented | `docs/SUBMISSION_SOURCE_RIGHTS.md` | PASS |
| Fresh manual external audit | 20 rows / 5 companies; 0 issues | PASS observed |
| Fresh manual support audit | 42 rows / 12 companies; 0 issues | PASS observed |
| Machine-readable Q8 record | `submission/v8-qualified-2026-10-06.json` | PASS |
| Official Builderr score >=65/100 | Builderr checked evaluation | OPEN |

## Q8 fresh qualification

Attempt #4 is the successful fresh cohort after three consumed debugging cohorts.

- seed: `20261107`
- excluded companies: **8,723**
- fresh companies: **100**
- overlap: **0**
- fresh cohort SHA-256: `444304a8ac88154efceb121b61efecfa6541b16b4682f9f6bd5dc8f0b7c44b1b`
- artifact digest: `74401ccf2e1c11832bc91563ce02c8cb4ff040491542c563052049205a1b995e`
- manual wrong-company publications: **0**
- manual support anomalies: **0**

See `docs/Q8_RELEASE_QUALIFICATION.md` and `submission/v8-qualified-2026-10-06.json`.

## Historical compatibility boundary

The certified 1,000-company V1/V5 bundle and `submission/manifest.json` remain immutable historical evidence. The V8 release does not rewrite those artifacts. The top-level evaluator is V8; the older V2 filename remains part of the delegated certified compatibility lineage.

## Decision rule

Submit only an exact frozen revision. Do not weaken exact-company or evidence rules merely to inflate local coverage. After Builderr returns the official score/category breakdown, select the next engineering target from the measured official gap.
