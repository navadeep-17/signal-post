# Signalpost V2 requirements matrix

Updated: 2026-09-25

This file separates directly reproduced properties from Builderr-owned evaluation outcomes. The certified V1 1,000-company corpus remains immutable; V2 changes mapping/product exposure and adds zero-network strict first-party activity projection rather than reselecting that evidence baseline.

Status meanings: **PASS** = directly reproduced/verified; **PARTIAL** = strong measured evidence but not proof of Builderr's evaluator result; **OPEN** = evaluator-owned.

## Qualification and execution requirements

| Requirement | V2 implementation/evidence | Status |
|---|---|---|
| Organisation number is the entity anchor | BRREG bulk/live and every promoted discovery path resolve to exact org number | PASS |
| 1,000+ completed profiles | immutable certified V1 release has 1,000 / 1,000 terminal completed | PASS |
| Generalization beyond development companies | certified release excludes 5,900 prior companies and has zero overlap | PASS observed |
| Exactly one terminal result/company | 1,000 unique orgs / 1,000 terminal V1 outputs | PASS |
| Source claims/evidence/changes/operations | base collector emits and validates `OUTPUT_CONTRACT.md` envelope | PASS |
| Evaluator-friendly canonical mapping | V2 adds evidence-linked `canonical_facts[]` and `canonical_profile` | PASS implementation |
| Registry/accounts mapped into explicit fields | 19,951 canonical facts over immutable certified 1,000; 0 mapping errors | PASS implementation |
| Current people flattened safely | 3,932 current `people.role` facts; inactive/departed appointments excluded from current canonical facts | PASS implementation |
| Locations flattened | 971 individual `locations.registered_workplace` facts in V2 audit | PASS implementation |
| Financial period/currency retained | V2 canonical financial facts preserve source claim period/currency | PASS |
| Claim-level provenance/time/hash | canonical facts reuse original evidence IDs; source envelope remains authoritative | PASS |
| Explicit availability states | unavailable values remain unavailable and are never converted to zero | PASS |
| No fabricated financials | deterministic BRREG financial path; V2 only projects existing claims | PASS |
| External identity precision | exact-company website/handle/contact guards unchanged from V1 | PARTIAL; Builderr authoritative |
| External/overall coverage | V2 exposes more existing facts but Builderr owns reference matching | OPEN |
| Idempotent refresh/history | saved replay detects exactly two expected changes and none on rerun | PASS |
| <=45-minute wall time / 100 | V1 collector slowest certified chunk 458.803 s; V2 projections are local | PASS baseline + negligible projection |
| <=2,000 outbound requests / 100 | V2 canonical/activity/product projections add zero network requests; V1 structural ceiling remains 2,000 | PASS |
| <=$10 external API spend / 100 | policy remains $0 | PASS |
| One evaluator command | `scripts/run_signalpost_v2.py` documented in `SUBMISSION.md` | PASS |
| Data-linked product surface | same V2 command emits a five-area evidence-linked HTML product from final JSONL | PASS implementation |
| Generic careers page not treated as hiring | job fact requires verified same-site page + specific title + job detail + explicit apply/application action | PASS implementation/tests |
| Generic/undated news not treated as activity | company-update fact requires verified same-site specific article/update + explicit date | PASS implementation/tests |
| Cross-domain activity rejected | strict first-party projector requires the retained page to remain on the exact verified company-owned site | PASS implementation/tests |
| Social claim boundary | social fact means verified company page declared URL; platform itself not fetched | PASS |
| Source rights documented | `docs/SUBMISSION_SOURCE_RIGHTS.md` + `submission/manifest.json` | PASS |
| Safe URL/SSRF/redirect handling | hardened V1 site stack remains base collector | PASS |
| Pinned dependencies/tests | `uv.lock`; full CI + canonical audit + product regression + refresh replay | PASS |
| Models/APIs/secrets declared | no LLM/paid/search/social scraper; no server-side secrets | PASS |

## V2 mapping diagnostic

Reproducible command:

```bash
uv run python scripts/audit_canonical_v2.py
```

Measured over the immutable certified V1 1,000-company output:

- companies: 1,000
- unique organisation numbers: 1,000
- canonical facts: **19,951**
- canonical validation errors: 0
- company record area: 998 / 1,000
- financials area: 998 / 1,000
- people / locations area: 999 / 1,000
- verified company-website area: 107 / 1,000
- hiring / public-activity area: 48 / 1,000 (validated company-declared social profiles; not job inference)
- current individual role facts: **3,932**
- registered-location facts: 971
- revenue facts: 792
- operating-result facts: 976
- workforce facts: 990
- social-profile facts: 82
- contact-email observations: 57

This diagnostic demonstrates mapping exposure only. It is **not** an official Builderr score and does not prove hidden/reference-set recall.

## Strict first-party activity boundary

`src/norway_company_agent/first_party_activity.py` is a zero-network projection over already retained pages from an exact verified company website.

It does not broaden website discovery or fetch job/social/news platforms. A generic careers page, generic news index, cross-domain page, missing apply action or undated update produces no job/update fact. This directly preserves the Builderr feedback boundary that a generic careers page must not count as hiring.

Any measured job/update yield from a fresh cohort is reported separately as a validation diagnostic and is not treated as an official Builderr score.

## Immutable V1 evidence identity

- V1 pinned submission SHA: `60c5b0852f41ddd7d5ef51b2c68b4d7fe0f1e4aa`
- base collector behavior SHA: `b14ef3c277d8f1512064f865d4028e23dcd8bacf`
- certified replay: `35246833190`
- final companies: 1,000
- overlap with prior cohorts: 0
- frozen manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`
- aggregate output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`
- aggregate artifact digest: `sha256:8cdaad00c48f1d0af811fb947c97f258fdeb26d8336767f8c8e2db7d7f15e37e`
- observed conservative requests: 13,628 total / 1,362.8 average per 100
- structural ceiling: 2,000 per 100
- third-party API cost: $0.00

## V2 production declaration

`scripts/run_signalpost_v2.py` invokes the existing final collector, then performs zero-network strict first-party activity and canonical projections and an optional data-linked product build. It does not change V1 identity thresholds, request policy, source connectors or the certified corpus.

The V2 evaluator path uses official BRREG sources, bounded Wikidata candidate nomination and independently verified company-owned public pages. It invokes no LLM, paid API, search API, sentiment model or social-platform scraper.

## Remaining action

1. complete and inspect the fresh zero-overlap V2 validation;
2. remove the temporary validation workflow after preserving its report/artifact identity;
3. finish V2 submission verifier/manifest packaging;
4. verify the final diff contains only intended canonical/product/submission changes;
5. run the full test suite, canonical 1,000 audit, repository verifier and refresh replay;
6. merge only from a green exact head SHA;
7. send Builderr the new pinned V2 commit as a revision while preserving V1 history.

Do not claim an official Builderr score before Builderr evaluates the pinned revision.
