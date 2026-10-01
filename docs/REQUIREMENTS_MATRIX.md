# Signalpost V5 requirements matrix

Updated: 2026-10-01

This file separates directly reproduced engineering properties from Builderr-owned evaluation outcomes. **PASS** means reproduced/verified by repository tests or qualification runs; **PARTIAL** means measured evidence exists but Builderr remains authoritative; **OPEN** means the official private evaluator decides the result.

## Qualification and execution requirements

| Requirement | Current implementation/evidence | Status |
|---|---|---|
| Organisation number is the entity anchor | BRREG bulk/live and every promoted discovery/change path resolve to exact org number | PASS |
| Exactly one terminal result/company | certified 1,000: 1,000 unique/1,000 completed; fresh V4/V5 cohorts 100/100 | PASS |
| 1,000+ release profiles | immutable certified V1 release remains committed and verified | PASS |
| Generalization beyond development companies | certified release excludes 5,900 prior; V4 fresh excludes 7,220; V5 fresh excludes 7,320 | PASS observed |
| Source claims/evidence/changes/operations | original output contract preserved | PASS |
| V1 base runner unchanged | Git blob `9be89b9827135b1ed703318e1d189d5d3b8ca604` | PASS machine-verified |
| V1 output adapter unchanged | Git blob `c163f493017e39252ef200e68d53bcebc12930b4` | PASS machine-verified |
| Evaluator-friendly canonical mapping | evidence-linked `canonical_facts[]` / `canonical_profile` | PASS implementation |
| Registry/accounts exposed explicitly | exact-org registry projection + canonical financial/company fields | PASS |
| Current people safely flattened | inactive/departed BRREG appointments excluded from current `people.role` facts | PASS |
| Locations flattened | individual registered-location facts with evidence | PASS |
| Financial period/currency retained | canonical financial facts preserve source period/currency | PASS |
| Honest missing financials | unavailable/source errors never converted to zero | PASS |
| No fabricated financials | official normalized accounts path; no imputation | PASS |
| Claim-level provenance/time/hash | output/canonical facts retain evidence IDs and source metadata | PASS |
| Explicit availability states | unavailable/blocked/failed remain explicit | PASS |
| Exact-company web identity | existing wrong-company/parent/brand guards unchanged | PASS implementation; evaluator precision authoritative |
| Company descriptions | V3 annual-report descriptions + V4 exact-org BRREG activity fallback | PASS implementation/fresh transfer |
| Description fallback precedence | stronger published description wins; registry activity only fills missing description | PASS tests/audits |
| Registered purpose separated from activity | `vedtektsfestetFormaal` exposed separately, never substituted for `aktivitet` | PASS |
| Strict first-party jobs | same verified site + detail URL + specific title + job marker + apply action | PASS implementation/tests |
| Strict first-party company updates | same verified site + detail URL + title + explicit date | PASS implementation/tests |
| Generic careers/news indexes rejected | section roots/generic filters do not count | PASS |
| Cross-domain activity rejected | exact verified company-owned domain required | PASS |
| Social claim boundary | verified company page declared URL; platform not fetched | PASS |
| Contact-email boundary | retained first-party evidence + matching registered domain | PASS |
| Official registry currentness | bounded exact-org BRREG update feed with dated events | PASS implementation/fresh transfer |
| Registry-change semantics | `company.registry_change`, never company-authored news/social/hiring | PASS tests/manual audit |
| Registry-change path abstention | unknown/unstable BRREG paths are not promoted | PASS |
| Registry-change exact attribution | unexpected orgs hard-fail integrity and are never attributed | PASS |
| Change explanation | deterministic synthesis can cite dated official registry changes when no stronger refresh diff exists | PASS implementation |
| Refresh/idempotency | saved refresh replay plus idempotent registry/change projections | PASS |
| <=45 min / 100 | certified slowest chunk 458.803 s; V5 exact fresh 100 414.534 s | PASS observed |
| <=2,000 requests / 100 | V5 observed 1,382; combined structural ceiling exactly 2,000 | PASS |
| <=$10 external API spend / 100 | production policy $0; V5 fresh $0 | PASS |
| One evaluator command | `scripts/run_signalpost_v2.py` | PASS |
| Data-linked product surface | same command can render HTML from final JSONL | PASS |
| Evidence-bounded deterministic synthesis | no LLM/new facts; positive statements trace to evidence | PASS |
| Source rights documented | `docs/SUBMISSION_SOURCE_RIGHTS.md` | PASS |
| Safe URL/SSRF/redirect handling | hardened bounded site stack unchanged | PASS implementation |
| Pinned dependencies/tests | `uv.lock`; full CI; submission verifier; refresh replay | PASS |
| Models/APIs/secrets declared | no LLM/paid/search/social-platform API; no required server secret | PASS |
| Official Builderr coverage >=21/35 | private evaluator-owned | OPEN |
| Weighted external company recall >=60% | private evaluator-owned | OPEN |
| External precision >=95% | private evaluator-owned | OPEN |
| Overall Builderr score >=65/100 | private evaluator-owned | OPEN |

## Immutable certified V1 baseline

Replay `35246833190`:

- companies: 1,000 / 1,000
- unique organisations: 1,000
- terminal completed: 1,000
- claims: 17,098
- deduplicated evidence: 17,050
- contract errors: 0
- observed conservative requests: 13,628 total
- structural ceiling: 20,000 total / 2,000 per 100
- slowest chunk: 458.803 s
- third-party API cost: $0.00
- search API requests: 0
- workforce companies: 990
- verified websites: 107
- social-handle companies: 48
- contact-email companies: 53

The certified V1 corpus remains immutable release evidence. Later improvements are qualified separately rather than tuned against that frozen release set.

## V2 canonical/product diagnostic

Zero-network canonical audit over the immutable certified V1 output:

- companies: 1,000
- canonical facts: 19,951
- canonical validation errors: 0
- company record: 998 / 1,000
- financials: 998 / 1,000
- people/locations: 999 / 1,000
- verified website area: 107 / 1,000
- hiring/public-activity area: 48 / 1,000 (driven by validated social-profile facts)
- current role facts: 3,932
- registered locations: 971
- revenue facts: 792
- workforce facts: 990

This established mapping/product exposure, not an official score.

## V3 annual-report company descriptions

V3 reuses exact-org official annual-account evidence with conservative company-scope language guards. It does not interpret group-only or weak OCR text as a company description.

Qualification evidence is documented in the V3 annual-report description docs and regressions. V3 is upstream of the V4 fallback: if a stronger annual-report/company-site description is already published, V4 must not replace it.

## V4 exact-org registry narrative

Certified 1,000 offline audit (`36884388934`):

- description companies before: **85 / 1,000**
- description companies after: **998 / 1,000**
- net-new: **913**
- stronger descriptions preserved: **85 / 85**
- registered-purpose companies: **961 / 1,000**
- added network requests: **0**
- idempotence/evidence/output/canonical/synthesis errors: **0**

Fresh zero-overlap 100 (`36884650475`), seed `20261007` after excluding 7,220 prior organisations:

- terminal: **100 / 100**
- descriptions: **100 / 100**
- registry-activity fallback: **85 / 100**
- registered purpose: **97 / 100**
- canonical facts: **3,697**
- conservative request charge: **1,380 / 2,000**
- wall runtime: **422.647 s**
- third-party cost: **$0.00**
- contract/canonical/synthesis/evidence errors: **0**

This is literal exact-org BRREG source text, not an LLM-generated description.

## V5 exact-org BRREG registry changes

Source-screen run `36885512441` on the fixed 20-company comparison cohort:

- 20 / 20 had update history;
- 20 / 20 had an event in the prior 365 days;
- one exact-org batched request;
- unexpected organisations: 0.

That justified promotion into a separate production connector with a narrow registry-only semantic boundary.

Fresh exact-production-head qualification (`36892430561`) used deterministic seed `20261008` after excluding **7,320** previously touched organisations:

- companies: **100 / 100**
- overlap: **0**
- registry-change companies: **100 / 100**
- published registry-change claims: **156**
- change-feed requests: **1**
- observed conservative request charge: **1,382 / 2,000**
- theoretical conservative ceiling: **2,000 / 2,000**
- wall runtime: **414.534 s**
- third-party cost: **$0.00**
- integrity/evidence/output/canonical/synthesis errors: **0**
- qualification: **PASS**

Fresh cohort SHA-256:

`a7a18aab77f9c7192ba5e55b31e5dd225718a20b6b0f6d036fb78a2a524d412d`

Observed qualified path families included latest submitted annual accounts, registered employee count, business address, articles date, VAT registration, industry and registered capital. A retained 50-event audit found no item relabelled as company-authored public activity.

See `docs/V5_BRREG_CHANGE_PRODUCTION.md` for the complete measurement.

## Request-budget proof after V5

The base runner previously used the available structural request capacity for annual-report attempts. V5 therefore reserves the shared change-feed budget first.

For 100 companies:

- BRREG change-feed theoretical logical ceiling: 1
- conservative multiplier: 2
- reserved challenge charge: 2
- base-runner challenge maximum: 1,998
- combined theoretical challenge ceiling: **2,000**

The fresh qualification observed **1,382**, leaving substantial runtime/request margin while still proving the structural hard cap.

## Current production declaration

`scripts/run_signalpost_v2.py` is the single evaluator path. The filename is retained for backward compatibility, but the current implementation includes:

- immutable V1 foundation/collector;
- V2 registry/canonical/product/synthesis layer;
- V3 qualified annual-report description intelligence;
- V4 exact-org registry narrative fallback;
- V5 bounded exact-org BRREG registry-change source.

It invokes no LLM, paid API, search API, sentiment model or social-platform scraper. The exact merged V5 production SHA before submission-only packaging is:

`a0ca7bb1ab19de5c7c96b2e5e862763c27f8e34b`

Merged-main Baseline CI `36894134314` passed.

## Remaining decision rule

Do not claim a new official score until Builderr evaluates the final pinned revision. After finalization, submit the exact main SHA and use the next Builderr report to choose any further engineering target. Do not weaken exact-company/evidence gates merely to inflate local counts.
