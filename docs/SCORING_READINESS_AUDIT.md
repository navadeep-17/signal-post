# Signalpost challenge scoring readiness audit

Updated: 2026-09-17

This is a release-readiness audit against the current live Builderr Signalpost challenge. It does not convert local diagnostics into an invented official score.

## Authority and claim boundary

Source-of-truth order:

1. current live Builderr Signalpost challenge page for scoring, qualification and resource limits;
2. starter `README.md`, `OUTPUT_CONTRACT.md` and tests for evaluator interface;
3. starter implementation/docs as diagnostics;
4. our measured experiments.

Official scoring remains 35 coverage / 30 accuracy / 20 refresh / 10 synthesis / 5 UX. Qualification requires at least 65 overall, at least 21/35 coverage, at least 60% weighted external company recall, at least 95% external precision, and all hard gates. Builderr owns the external availability denominator and hidden company labels, so official coverage points and weighted recall cannot be computed locally.

## Current production candidate

Production application SHA:

`b14ef3c277d8f1512064f865d4028e23dcd8bacf`

Current `main` also contains documentation-only PR #27 (`013ae109...`) recording the final source-landscape audit. No application behavior changed in PR #27.

## What is already proven or strongly evidenced

| Requirement / score area | Evidence | Readiness |
|---|---|---|
| Terminal outputs | large runs and H2g qualification complete without silent drops | GREEN |
| Output contract / evidence | claim-specific evidence, URLs, timestamps, hashes and reporting periods validate cleanly | GREEN |
| Financial honesty | deterministic BRREG path; missing is not zero | GREEN |
| Exact website identity | hardened wrong-entity regressions plus prior heldout 20/20 website audit | GREEN observed / hidden judge authoritative |
| Workforce evidence | H2e+H2g reached 296/300 on fresh transfer and 100/100 on default 100 smoke | GREEN strong |
| Request budget | H2g structural ceiling exactly 2,000 conservative requests/100; default 100 observed 1,370 | GREEN |
| Runtime | H2g default 100: 427.825 s; integrated 300: 1,277.63 s | GREEN |
| Third-party cost | $0 | GREEN |
| Refresh/idempotency | deterministic change contract and zero-change replay | GREEN current fields |
| Source rights / safe URLs | production uses official/company-owned/CC0 nomination paths with documented gates | GREEN |
| Research/screening | deterministic evidence-bounded answers; unsupported topics abstain | YELLOW |
| UX | substantial static prototype exists | YELLOW |
| Coverage >=21/35 | hidden evaluator required | **NOT ESTABLISHED** |
| Weighted external recall >=60% | hidden evaluator required | **NOT ESTABLISHED** |
| Overall >=65 | hidden evaluator required | **NOT COMPUTABLE LOCALLY** |

## H2g changed the coverage picture

Before H2g, workforce evidence existed mainly where the live BRREG entity record exposed employee count. H2g adds exact-entity workforce observations from the latest official annual-account PDF only when H2e is absent.

Independent fresh-300 transfer:

- H2e workforce: 40/300;
- H2g selected: 260;
- H2g accepted: 256/260 = 98.46%;
- combined workforce coverage: **296/300 = 98.67%**;
- exact organisation number recovered in all 260 tested reports;
- zero validation/contract/execution errors;
- $0 third-party cost.

Integrated production qualification:

- 300/300 terminal objects;
- 296/300 workforce companies;
- 4,106 conservative request charge / 6,000;
- 1,277.63 s / 2,400 s;
- $0;
- zero production qualification errors.

Default 100-company production smoke:

- 100/100 terminal objects;
- **100/100 workforce companies**;
- H2g accepted 84/84;
- 1,370 conservative requests / 2,000;
- 427.825 s;
- $0;
- zero execution/validation/contract/budget errors.

This is strong evidence for the workforce/jobs information family, but it must not be relabelled as ratings, reviews, buzz, engagement or sentiment.

## External signal breadth still missing

Current production has qualified:

- exact verified official website evidence;
- company-owned description/structured page evidence where present;
- verified company-declared social-profile URLs;
- verified same-domain contact email;
- official workforce snapshot through H2e/H2g.

The largest remaining sparse/absent families are:

- ratings/reviews/place summaries;
- dated independent/public activity;
- social follower/engagement metrics;
- qualified sentiment;
- broader second-platform external evidence.

### Measured post-H2g screens

**H2h Fagfolkguiden reviews — DROP**

Fresh 100, excluding 5,800 prior companies:

- 100 requests;
- 21 exact company pages;
- **0 rated companies**;
- 77 HTTP 404s, 2 source errors;
- runtime 513.779 s;
- $0;
- publication disabled;
- rights remained unresolved because page ratings were Google-derived.

Zero measured rating yield plus uncertain publication rights makes further H2h work unjustified.

**H2i NAV jobs — SHELVED**

Bounded 20-company feasibility screen:

- 90-day lookback;
- 30 feed pages / 30,000 items traversed;
- 7 candidate employer headers;
- 3 detail requests;
- **0 exact main/subunit active-job matches**;
- 54 logical requests;
- $0.

Even if later cohorts yield jobs, the local workforce/jobs family is already near-saturated by H2e/H2g, so incremental scoring leverage is weak.

## Current official-category readiness

### Coverage & source discovery — 35

**Status: YELLOW/RED — materially improved but not proven.**

H2g dramatically strengthens one major external information family. However, Builderr weights multiple external fields and owns the availability denominator. Sparse ratings/reviews, public activity/metrics, sentiment and source breadth mean we still cannot claim 21/35 or 60% weighted external recall.

### Accuracy, identity & evidence — 30

**Status: GREEN / strongest area.**

Exact org-number anchoring, conservative website verification, wrong-org vetoes, claim-level provenance and explicit abstention behavior remain the project's strongest qualities.

### Refresh & extensibility — 20

**Status: GREEN current fields / YELLOW breadth.**

Idempotent refresh and previous/current evidence are implemented. Dynamic external-signal breadth is narrower than ideal.

### Decision-useful synthesis — 10

**Status: YELLOW.**

The research layer is safe and source-bounded. The next value now comes from presenting the qualified release data more clearly rather than inventing missing signals.

### UX & interaction — 5

**Status: YELLOW.**

The static prototype is substantial but needs release-data-driven polish, especially visible provenance, missing states, workforce periods and change history.

## Source-hunting stop decision

The final source landscape audit reviewed the remaining zero-cost candidates and set a stop rule: do not start another full connector cycle unless a source plausibly improves a genuinely unsolved information family, has suitable rights, supports exact entity proof, remains $0, shows roughly 5–10% random-company reach (or equal hidden-evaluator value), fits request/runtime limits, and supports deterministic evidence/refresh semantics.

Under current evidence, no remaining source clears that bar strongly enough to justify another broad connector cycle. See `FINAL_SOURCE_LANDSCAPE_AUDIT.md`.

## Release finalization plan

The next engineering work is:

1. reconcile permanent production docs after H2g/H2h/H2i;
2. freeze a new deterministic 1,000-company corpus outside all previously touched companies (historical exclusion count is 5,900 unique companies after H2h; H2i reused H2h companies);
3. run current production in ten independent evaluator-shaped 100-company chunks;
4. aggregate operational and coverage diagnostics without altering outputs;
5. improve evidence-bounded synthesis and the existing prototype around the qualified fields;
6. freeze final code SHA, manifest/digest, source/licence register, setup instructions and submission package.

The previous 1,000 release remains evidence for its older application SHA, but it predates H2g and its heldout subset is consumed. It must not be used to certify or tune the current production stack.