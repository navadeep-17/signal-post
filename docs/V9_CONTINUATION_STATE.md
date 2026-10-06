# Signalpost V9 Continuation State

Last updated: 2026-10-06

This document is the V9 engineering handoff. Live GitHub is authoritative if any recorded SHA advances.

## M0 freeze verification

- current production `main`: `72f1bf2892ec1c1e35674aa383433c9a37afdaca`
- frozen qualified SHA: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- frozen qualified ref: `release/v8-qualified-2026-10-06`
- frozen submission ref: `release/v8-submission-2026-10-06`
- submission ref currently equals `main`
- V9 branch: `experiment/v9-email-domain-substitution`
- V9 branch base: exact current `main`
- research branch: `research/bulk-exact-org-recall`
- live research relation observed at V9 start: **+293 / -67 vs main**
- the research branch remains an archive and must never be merged wholesale

The live relation differs from the planning PDF's earlier +289/-67 snapshot; live GitHub wins.

`docs/CONTINUATION_STATE.md` on `main` records the latest pre-cleanup Baseline CI run `37407690443` as PASS. The GitHub connector's commit-run wrapper exposes PR-triggered runs only and returned no directly attached run for the current main commit, so V9 branch CI is still a separate gate.

Decision: **M0 PASS**. V8 refs were not moved or rewritten.

## Active milestone

**M1 measurement harness + M2 budget-neutral strong BRREG registry-email-domain substitution.**

North-star:

> net-new exact-company coverage per Builderr-scored family per request

The V9 challenger must not optimize raw claim count.

## First implementation block

Implemented on the isolated V9 branch only:

1. A company-family measurement module/CLI that compares baseline and challenger on an identical cohort and reports:
   - verified website companies;
   - social companies;
   - external-contact companies;
   - careers-surface companies;
   - company-authored hiring-intent companies;
   - specific active-job companies;
   - dated first-party activity companies;
   - logical/conservative request charge;
   - terminal/error/cost summaries.
2. The initial BRREG email-domain selector admitted `exact`, `multi`, or `acronym`; the M2 RETUNE now also preserves `partial` candidates because targeted consumed evidence showed that pre-fetch removal of partial domains can delete exact verified sites.
3. The candidate remains nomination only. Independent fetch, existing exact-company verifier, wrong-org veto, registry-risk guard, and all publication evidence rules remain unchanged.
4. The current retune substitutes only clearly unrelated (`none`) registry-email domains. `partial` remains candidate nomination only and still must pass the unchanged independent exact-company verifier.

## Safety boundary

Do not:

- move either V8 release ref;
- merge the research branch wholesale;
- weaken exact-company verification;
- use an email domain as ownership proof;
- consume a fresh cohort for M1/M2 tuning;
- add search/paid API requests;
- increase `MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE`;
- merge this branch before consumed baseline-vs-challenger transfer evidence exists.

## M2 consumed-transfer decision

Decision: **RETUNE**. M2 is not promoted and no later milestone may be stacked on it yet.

The governing consumed evidence is the exact-branch push run `37464768685` at challenger
`58723f89fa192a1dd449c72f907ac86bd477c203`, compared with frozen `main`
`72f1bf2892ec1c1e35674aa383433c9a37afdaca`. The subsequent branch commit
`69c73fb38371ee14312fb75c8b91c76947fc3e5c` was an empty commit with the same Git tree
`19e9f049a1acbfe3ba3c1e24bc1fe8d7628dd37f`, so the measured implementation tree is identical.

The PR-triggered run `37464804373` checked GitHub's synthetic merge commit
`09020e31ba36147a360c5f93ccb579b58731d22d`; it is useful corroboration but is not the
governing exact-branch result. The M2 workflow has since been tightened to explicitly check out
the PR head SHA and verify that recorded challenger SHA.

Consumed 100-company exact-branch result:

- verified website companies: **6 -> 5**; net-new **0**; lost **1**;
- social companies: **4 -> 4**;
- external-contact companies: **5 -> 5**;
- careers-surface companies: **0 -> 0**;
- company-authored hiring-intent companies: **0 -> 0**;
- specific active-job companies: **0 -> 0**;
- dated first-party activity companies: **1 -> 1**;
- net-new scored company-family coverage: **0**;
- evaluator-family publications added: **0**;
- evaluator-family publications lost: **1**;
- reported per-company conservative request charge: **1378 -> 1320**;
- whole-run observed logical requests: **692 -> 663**;
- whole-run observed conservative challenge charge: **1384 -> 1326**;
- theoretical conservative ceiling: **2000 -> 2000**;
- wall runtime: **636.253 s -> 635.181 s**;
- third-party API cost: **$0 -> $0**;
- search API requests: **0 -> 0**;
- terminal outputs: **100/100 -> 100/100**;
- source-level reported errors: **162 -> 164**;
- contract errors: **0**;
- canonical validation errors: **0**;
- synthesis validation errors: **0**;
- external-observation validation errors: **0**;
- wrong-company new publications after manual audit: **0**.

Manual publication audit is complete because the challenger added **zero** evaluator-family
publications. The single lost publication was separately regression-audited: organisation
`921093934`, `https://www.aursneskiosk.no/`. The retained baseline evidence classified it
as exact with score 0.98, full normalized legal-name tokens, registry-location/title-domain
corroboration, and same-domain secondary identity corroboration. Treat the loss as a real
verified-site regression, not as removal of a dubious publication.

Why RETUNE rather than PROMOTE: the challenger saved observed requests but produced no
net-new scored-family coverage and violated the no-existing-verified-site-loss gate. The likely
retune target is candidate allocation/priority: a strong email-domain nomination must not
consume the request opportunity needed to retain an already productive deterministic H1c path.
Do not weaken identity gates to repair this.

## Milestone sequencing lock

Until the M2 retune passes consumed transfer and manual audit:

- do not start M5 or M6;
- do not stack M4 onto M2;
- do not consume a fresh cohort;
- do not merge PR #142;
- keep PR #143 as the canonical isolated M4 experiment based from `main`;
- PR #144 is superseded/closed and must not be revived;
- keep PR #137 parked as optional M9-only search fallback.

Builderr's current official path must remain credential-free. No general model/search provider
is injected by default and participant-owned API keys are not used. If Builderr later explicitly
arranges a reproducible provider/key, paid model/search/tool usage shares the official **$10**
external-API cap per 100-company shard; internal planning should target at most **$8** with about
**$2 reserve**. Current shard limits remain **45 minutes**, **2,000 outbound requests**, and
**$10 external API cost**.

## Exact next action

Remain in **M2 RETUNE**. Diagnose and fix the one-site regression without increasing the
four-logical-site-request ceiling, then re-run the same consumed 100-company baseline/challenger
gate on the exact challenger head. Promotion still requires zero website losses, positive
net-new scored-family coverage, zero wrong-company publications, clean contract/canonical/
synthesis/evidence validation, and the unchanged <=2,000 worst-case request theorem.


## M2 RETUNE causal-exposure result

A targeted consumed-only gate was added so M2 is measured on companies whose request allocation
actually changes, rather than relying on a random consumed 100 with little causal exposure.

Consumed-1000 causal census run `37484232499` (fresh companies used: **0**) found:

- registry website already present: **116**;
- eligible without registry website: **884**;
- initial M2 behaviorally affected (`m2_delta`): **69**;
- initial strong-email controls: **18**;
- no-email controls: **797**;
- baseline candidate strengths among email candidates: exact **15**, acronym **2**, multi **1**,
  partial **15**, none **54**.

The first targeted transfer run `37483662873` included all **69** affected companies, all
**18** same-candidate controls, and **13** no-email controls. Control variance was **false**,
so publication movement in that run is causally attributable to the M2 allocation change.

Targeted result:

- verified websites: **8 -> 7**; **+1 new / -2 lost**;
- social: **5 -> 5**; **+1 / -1**;
- external contact: **4 -> 4**; **+1 / -1**;
- careers surface: **2 -> 3**; **+1 / -0**;
- company-authored hiring intent: **0 -> 0**;
- specific active jobs: **0 -> 0**;
- dated first-party activity: **2 -> 1**; **+0 / -1**;
- net-new family-company edges: **4**;
- lost family-company edges: **5**;
- new evaluator-family publications: **5**;
- lost evaluator-family publications: **6**;
- observed conservative request charge: **1602 -> 1358**;
- theoretical ceiling: **2000 -> 2000**;
- wall runtime: **702.497 s -> 639.446 s**;
- external API cost: **$0**;
- search API requests: **0**;
- machine decision: **RETUNE_LOSS**.

Manual audit of all five new publications is complete. All five belong to organisation
`999096298`, **DEN GLADE GRIS AS**, and derive from the newly recovered exact site
`https://www.dengladegris.no/`: official website, careers surface, Facebook, Instagram and
same-domain contact email. The retained site identity is exact at **0.98**, matches all legal-name
tokens, and records bounded same-domain secondary identity corroboration. Evidence is hashed and
timestamped. Manual result: **5/5 reviewed, 0 wrong-company new publications**.

The six lost publications are also real regressions, all inside the causal `m2_delta` bucket.
Two lost verified sites explain the family losses:

- `943378649`, **OPUS AS**, `https://opusas.no/`: BRREG registered email
  `oad@opusas.no`; baseline website identity exact at **0.95**. Its email-domain morphology is
  classified `partial`.
- `965880437`, **KOKKERSVOLD AS**, `https://kokkers.no/`: BRREG registered email
  `kjell@kokkers.no`; baseline website identity exact at **1.0** with explicit organisation
  number `965880437`. Its email-domain morphology is also `partial`, and losing the site also
  loses two strict dated same-site feed updates.

This isolates the defect in M2 iteration 1: rejecting every `partial` candidate before fetching
is too aggressive. Morphology is only a nomination heuristic; the unchanged exact-company verifier
is what decides publication.

### M2 RETUNE iteration 2

The candidate-allocation policy is therefore narrowed:

- preserve `exact`, `acronym`, `multi`, and `partial` registry-email candidates;
- substitute only `none` candidates;
- do not weaken or bypass any identity/evidence gate;
- do not increase the four-logical-site-request ceiling;
- do not use search or paid APIs;
- re-run the consumed causal census and targeted consumed-100 transfer before any promotion.

Expected causal exposure under the same census is approximately the **54** `none` candidates,
rather than all 69 initial affected companies; the new census is authoritative once complete.

Decision remains **RETUNE** until iteration 2 passes zero-loss, positive-family-lift and manual
precision gates.
