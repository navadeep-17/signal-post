# Signalpost V8 requirements matrix

Updated: 2026-10-06

`PASS` means reproduced by tests or qualification evidence. `OPEN` means Builderr's official evaluator owns the result.

## Current release boundary

- production SHA: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- release ref: `release/v8-qualified-2026-10-06`
- evaluator: `scripts/run_signalpost_v8.py`
- fresh qualification workflow: `37403982422`
- fresh artifact: `11386579108`
- official Builderr score for this revision: **OPEN**

The public qualification line is 65/100 overall. Score weights are recall/coverage 50, precision/evidence 30, synthesis 12 and UX 8.

| Requirement | Current evidence | Status |
|---|---|---|
| Organisation number is the legal-entity anchor | exact-org BRREG and source-specific exact-recipient rules | PASS |
| One terminal result per input | Q8 fresh 100 / 100 | PASS |
| Fresh generalization | 8,723 touched companies excluded; seed 20261107; overlap 0 | PASS observed |
| Original source envelope preserved | claims/evidence/changes/errors/operations | PASS |
| Current evaluator command | `scripts/run_signalpost_v8.py` | PASS |
| Dynamic evaluator batch handling | V8 derives actual input count | PASS |
| Evidence-linked canonical mapping | canonical facts retain source/evidence references | PASS |
| Deterministic synthesis | cannot create unsupported facts | PASS |
| Exact-company website publication | candidates never substitute for identity proof | PASS |
| Wrong-site-owner veto | explicit different site owner quarantines publication | PASS |
| Multi-entity/shared-domain protection | conflicting/multiple org evidence abstains | PASS |
| Social claim boundary | exact verified company page must declare the profile URL | PASS |
| Social identity hardening | profile handle must remain consistent with exact company identity | PASS |
| Contact-email boundary | retained first-party evidence + verified-site domain agreement | PASS |
| Careers precision | profile/listing/service text does not become careers merely via ambiguous “job” wording | PASS |
| Active-job precision | specific company-owned role detail + apply/application evidence required | PASS |
| Dated activity precision | specific first-party update + explicit non-future publication date | PASS |
| Generic CMS placeholder rejection | default posts such as Hello world / Hei verden are rejected | PASS |
| Feed precision | same verified site + bounded RSS/Atom + non-future dated entry | PASS |
| Final precision guard | zero-network, idempotent postprojection guard | PASS |
| Official registry changes | exact-org BRREG update feed; typed as registry changes only | PASS |
| Official support | Støtteregisteret primary recipient organisation number only | PASS |
| Support provenance | exact recipient proof + source-row key/hash/retrieval metadata | PASS |
| Core evidence completeness | 4,600 / 4,600 fresh Q8 | PASS observed |
| Evidence reopenability | 4,600 / 4,600 fresh Q8 | PASS observed |
| Identity proof visibility | 164 / 164 identity-sensitive claims | PASS observed |
| Extraction method visibility | 164 / 164 identity-sensitive claims | PASS observed |
| Contract validation | 0 errors fresh Q8 | PASS |
| Canonical validation | 0 errors fresh Q8 | PASS |
| Synthesis validation | 0 errors fresh Q8 | PASS |
| Dangling evidence references | 0 fresh Q8 | PASS |
| Refresh/idempotency | baseline deterministic replay + projection idempotence tests | PASS |
| Requests <=2,000 / 100 | observed 1,376; structural theorem exactly 2,000 | PASS |
| Runtime <=45 min / 100 | 629.722 s / 2,400 s | PASS observed |
| External API spend <=$10 / 100 | $0.00 | PASS |
| Search API dependency | 0 production search API requests | PASS |
| Server-side secrets | none required | PASS |
| Data-linked product | HTML workspace generated from exact final JSONL | PASS |
| Company explorer | same evidence-linked payload | PASS |
| Side-by-side comparison | descriptive only; no winner/ranking | PASS |
| Missing values | explicit unknown / not published; no imputation | PASS |
| Source rights documented | `docs/SUBMISSION_SOURCE_RIGHTS.md` | PASS |
| Frozen release record | `submission/v8-qualified-2026-10-06.json` | PASS |
| Fresh manual external audit | 20 rows / 5 companies; 0 issues | PASS observed |
| Fresh manual support audit | 42 rows / 12 companies; 0 issues | PASS observed |
| Official Builderr score >=65/100 | Builderr-owned checked evaluation | OPEN |

## Fresh Q8 record

Attempt #4 is the qualifying fresh cohort after three consumed debugging cohorts.

- seed: `20261107`
- excluded companies: 8,723
- cohort SHA-256: `444304a8ac88154efceb121b61efecfa6541b16b4682f9f6bd5dc8f0b7c44b1b`
- artifact digest: `74401ccf2e1c11832bc91563ce02c8cb4ff040491542c563052049205a1b995e`
- precision guard residuals: 0
- manual wrong-company publications: 0

See `Q8_FRESH_QUALIFICATION_2026-10-06.md` for details.

## Historical compatibility

The certified 1,000-company V1/V5 bundle and `submission/manifest.json` remain immutable historical compatibility evidence. They are intentionally not rewritten to pretend they are the current fresh qualification.

The older V2/V5/V7 qualification sections in repository history remain useful audit evidence, but this matrix's current release boundary is V8 at the SHA above.

## Decision rule

Submit the exact frozen release ref/SHA. Do not weaken exact-company or evidence gates to inflate coverage. After Builderr returns the new official score and category breakdown, select the next engineering target from the measured official gap.
