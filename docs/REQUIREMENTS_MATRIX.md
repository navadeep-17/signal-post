# Signalpost final requirements matrix

Updated: 2026-09-17

This file separates directly verified submission properties from Builderr's hidden-evaluator requirements. The live Builderr Signalpost challenge is authoritative for scoring, qualification and resource limits. Historical local/proxy scorers are diagnostic only and are not converted into an official score.

Status meanings: **PASS** = directly reproduced/verified for the final submission path; **PARTIAL** = strong measured evidence but not proof of the hidden requirement; **OPEN** = evaluator-owned result.

## Qualification and execution requirements

| Requirement | Final implementation/evidence | Status |
|---|---|---|
| Organisation number is the entity anchor | BRREG bulk/live and every promoted discovery path resolve back to exact org number | PASS |
| Frozen eligible universe | deterministic selector uses Builderr's 411,160-company universe | PASS |
| At least 1,000 completed profiles | certified final release has 1,000 / 1,000 terminal completed | PASS |
| Generalize beyond development companies | final release excludes 5,900 prior companies and has zero overlap | PASS observed |
| Exactly one terminal result/company | certified 1,000 has 1,000 unique orgs and 1,000 terminal outputs | PASS |
| Claims/evidence/changes/operations envelope | final runner emits and validates `OUTPUT_CONTRACT.md` objects | PASS |
| Claim-level provenance/time/hash/period | official, website and workforce claims preserve provenance metadata | PASS |
| Distinct missing/blocked/not-applicable states | contract preserves explicit availability states | PASS |
| No fabricated financials | deterministic BRREG financial path; unavailable values remain unavailable | PASS |
| External precision >=95% | strict exact-entity gates, wrong-company regressions and manual promotion audits provide strong evidence | PARTIAL; hidden evaluator authoritative |
| Weighted external company recall >=60% | 990/1000 workforce plus narrower website/contact/social families on certified replay | OPEN; hidden denominator authoritative |
| Coverage >=21/35 | field availability/external union scored by Builderr | OPEN |
| Overall >=65/100 | Builderr hidden judge | OPEN |
| Idempotent refresh/history | saved refresh replay detects two expected changes and zero extra changes on rerun | PASS |
| <=45-minute wall time / 100 | all ten final chunks passed; slowest was 458.803 s | PASS |
| <=2,000 outbound requests / 100 | structural conservative ceiling is exactly 2,000; observed max final chunk was 1,404 | PASS |
| <=$10 external API spend / 100 | stricter final policy is $0 third-party API spend | PASS |
| One evaluator command | `scripts/run_signalpost_final.py` documented in `SUBMISSION.md` | PASS |
| Source rights documented | `docs/SUBMISSION_SOURCE_RIGHTS.md` + machine-readable submission manifest | PASS |
| Safe URL/SSRF/redirect handling | hardened site stack remains in production | PASS |
| Pinned dependencies and tests | `uv.lock`; Baseline CI and submission regressions | PASS |
| Snapshot drift safe | release included two companies absent from current BRREG bulk and still completed 1,000/1,000 | PASS |
| Candidate discovery independently verified | H1 candidate paths nominate only; exact company page proof is required for publication | PASS |
| UI exposes evidence/gaps/changes | F4 static workspace builds directly from final output-contract claims/evidence | PASS implementation; official UX score hidden |
| Research answers are evidence-bounded | F4 deterministic brief uses only published claims and labels unknowns explicitly | PASS implementation; official synthesis score hidden |
| Models/APIs/licences/caches/hosting declared | `submission/manifest.json` and `docs/SUBMISSION_SOURCE_RIGHTS.md` | PASS |

## Certified final release identity

- Production application behavior SHA: `b14ef3c277d8f1512064f865d4028e23dcd8bacf`
- Certified release harness SHA: `550bba0cce64a0a26d878c3b7f41eb20a55dc10e`
- Certified GitHub Actions replay: `35246833190`
- Release seed: `20261002`
- Prior exclusions: 5,900
- Final companies: 1,000
- Overlap with prior cohorts: 0
- Frozen manifest SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`
- Aggregate output SHA-256: `00750f7d66f16937703f417af493dad38d895cdf0e36020be9c28399e6d6d0f2`
- Aggregate artifact digest: `sha256:8cdaad00c48f1d0af811fb947c97f258fdeb26d8336767f8c8e2db7d7f15e37e`

## Certified final release metrics

- terminal completed: 1,000 / 1,000
- claims: 17,098
- deduplicated evidence records: 17,050
- canonical contract-validation errors: 0
- runner contract errors: 0
- change errors: 0
- observed conservative request charge: 13,628 total / 1,362.8 average per 100
- structural request ceiling: 20,000 total / 2,000 per 100
- slowest 100-company chunk: 458.803 seconds
- third-party API cost: $0.00
- search API requests: 0
- workforce: 990 / 1,000
- verified websites: 107 / 1,000
- companies with declared social handles: 48 / 1,000
- companies with qualifying contact email: 53 / 1,000

Full evidence: `docs/FINAL_RELEASE_1000_AUDIT.md`.

## Final production declaration

The production runner uses official BRREG sources, bounded Wikidata candidate discovery and independently verified company-owned public pages. It invokes no LLM, paid API, search API, sentiment model or social-platform scraper. Social-handle claims represent URLs declared by verified company pages; contact-email claims are bounded same-domain first-party evidence; neither expands into unsupported platform/mailbox assertions.

## Remaining action

No further tuning should be performed against the frozen release corpus. Submission preparation consists only of:

1. merge the F5 documentation/verifier bundle after CI;
2. record the resulting exact `main` commit SHA externally in the Builderr submission email;
3. send the repository URL, exact SHA, evaluator command, model/API declaration and expected $0 third-party API cost per 100-company run.

The submission must not claim Builderr's hidden recall, coverage or overall score before the evaluator reports them.
