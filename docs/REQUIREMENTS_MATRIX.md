# Signalpost V2 requirements matrix

Updated: 2026-09-25

This file separates directly reproduced properties from Builderr-owned evaluation outcomes. The certified V1 1,000-company corpus remains immutable; V2 changes evaluator-facing mapping/product exposure through zero-network projections rather than reselecting that evidence baseline.

Status meanings: **PASS** = directly reproduced/verified; **PARTIAL** = measured evidence but Builderr remains authoritative; **OPEN** = evaluator-owned.

## Qualification and execution requirements

| Requirement | V2 implementation/evidence | Status |
|---|---|---|
| Organisation number is the entity anchor | BRREG bulk/live and every promoted discovery path resolve to exact org number | PASS |
| 1,000+ completed profiles | immutable certified V1 release has 1,000 / 1,000 terminal completed | PASS |
| Generalization beyond development companies | certified V1 release excludes 5,900 prior companies; fresh V2 diagnostic excludes 6,900 known internal companies | PASS observed |
| Exactly one terminal result/company | 1,000 unique orgs / 1,000 terminal certified V1 outputs; fresh V2 300 / 300 | PASS |
| Source claims/evidence/changes/operations | unchanged V1 collector emits and validates `OUTPUT_CONTRACT.md` envelope | PASS |
| V1 base runner unchanged | Git blob `9be89b9827135b1ed703318e1d189d5d3b8ca604` | PASS machine-verified |
| V1 output adapter unchanged | Git blob `c163f493017e39252ef200e68d53bcebc12930b4` | PASS machine-verified |
| Evaluator-friendly canonical mapping | V2 adds evidence-linked `canonical_facts[]` and `canonical_profile` | PASS implementation |
| Registry/accounts mapped into explicit fields | immutable audit 19,951 facts; live V2 additionally projects retained exact-org registry fields | PASS implementation |
| Current people flattened safely | 3,932 current `people.role` facts; inactive/departed appointments excluded | PASS implementation |
| Locations flattened | 971 individual registered-location facts on immutable audit | PASS implementation |
| Financial period/currency retained | canonical financial facts preserve source period/currency | PASS |
| Claim-level provenance/time/hash | canonical facts preserve source fields/evidence IDs | PASS |
| Explicit availability states | unavailable values never converted to zero | PASS |
| No fabricated financials | deterministic BRREG financial path; V2 only projects retained facts | PASS |
| External identity precision | exact-company website/handle/contact guards unchanged from V1 | PARTIAL; Builderr authoritative |
| External/overall coverage | V2 exposes more existing facts but Builderr owns reference matching | OPEN |
| Idempotent refresh/history | saved replay detects exactly two expected changes and none on rerun | PASS |
| <=45-minute wall time / 100 | certified V1 slowest chunk 458.803 s; fresh V2 300 took 1,105.442 s | PASS observed |
| <=2,000 outbound requests / 100 | fresh V2 used 4,052 conservative requests for 300 vs 6,000 ceiling; V2 projections add zero network | PASS |
| <=$10 external API spend / 100 | $0 policy; fresh V2 $0 | PASS |
| One evaluator command | `scripts/run_signalpost_v2.py` documented in `SUBMISSION.md` | PASS |
| Data-linked product surface | same V2 command emits five-area evidence-linked HTML from final JSONL | PASS implementation |
| Generic careers page not treated as hiring | requires same-site role detail URL + specific title + job detail + explicit apply action | PASS implementation/tests |
| Generic news index not treated as activity | requires same-site article/update detail URL + specific title + explicit date | PASS implementation/tests |
| Cross-domain activity rejected | strict projector requires exact verified company-owned site | PASS implementation/tests |
| Fresh strict jobs/news yield measured honestly | final 300 replay produced 0 job postings and 0 company updates | PASS diagnostic; no coverage gain claimed |
| Social claim boundary | social fact means verified company page declared URL; platform itself not fetched | PASS |
| Source rights documented | `docs/SUBMISSION_SOURCE_RIGHTS.md` + `submission/manifest.json` | PASS |
| Safe URL/SSRF/redirect handling | hardened V1 site stack remains unchanged base collector | PASS |
| Pinned dependencies/tests | `uv.lock`; full CI + canonical audit + product regression + refresh replay | PASS |
| Models/APIs/secrets declared | no LLM/paid/search/social scraper; no server-side secrets | PASS |

## Immutable-corpus V2 mapping diagnostic

Reproducible command:

```bash
uv run python scripts/audit_canonical_v2.py
```

Measured over the immutable certified V1 1,000-company output:

- companies: 1,000
- unique organisation numbers: 1,000
- canonical facts: **19,951**
- canonical validation errors: 0
- company record: 998 / 1,000
- financials: 998 / 1,000
- people / locations: 999 / 1,000
- verified company website: 107 / 1,000
- hiring / public activity: 48 / 1,000, driven by validated company-declared social profiles, not jobs
- current individual role facts: **3,932**
- registered locations: 971
- revenue: 792
- operating result: 976
- workforce: 990
- social profiles: 82
- contact emails: 57

This demonstrates mapping exposure only. It is **not** an official Builderr score.

## Fresh V2 300-company diagnostic

Capture workflow `36148292559` selected 300 companies with deterministic seed `20261003` after excluding 6,900 known internal companies. Proven overlap within that known-internal scope: 0. Builderr's private 700-company capture is unknown, so no disjointness claim is made against it.

Live capture:

- 300 / 300 terminal
- 4,052 observed conservative requests vs 6,000 structural ceiling
- 1,105.442 seconds wall time
- $0 third-party API cost
- 0 search API requests
- 0 contract errors
- 0 canonical errors

The retained capture was replayed through the final V2 projections with **zero additional network requests** in workflow `36151163094`. Final replay:

- 7,165 canonical facts
- company record: 299 / 300
- financials: 300 / 300
- people / locations: 299 / 300
- company website: 30 / 300
- hiring / public activity: 12 / 300, driven by social-profile facts
- strict job postings: **0**
- strict dated company updates: **0**
- contract errors: 0
- canonical errors: 0
- replay output SHA-256: `e9542031767a97d79ab271330061c2d2e0cdaf7655a7211d37ec09725d6af63a`

The activity audit was empty, so V2 does **not** claim a job/news coverage improvement from this bounded retained-page layer.

## Strict first-party activity boundary

`src/norway_company_agent/first_party_activity.py` performs zero-network projection over already retained pages from an exact verified company website. Generic section roots, generic filter queries, cross-domain pages, missing apply actions and undated updates produce no job/update fact.

## Immutable V1 evidence identity

- V1 pinned submission SHA: `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`
- base collector behavior SHA: `b14ef3c277d8f1512064f865d4028e23dcd8bacf`
- certified replay: `35246833190`
- final companies: 1,000
- frozen manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`
- aggregate output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`
- aggregate artifact digest: `sha256:8cdaad00c48f1d0af811fb947c97f258fdeb26d8336767f8c8e2db7d7f15e37e`
- observed conservative requests: 13,628 total / 1,362.8 average per 100
- structural ceiling: 2,000 per 100
- third-party API cost: $0.00

## V2 production declaration

`scripts/run_signalpost_v2.py` invokes the unchanged final collector, then performs zero-network V2 registry, strict first-party activity and canonical projections plus optional data-linked product rendering. It does not change V1 identity thresholds, request policy, source connectors, base runner/output adapter or certified corpus.

The evaluator path uses official BRREG sources, bounded Wikidata candidate nomination and independently verified company-owned public pages. It invokes no LLM, paid API, search API, sentiment model or social-platform scraper.

## Remaining release actions

1. finish final submission-doc/email/verifier packaging;
2. verify the V1→V2 diff contains no collector/output-adapter drift or temporary workflows;
3. run full exact-head CI, canonical audit, repository verifier, product regression and refresh replay;
4. merge PR #33 only from that green exact head SHA;
5. submit the new pinned V2 commit as a revision while preserving V1 history.

Do not claim an official Builderr score before Builderr evaluates the pinned revision.
