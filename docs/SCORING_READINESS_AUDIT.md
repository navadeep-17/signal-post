# Signalpost challenge scoring readiness audit

Date: 2026-09-15

This document is a release-readiness audit against the **current live Builderr Signalpost challenge**, not the older indexed Signalpost variants and not the starter repository's local competition proxy.

## Authority and claim boundary

Source-of-truth order remains:

1. current live Builderr Signalpost challenge page for scoring, qualification and resource limits;
2. starter `README.md`, `OUTPUT_CONTRACT.md` and tests for the evaluator interface;
3. starter implementation/docs as local diagnostics;
4. project measurements and experiments.

Current live challenge: <https://www.builderr.ai/challenges/signalpost>

The live challenge currently scores:

| Category | Points |
|---|---:|
| Coverage & source discovery | 35 |
| Accuracy, identity & evidence | 30 |
| Refresh & extensibility | 20 |
| Decision-useful synthesis | 10 |
| UX & interaction | 5 |

Qualification requires at least 65/100 overall, at least 21/35 coverage, at least 60% weighted external company recall, at least 95% external precision, and all hard gates. For each external field, Builderr states that 70% of its coverage score is company recall and 30% is claim recall. The evaluator-owned external field union and gold availability labels are not available locally, so **official coverage points and weighted external recall cannot be computed from our own outputs**.

The starter's `score_competition_v3.py` (55/15/10/12/8) is retained only as a development proxy. It is not the official rubric.

## Frozen release candidate

Audited application code SHA:

`24145ffb98e36c31a16145d6408a7556a38b5289`

Current `main` additionally contains documentation-only PR #20 recording the release audit. No application behavior changed after the audited SHA.

Release evidence:

- non-heldout 800 workflow: `34946808243`
- non-heldout artifact digest: `sha256:153fd7bf25a424650fe427bde8d0da559aec0835184892ba2fa231900d08655e`
- predeclared heldout 200 SHA: `fb81f7695ee91606d1af7eee00e8323a326ebc33b79b3cb1a4f046573ae3368f`
- heldout workflow: `34948307697`
- heldout artifact digest: `sha256:d2e87c64324df31643ef969b9fd432d33fe971c8689c36833b9a56edf5176efd`
- complete audit: `docs/FINAL_RELEASE_AUDIT.md`

The heldout 200 is now consumed. It must not be used for further tuning.

## What is already proven

| Requirement / score area | Evidence | Readiness |
|---|---|---|
| Exactly 100 terminal outputs | frozen-100 final runner and larger 800/200 release runs completed with zero silent drops | GREEN |
| Output contract / claim evidence | claim-specific evidence, source URL/class, retrieval time, hashes and period where relevant validate cleanly | GREEN |
| Financial honesty | deterministic BRREG path; missing is not converted to zero | GREEN |
| Missing/blocked states | explicit terminal states and regressions | GREEN |
| Exact website entity safety | final heldout website audit 20 correct / 0 wrong | GREEN observed; not a statistical proof of population precision |
| Request budget | structural ceiling 1,802 conservative requests/100; release runs comfortably below limit | GREEN |
| Runtime | frozen 100 about 95 s; 800 run 518.772 s; heldout 200 run 122.656 s | GREEN |
| Third-party API cost | $0; search API requests 0 | GREEN |
| Refresh/idempotency | deterministic change contract and current→current zero-change replay | GREEN for current tracked fields |
| Source rights / safe URLs | current production stack is official/company-owned/Wikidata-candidate-only with rights register and SSRF/redirect guards | GREEN current stack |
| Research/screening | deterministic, evidence-bounded answers and structured screen parser; explicitly abstains on unqualified external topics | YELLOW |
| UX | substantial static prototype exists, but external intelligence is sparse | YELLOW |
| Coverage >=21/35 | hidden evaluator required | **NOT ESTABLISHED** |
| Weighted external company recall >=60% | hidden evaluator required | **NOT ESTABLISHED** |
| Overall >=65/100 | hidden evaluator required | **NOT COMPUTABLE LOCALLY** |

## Release-scale operational evidence

### Non-heldout 800

- 800/800 completed terminal outputs
- 12,696 claims and 12,696 evidence items
- 4,688 observed logical requests
- 9,376 conservative challenge request charge
- 518.772 seconds wall runtime
- $0 third-party API spend
- 0 search API requests
- 0 contract/change/budget errors
- 55 verified websites
- one current-BRREG snapshot drift company retained safely

### Final heldout 200

- 200/200 completed terminal outputs
- 3,191 claims and 3,191 evidence items
- 1,208 observed logical requests
- 2,416 conservative challenge request charge = 1,208/100 normalized
- 122.656 seconds wall runtime
- $0 third-party API spend
- 0 search API requests
- 0 contract/change/budget errors
- 20 verified websites
- all 20 manually audited correct; 0 wrong-company publication observed

The 20/20 result is 100% observed point precision, but the sample is too small to claim that it statistically proves an underlying precision of at least 95% (approximate 95% Wilson lower bound is about 83.9%).

## Observable external coverage on the full frozen 1,000

The following numbers were computed from the exact 800 + 200 release artifacts. They are **population reach diagnostics, not Builderr's official external recall**.

| Company-owned field already in production artifacts | Companies | Population reach |
|---|---:|---:|
| Verified official website | 75 | 7.5% |
| Published company description from verified site | 56 | 5.6% |
| Publishable company-declared social-profile links | 32 | 3.2% |

The 32 companies with publishable declared social profiles contain 55 exact-handle links:

| Platform | Companies with a publishable declared handle |
|---|---:|
| Facebook | 25 |
| Instagram | 19 |
| LinkedIn | 10 |
| YouTube | 1 |

Nineteen companies expose at least two publishable social platforms through the already-verified company-site evidence.

These links are useful exact profile identities, but they do **not** mean Signalpost has fetched or qualified metrics/posts from those platforms. They therefore must not be counted locally as jobs, buzz, engagement, reviews or sentiment.

## Current production external-signal gap

The final runner's promoted modules are official registry/accounting data plus exact company website evidence. It does not currently publish production observations for:

- active jobs / hiring direction;
- workforce snapshots beyond official registry employee data;
- ratings / reviews / place summaries;
- dated public posts or independent mentions;
- social follower/engagement metrics;
- qualified sentiment.

This is the primary release risk. High identity precision cannot compensate for the live challenge's mandatory 21/35 coverage and 60% weighted external-company-recall gates.

The connector register confirms why these fields are absent: paid search/Places paths conflict with the project's $0 policy, LinkedIn/Glassdoor/public-platform scraping remains experimental or rights-blocked, and sentiment has not been qualified.

## Scoring readiness by official category

### Coverage & source discovery — 35 points

**Status: RED / not established.**

Builderr controls the external availability denominator and claim union. Local website population reach is only 7.5%, while several external signal families are not in the final runner at all. We cannot honestly assert 21/35 or 60% weighted recall yet.

### Accuracy, identity & evidence — 30 points

**Status: GREEN / strongest area.**

The project has exact organisation-number anchoring, conservative website identity, explicit wrong-org vetoes, independent candidate verification, claim-specific evidence and a clean heldout website audit. Precision must still be confirmed by Builderr's hidden evaluator, but current observed evidence is strong.

### Refresh & extensibility — 20 points

**Status: GREEN for current fields; YELLOW for breadth.**

Idempotent refresh, previous/current values and hashes, source provenance and zero-change reruns are implemented. The limitation is that few external dynamic signal types are currently promoted, so external refresh breadth is narrow.

### Decision-useful synthesis — 10 points

**Status: YELLOW.**

The research layer returns only source-linked facts and has deterministic screening. It correctly abstains on sentiment, reviews, LinkedIn-derived employee data and buzz because those sources are not qualified. This is safe, but limits decision usefulness until external observations expand.

### UX & interaction — 5 points

**Status: YELLOW.**

The static prototype provides a useful profile shape, but product polish cannot make up for missing external evidence. UX work should follow the next external-signal qualification rather than precede it.

## Next bounded experiment: H2a company-declared social profile observations

The best immediate zero-cost scoring experiment is to reuse **already-fetched, exact company-owned website evidence** and convert publishable company-declared handles into formal `profile_handle` external observations.

Why this is first:

1. the 1,000 release artifacts already expose 55 publishable handle links across 32 companies;
2. no social-platform request is needed to assert only the narrow claim "this exact company website declares this profile URL";
3. candidate identity inherits the exact company-site gate and the existing deterministic social-handle gate;
4. source URL, retrieval time and content hash already exist;
5. an older dormant branch (`feature/company-site-social-handles`, commit `ea9dfc13a00fa7f7f66177bd3f824fbfe5535b82`) already contains a conservative implementation that abstains when per-link provenance is ambiguous;
6. this creates explicit external profile observations without violating the $0 policy or pretending we fetched social-platform content.

The dormant implementation must **not** be merged directly because it predates H1d/H1e and the final runner. Port the concept onto current `main`, preserve the audited identity rules, then validate on a new disjoint corpus outside the consumed 1,000.

Acceptance gate for H2a:

- zero additional network requests for extraction itself;
- $0 third-party API spend;
- every observation passes `external_footprint.validate_observation`;
- exact source-page provenance (do not use a merged multi-page social list when the declaring page is unknown);
- no claim that a profile is active/current merely because its URL is linked;
- no follower/post/engagement metrics unless independently fetched through an approved connector later;
- manual audit of every published observation on a fresh disjoint validation set;
- no use of the consumed 200-company holdout for tuning.

## Experiment after H2a

After formal profile-handle observations, the next highest-value zero-cost routes should be measured separately:

1. **company-owned dated news/activity pages** from verified sites;
2. **company careers/jobs pages**, but only if a new bounded experiment beats the previous low-yield jobs attempt;
3. annual-report workforce evidence where period-correct official filings provide useful workforce signals;
4. only then reconsider a genuinely free official platform API if its quota/reproducibility and rights remain valid for the entire competition.

The older `feature/company-careers-signals` audit is useful prior art, but it must be judged by its measured yield before being revived. No experiment earns production status merely because code exists.

## Release discipline from this point

The heldout 200 has been consumed. Therefore any future application change creates a **new release candidate** and must use new disjoint validation companies outside the original frozen 1,000 for tuning and transfer checks. The old heldout result remains evidence for SHA `24145ffb98e36c31a16145d6408a7556a38b5289`; it cannot certify later behavior.

Do not change identity thresholds to recover coverage. Candidate discovery and external-signal extraction may broaden, but publication must remain exact and evidence-backed.
