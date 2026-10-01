# Signalpost V5 requirements matrix

Updated: 2026-10-01

This document separates **repository-verifiable engineering properties** from **Builderr-owned scoring outcomes**. `PASS` means reproduced by tests or qualification runs. `OPEN` means only Builderr's official evaluation can decide the result.

## Current qualification boundary

The current public rule is **65/100 overall**. The four score dimensions are weighted components — recall/coverage 50, precision/evidence 30, synthesis 12, UX 8 — and are **not separate qualification thresholds**.

| Requirement | Evidence | Status |
|---|---|---|
| Organisation number is the identity anchor | exact-org BRREG resolution across promoted paths | PASS |
| One terminal result per input | certified 1,000 = 1,000/1,000; current V5 smoke = 100/100 | PASS |
| Current 100-company smoke report committed | `submission/v5-smoke-100-run-report.json` | PASS |
| Generalization beyond development cohorts | V5 fresh cohort excludes 7,320 prior organisations; overlap 0 | PASS observed |
| Original source envelope preserved | `claims[]`, `evidence[]`, `changes[]`, `errors[]`, `operations` | PASS |
| V1 base runner unchanged | Git blob `9be89b9827135b1ed703318e1d189d5d3b8ca604` | PASS machine-verified |
| V1 output adapter unchanged | Git blob `c163f493017e39252ef200e68d53bcebc12930b4` | PASS machine-verified |
| V5 production wrapper pinned | Git blob `07cdd0f5f1edb6c425ac8b8c9ae90e6357c87643` | PASS machine-verified |
| V5 BRREG-change connector pinned | Git blob `9d22bcaf494a356a47985fc731cef6c2e0ecd493` | PASS machine-verified |
| Evidence-linked canonical mapping | `canonical_facts[]` / `canonical_profile` | PASS |
| Deterministic evidence-linked synthesis | no new factual claims created by synthesis | PASS |
| Financial period/currency retained | canonical financial facts preserve source period/currency | PASS |
| Missing financials remain explicit | unavailable/source errors are not converted to zero | PASS |
| Current people safely flattened | inactive/departed appointments excluded from current `people.role` facts | PASS |
| Registered locations flattened | individual location facts preserve evidence | PASS |
| Company descriptions | V3 annual-report extraction + V4 exact-org BRREG activity fallback | PASS |
| Stronger description precedence | registry activity only fills a missing description | PASS |
| Registered purpose kept distinct | `vedtektsfestetFormaal` is not silently rewritten as activity | PASS |
| Exact-company website publication | candidate discovery never replaces exact-company proof | PASS implementation |
| Strict job publication | verified site + detail URL + specific title + job marker + apply action | PASS |
| Strict company-update publication | verified site + detail URL + specific title + explicit date | PASS |
| Generic careers/news indexes rejected | section roots do not become facts | PASS |
| Social claim boundary | company page declared URL; platform itself is not fetched | PASS |
| Contact-email boundary | retained first-party evidence + verified-site domain agreement | PASS |
| Official registry currentness | bounded exact-org BRREG update feed | PASS |
| Registry-change semantics | `company.registry_change`, never company-authored news/social/hiring | PASS |
| Unknown registry paths abstain | conservative stable-path allowlist | PASS |
| Unexpected returned organisations fail integrity | exact target attribution enforced | PASS |
| Refresh/idempotency | deterministic replay + idempotent projections | PASS |
| Runtime <=45 min / 100 | V5 smoke 414.534 s / 2,400 s | PASS observed |
| Requests <=2,000 / 100 | V5 observed 1,382; structural ceiling exactly 2,000 | PASS |
| External API spend <=$10 / 100 | production policy and smoke result are $0.00 | PASS |
| One evaluator command | `scripts/run_signalpost_v2.py` | PASS |
| Data-linked product | `--product-output` renders from the final JSONL | PASS |
| Source rights documented | `docs/SUBMISSION_SOURCE_RIGHTS.md` | PASS |
| Safe URL/redirect handling | hardened bounded web stack retained | PASS implementation |
| Dependencies pinned | `uv.lock` | PASS |
| Models/APIs/secrets declared | no LLM/paid/search/social-platform API; no server secret | PASS |
| Scoring weights documented | 50 / 30 / 12 / 8 | PASS documentation |
| Official Builderr score >=65/100 | Builderr checked collection/evaluator owned | OPEN |

## Current V5 smoke test

Exact-production-head workflow: `36892430561`.

- companies: **100 / 100** terminal;
- prior organisations excluded: **7,320**;
- overlap: **0**;
- canonical facts: **3,795**;
- company descriptions: **100 / 100**;
- workforce: **98 / 100**;
- verified company-site profiles: **7 / 100**;
- companies with social-profile observations: **2 / 100**;
- companies with contact-email observations: **4 / 100**;
- registry-change companies: **100 / 100**;
- published registry-change claims: **156**;
- contract/canonical/synthesis/registry-integrity errors: **0**;
- observed conservative request charge: **1,382 / 2,000**;
- theoretical conservative ceiling: **2,000 / 2,000**;
- wall runtime: **414.534 s**;
- third-party API cost: **$0.00**;
- search API requests: **0**.

Fresh selection SHA-256:

`a7a18aab77f9c7192ba5e55b31e5dd225718a20b6b0f6d036fb78a2a524d412d`

A concise machine-readable copy is committed at `submission/v5-smoke-100-run-report.json`.

## Immutable certified V1 baseline

Replay `35246833190` remains historical release evidence:

- companies: **1,000 / 1,000**;
- unique organisations: **1,000**;
- terminal completed: **1,000**;
- claims: **17,098**;
- deduplicated evidence: **17,050**;
- contract errors: **0**;
- observed conservative requests: **13,628** total;
- structural ceiling: **20,000 total / 2,000 per 100**;
- slowest chunk: **458.803 s**;
- third-party API cost: **$0.00**;
- search API requests: **0**.

The historical V1 corpus is immutable. Later layers are qualified separately instead of rewriting that baseline.

## Preserved V2 canonical/product compatibility

The zero-network projection over the immutable certified V1 output contains:

- **19,951 canonical facts**;
- **0 canonical validation errors**;
- **3,932 current individual role facts**;
- 971 registered locations;
- 792 revenue facts;
- 990 workforce facts;
- 82 validated social-profile facts;
- 57 first-party contact-email observations.

The historical fresh V2 diagnostic yielded zero strict job-posting facts and zero strict dated company-update facts. Those zeroes mean no retained page met the publication gate; they are not negative claims about the companies.

## V3 and V4 description qualification

V3 reuses exact-org annual-account evidence with conservative company-scope language guards. V4 adds literal exact-org BRREG `aktivitet` only as a fallback.

Certified 1,000 V4 audit (`36884388934`):

- descriptions before: **85 / 1,000**;
- descriptions after: **998 / 1,000**;
- net-new: **913**;
- stronger descriptions preserved: **85 / 85**;
- added network requests: **0**;
- output/canonical/synthesis/evidence errors: **0**.

Fresh V4 100 (`36884650475`):

- terminal: **100 / 100**;
- descriptions: **100 / 100**;
- request charge: **1,380 / 2,000**;
- runtime: **422.647 s**;
- third-party API cost: **$0.00**;
- hard-check failures: **0**.

## V5 registry-change qualification

The promoted connector uses the official Enhetsregister update feed with exact organisation numbers, one bounded batch for 100 companies, a 365-day lookback, a stable-path allowlist, and at most three newest qualified events per company.

The change-feed request budget is reserved before base execution. For 100 companies:

- change-feed logical ceiling: 1;
- conservative multiplier: 2;
- reserved challenge charge: 2;
- base-runner maximum: 1,998;
- combined theoretical ceiling: **2,000**.

Registry-change facts remain `company.registry_change`. They do not become company-authored public activity and they never invent an earlier value that BRREG did not supply.

## Current production declaration

`scripts/run_signalpost_v2.py` is the single evaluator path. Its filename is retained for backward compatibility. Current production combines:

- the immutable V1 exact-entity collection foundation;
- V2 canonical projection, deterministic synthesis and product rendering;
- V3 annual-report company descriptions;
- V4 exact-org registry-activity fallback;
- V5 bounded exact-org BRREG registry changes.

Merged V5 production SHA before final documentation/audit packaging:

`a0ca7bb1ab19de5c7c96b2e5e862763c27f8e34b`

The verifier pins the current production wrapper and BRREG-change connector by Git blob so final presentation/documentation changes cannot silently alter evaluator behavior.

## Decision rule

Do not claim qualification until Builderr evaluates the final pinned revision. Submit the exact final `main` SHA and use the next official category breakdown to choose any subsequent engineering target. Do not weaken exact-company or evidence gates merely to inflate local counts.
