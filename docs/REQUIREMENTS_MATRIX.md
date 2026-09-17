# Signalpost requirements matrix

Updated: 2026-09-17

This file separates official requirements, measured production status and hidden-evaluator dependencies. The live Builderr Signalpost challenge remains authoritative for scoring, qualification and resource limits. The starter's local competition scorer is diagnostic only.

Status meanings: **PASS** = directly reproduced/verified; **PARTIAL** = strong measured evidence but not full proof of the official hidden requirement; **OPEN** = hidden-evaluator dependent; **GAP** = known shortfall.

## Qualification and execution requirements

| Requirement | Current implementation/evidence | Status | Next action |
|---|---|---|---|
| Organisation number is the entity anchor | BRREG bulk/live and every promoted discovery path resolve back to exact org number | PASS | Preserve invariant |
| Frozen eligible universe | deterministic selector uses Builderr's 411,160-company universe | PASS | Freeze new final manifest/digest |
| At least 1,000 completed profiles | prior release audit completed 1,000; a new post-H2g final corpus is still required because production changed materially | PARTIAL for current production SHA | Run new disjoint 1,000 release corpus |
| Generalize beyond development companies | many zero-overlap cohorts plus H2g fresh-300 transfer | PASS observed | Do not tune on future final heldout subset |
| Exactly one terminal result/company | maintained across frozen 100, larger release runs, H2g 300 and default 100 smoke | PASS | Keep contract gate |
| Claims/evidence/changes/operations envelope | final runner emits validated output contract | PASS | Preserve |
| Claim-level provenance/time/hash/period | validated for official, website and workforce claims | PASS | Preserve |
| Distinct missing/blocked/not-applicable states | explicit mappings and regressions | PASS | Preserve |
| No fabricated financials | deterministic BRREG accounting path | PASS | Preserve |
| External precision >=95% | strong wrong-entity regressions; previous heldout website audit 20/20 correct; later site promotions manually audited | PARTIAL / strong observed evidence | Hidden evaluator authoritative |
| Weighted external company recall >=60% | H2e+H2g gives near-universal workforce evidence; website/social/contact remain much narrower; official hidden denominator unavailable | **OPEN / PRIMARY UNKNOWN** | Measure release diagnostics; Builderr hidden judge decides |
| Coverage >=21/35 | official field availability/union hidden | **OPEN / PRIMARY UNKNOWN** | Cannot honestly self-score |
| Overall >=65/100 | hidden judge | OPEN | Do not invent score |
| Idempotent refresh/history | exact change fixture + zero-change rerun; old/new hashes and provenance preserved | PASS current tracked fields | Re-check post-H2g release package |
| 45-minute wall time / 100 | H2g default 100 smoke: 427.825 s | PASS | Revalidate across new ten-chunk release |
| <=2,000 outbound requests / 100 | production structural ceiling exactly 2,000 with H2g; default 100 observed 1,370 | PASS | Keep per-chunk budget gate |
| <=$10 external API spend / 100 | stricter project policy: $0 third-party spend | PASS | Preserve unless policy changes |
| One evaluator command | `scripts/run_signalpost_final.py` | PASS | Freeze exact command/setup |
| Source rights documented | connector register + source landscape audit | PASS production stack | Include in submission package |
| Safe URL/SSRF/redirect handling | hardened site stack | PASS | Preserve |
| Pinned dependencies and tests | `uv.lock`; current suite >200 tests plus subtests | PASS | Run on release SHA |
| Snapshot drift safe | missing BRREG bulk row no longer crashes batch | PASS | Preserve |
| Candidate discovery independently verified | H1 paths nominate only; page evidence proves publication | PASS | Preserve |
| UI exposes evidence/gaps/changes | substantial static prototype exists | PARTIAL | Harden after release data is frozen |
| Research answers are evidence-bounded | deterministic answer/screen layer abstains when unsupported | PARTIAL / safe | Improve synthesis after release-scale data run |
| Models/APIs/licences/caches/hosting declared | mostly documented across connector/decision docs | PARTIAL | Produce final submission manifest |

## Current official-scoring readiness

| Official category | Current readiness | Why |
|---|---|---|
| Coverage & source discovery (35) | **YELLOW/RED — materially improved, not established** | H2g dramatically raises workforce coverage, but ratings/reviews, independent activity, metrics, sentiment and platform breadth remain sparse; official weighted recall is hidden |
| Accuracy, identity & evidence (30) | **GREEN / strongest** | exact-org anchoring, conservative site identity, claim evidence and extensive wrong-entity regressions |
| Refresh & extensibility (20) | **GREEN current fields / YELLOW breadth** | robust refresh contract; fewer dynamic external families than ideal |
| Decision-useful synthesis (10) | **YELLOW** | safe evidence-bounded layer but needs release-data-driven polish |
| UX & interaction (5) | **YELLOW** | usable static prototype; final polish remains |

Do not convert readiness labels into an invented official score.

## Post-H2g production evidence

Production application SHA before documentation-only PR #27:

`b14ef3c277d8f1512064f865d4028e23dcd8bacf`

### H2g integrated fresh 300

- final objects: 300/300
- H2e+H2g workforce companies: **296/300 = 98.67%**
- H2g accepted: 256/260
- H2g requests: 260
- observed conservative request charge: 4,106 / 6,000
- wall runtime: 1,277.63 s / 2,400 s
- $0 third-party cost
- 0 execution/external-validation/contract errors

### H2g default 100 production smoke

- final objects: 100/100
- workforce companies: **100/100**
- H2g accepted: 84/84
- observed conservative request charge: **1,370 / 2,000**
- structural ceiling: **2,000 / 2,000**
- wall runtime: **427.825 s**
- $0 third-party cost
- 0 execution/validation/contract/budget errors

## External-source experiments after H2g

- H2h Fagfolkguiden reviews: **DROP**. Fresh 100 produced 21 exact pages but 0 rated companies; rights also unresolved because pages expose Google-derived review content.
- H2i NAV jobs: **SHELVED**. A bounded 20-company screen traversed 30,000 feed items and found 0 exact active jobs; workforce is already near-saturated.
- Remaining zero-cost candidates were audited in `FINAL_SOURCE_LANDSCAPE_AUDIT.md`; broad connector hunting is paused unless new evidence changes the source landscape.

## Historical release evidence

The older 1,000-company release (800 + predeclared 200 heldout) remains valid evidence for its audited application SHA, including 20/20 manually correct heldout websites, but it predates H2g and therefore cannot certify the current production stack. Its heldout 200 is consumed and must never be reused for tuning.

## Next action

Follow the finalization plan in `FINAL_SOURCE_LANDSCAPE_AUDIT.md`:

1. reconcile permanent documentation;
2. freeze a new deterministic 1,000-company corpus excluding all previously touched companies;
3. run current production in ten evaluator-shaped 100-company chunks;
4. aggregate coverage/precision/operations diagnostics without changing company outputs;
5. improve evidence-bounded synthesis and the existing prototype;
6. freeze the final SHA, manifest, source/licence register and submission package.