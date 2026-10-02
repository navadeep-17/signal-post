# V6c Candidate Ranking — Controlled Experiment Decision

## Decision

**NO-GO for production. Keep V5 unchanged. Reject the ML challenger and do not promote the deterministic challenger.**

The user-defined primary metric for V6c is **correct verified websites discovered per charged network request**. On the untouched V6c development cohort, both candidate rankers produced **zero net-new verified websites**, so neither strategy improves production recall under the strict exact-company publication gate.

This decision does **not** treat ranking scores as evidence. The existing exact-company identity gate remained authoritative for every publication decision.

## Experimental design

Pipeline:

`shared bounded candidate generation -> ranker -> top 1–2 probes -> existing exact-company identity gate`

Challengers:

- `website.candidate_rank.rules.v1`
- `website.candidate_rank.ml.v1`

Both consumed the same candidate generator. Candidate generation was bounded to zero-cost already-known facts such as registry/verified email domains, normalized legal-name forms, safe acronym forms, municipality variants, and `.no` / `.com` variants. No search API, external inference API, paid connector, or LLM was used.

The ML challenger was a small fully local logistic-regression model trained only from historical website attempts that had already been independently resolved by the existing identity gate. The fresh V6c cohort was not used for training or tuning.

## Frozen cohort integrity

- Cohort size: **50**
- Historical exclusions before selection: **7,470**
- Overlap with exclusions: **0**
- Cohort SHA-256: `fd2b58949746eac3acd0f3238ace494ef98c2bdfa9edeaf3c3d0c7079e4f8bc7`
- Evaluation split: `v6c_candidate_ranking_development`
- Sample slice: `unseen_rules_vs_ml`

The rejected prior V6 deterministic-domain development cohort was included in the exclusion set before V6c selection.

## Historical ML training set

- Independently resolved examples: **80**
- Training examples: **70**
- Holdout examples: **10**
- Positive labels: **18**
- Negative labels: **62**
- Fresh V6c data used for training/tuning: **false**

The offline holdout binary accuracy was 0.90, but that is explicitly **not** the promotion metric and the ranking holdout contained only one group with a positive example. It is therefore not evidence that ML improves production website discovery.

## Same-cohort production-style comparison

| Metric | Frozen V5 incumbent | Rules challenger | ML challenger |
|---|---:|---:|---:|
| Verified websites before challenger | 3 | 3 | 3 |
| Net-new verified websites | — | **0** | **0** |
| Top-1 verified hits | — | 0 | 0 |
| Top-2 verified hits | — | 0 | 0 |
| Network probe attempts | — | 92 | 92 |
| Added logical HTTP requests | — | 34 | 50 |
| Added conservative request charge | — | 68 | 100 |
| Combined conservative request charge | 666 | 734 | 766 |
| Wall runtime, seconds | — | 49.962 | 52.054 |
| Contact emails unlocked | — | 0 | 0 |
| Social profiles unlocked | — | 0 | 0 |
| Strict jobs unlocked | — | 0 | 0 |
| Strict company updates unlocked | — | 0 | 0 |
| Published identity conflicts | — | 0 | 0 |
| Third-party API cost | $0 | $0 | $0 |
| Verified websites / added conservative charge | — | **0.0** | **0.0** |

The different logical-request counts arise from actual bounded fetch outcomes after ranking; both rankers still attempted at most the same top-2 policy over the same generated candidate sets. Candidate ranking itself never created or upgraded evidence.

## Interpretation

1. **ML did not materially outperform deterministic ranking.** Both yielded zero verified websites, while ML consumed more charged requests and slightly more runtime.
2. **Deterministic ranking also failed the production promotion gate.** Lower request cost is not enough when verified-site gain is zero.
3. **V5 remains the production strategy.** No website identity rule or publication threshold should be weakened to rescue V6c candidates.
4. **Do not tune on this V6c cohort.** It is now historical experiment evidence and must be excluded from any future website-discovery validation cohort.

## Promotion status

- `website.candidate_rank.ml.v1`: **REJECTED**
- `website.candidate_rank.rules.v1`: **REJECTED FOR PRODUCTION**
- Existing V5 website discovery / exact-company gate: **RETAINED**

V6c code and artifacts are kept only as experiment evidence. They should not be merged into `main` as a production feature.
