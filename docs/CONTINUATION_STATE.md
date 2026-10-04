# Signalpost — Current Continuation State

Last updated: 2026-10-04 15:57 Asia/Kolkata

This is the **first file every new implementation chat must read**. It is intentionally short and current. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; strategy belongs in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Current production `main` SHA:

`bd6b337ce89770fb3cc7633d1e1cf1852d5f89c2`

Latest merged production feature:

- PR #92 — `Phase 1: recover evaluator-visible exact BRREG claims`
- merge commit: `911ecef4f785bb5f2b5aa7cf75a52efd6f7c3051`
- post-merge Baseline CI run `37193327713`: **PASS**

Current `main` is one documentation merge ahead of that feature:

- commit `bd6b337ce89770fb3cc7633d1e1cf1852d5f89c2`
- message: `docs: add 70+ roadmap and cross-chat continuation system`
- production code semantics remain the Phase-1 code line.

### Active implementation branch / PR

- active branch: `feature/phaseb-idle-contact-enrichment`
- PR #94 — `Phase B: exact-site contact phone enrichment`
- PR state: **OPEN / DRAFT / NOT MERGED**
- exact branch head: `f04c1faee580a9e61194d00a0ef2625936d91871`
- base: `main` at `bd6b337ce89770fb3cc7633d1e1cf1852d5f89c2`
- Baseline CI on exact head: run `37195005850` — **PASS**
- consumed-cohort E2E: run `37195003615` — **IN PROGRESS** at the actual V8 evaluator stage as of this update.

Other open draft PRs are historical/experimental and are not the current production path:

- PR #84 — provider-gated V9 M1c readiness; no live provider qualification dispatched;
- PR #78 — V9 Website Discovery 2.0 experiment; not wired into production V8;
- PR #76 — stale V7 exact-org BRREG registered-contact fallback; do not merge directly.

Do not infer state from older chat messages if GitHub disagrees with this file.

## 2. Current Builderr snapshot

Verified from the live Builderr challenge page on 2026-10-04:

- scoring: 50 recall / 30 precision-evidence / 12 synthesis / 8 UX;
- qualification: >=65 overall on an official run;
- public board reviewed 2026-10-03;
- Navadeep public-board entry shown there: **52.41/100** = 12.83 recall + 26.92 evidence + 9.46 synthesis + 3.20 UX;
- current board leader shown there: 60.51/100;
- 0 qualified at that review point;
- up to five total versions: first submission + four revised commit hashes.

Important: the public-board score can correspond to an older submitted SHA. It does **not** prove the current `main` score.

Internal next-major-revision target:

- recall 22-24+
- evidence 28-29+
- synthesis 12
- UX 8
- total 70-73+

## 3. Production state — explicit lifecycle labels

### MERGED + POST-MERGE GREEN — Phase 1 exact BRREG claim recovery

PR #92 recovered evaluator-visible exact BRREG facts that were already available in live registry evidence but were previously discarded or insufficiently projected.

Production retains/projects:

- registration date;
- registered business address;
- registered business/activity description;
- registered purpose;
- registered contact email;
- phone;
- mobile;
- exact source-field lineage into canonical facts.

Fresh zero-overlap qualification for PR #92:

- 100 unique companies; overlap 0;
- seed `20261101`;
- cohort SHA `92fc871ee9c94a928908cf00f007aef67eea02fe788caf70e8e734e82bd76b5d`;
- run `37192494569`;
- artifact `phase1-fresh-disjoint-100`, ID `11299633898`;
- artifact digest `812941edf79709cc2324b907d9efc4b889fc56ee7df9e095bfad2890a9ba5f3d`;
- 100/100 terminal completed;
- company description: 100/100 vs baseline 14/100 on same cohort;
- registered purpose: 96/100 vs baseline 0;
- registration date: 100/100 vs baseline 0;
- registered address: 100/100 vs baseline 0;
- registered contact email: 21/100 vs baseline 0;
- phone: 17/100 vs baseline 0;
- mobile: 16/100 vs baseline 0;
- exact BRREG evidence audit: 100 rows, 0 evidence errors;
- output-contract errors: 0;
- canonical errors: 0;
- synthesis errors: 0;
- logical requests: 669;
- conservative request charge: 1,338/2,000;
- runtime: 449.589 s;
- third-party cost: $0;
- search requests: 0.

State labels:

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** yes, fresh zero-overlap 100
- **MERGED:** yes
- **POST-MERGE GREEN:** yes

### IMPLEMENTED + TESTED, NOT YET QUALIFIED — PR #94 exact-site contact enrichment candidate

Live GitHub shows PR #94 currently contains a Phase B / Phase C candidate that extends exact verified-site contact coverage while preserving the existing site-request ceiling and evidence model. Current PR metadata describes:

- explicitly labelled Norwegian contact-phone extraction from exact verified company pages;
- `external.contact_phone` with canonical `website.contact_phone`;
- separation from official BRREG registered phone/mobile;
- page URL/hash/evidence-span provenance;
- a consumed-cohort contact-page experiment intended to use otherwise-idle site budget without displacing stronger careers/news paths.

Current state labels:

- **IMPLEMENTED:** yes, on branch `feature/phaseb-idle-contact-enrichment`
- **TESTED:** yes, Baseline CI run `37195005850` passed on exact head `f04c1fae...`
- **QUALIFIED:** no — consumed E2E run `37195003615` is still in progress and no fresh promotion cohort has been accepted
- **MERGED:** no
- **POST-MERGE GREEN:** not applicable

Do not merge or call PR #94 complete until the documented Phase A audit is closed and PR #94 passes its own promotion/qualification gates.

## 4. Existing production foundation

### Official / canonical

- exact organisation-number identity anchor;
- BRREG live/bulk data;
- financials;
- roles;
- locations/workplaces;
- group/registry context where available;
- canonical claims + evidence;
- availability states;
- deterministic refresh/change tracking;
- one terminal envelope/company;
- output-contract projection;
- request/runtime/cost accounting.

### Website discovery and identity

Production includes hardened:

- registry website handling;
- registry-email-domain discovery;
- deterministic `.no` discovery;
- legal/contact identity corroboration;
- exact-org Wikidata website candidate path;
- hyphenated `.no` fallback;
- parked/hosting/service-provider/parent/franchise/namesake conflict guards.

Publication remains fail-closed.

### External facts already productionized

- verified company-declared social handles;
- first-party contact emails;
- registry workforce snapshots;
- official annual-report OCR workforce snapshots;
- annual-report business/company description fallback;
- C12 current first-party social provenance improvements;
- C12 bounded dated first-party news detail;
- C12 bounded current first-party job postings.

## 5. Previous major milestone — C12 M4 jobs

PR #90 is merged.

Production behavior:

- generic careers page is **not** a job posting;
- careers follow-up is only spent when an exact verified homepage exposes an explicit positive vacancy-count signal;
- current company-owned role cards / `JobPosting` evidence can materialize specific jobs;
- job publication requires exact employer context and a concrete role/application URL;
- expired jobs abstain;
- parent targets cannot inherit subsidiary jobs;
- third-party ATS URLs may be carried only as action URLs, not employer identity proof;
- C12 M3 news remains the fallback when no qualified careers follow-up is justified;
- site ceiling remains four logical site requests/profile;
- third-party API cost remains $0.

Live proofs:

- Granne `838797172`: vacancy count 0, no careers follow-up, 0 jobs.
- AF GRUPPEN ASA `938702675`: homepage vacancy count 31, bounded careers surface, current jobs published within 4/4 site requests.

M4 proof artifact:

- `c12-m4-live-proof`
- artifact ID `11295658686`
- digest `b51f1ea151329ef3ad98f1c6f66ae09ced0b5d6aaa699e132312b580cac7fe4c`

## 6. Known measured production strengths

- exact terminal-output behavior is strong;
- evidence completeness and hashes are strong;
- refresh/idempotency is strong;
- runtime/request accounting is strong;
- $0 third-party API policy is preserved;
- workforce coverage became near-universal after H2g;
- website precision has been protected through repeated manual audits and regressions;
- Phase 1 proved substantial evaluator-visible recall can be recovered without new sources or added requests.

Do not weaken these strengths to chase recall.

## 7. Primary remaining risk

**Recall / company coverage**, especially non-registry information families.

Phase 1 substantially improves official/canonical breadth, but we still need more distinct checked information families across more companies while preserving exact identity and evidence.

Optimize **net-new companies covered per information family**, especially:

- concrete jobs;
- dated first-party activity;
- contact/social/people/location facts unlocked by verified sites;
- any broad exact-ID official source that reaches companies without requiring a website.

Do not optimize merely for total claim count.

## 8. Exact next action

Phase A is **partially complete**: lost-claim BRREG recovery has shipped.

The next gate remains the repository-documented Phase A audit, even though PR #94 already exists as a draft candidate:

1. complete the post-Phase-1 current-main evaluator-shaped **family coverage matrix** using the frozen Phase-1 qualification artifact where possible;
2. compare internally collected data against canonical emitted facts and identify any remaining meaningful zero-risk projection gaps;
3. record unique-company coverage for website, contact email/phone, social, concrete jobs, dated activity, people, locations, workforce and registry changes;
4. record request/runtime/cost and precision/evidence findings;
5. only if no meaningful zero-risk projection gaps remain, treat PR #94 / Phase B verified-site enrichment as the active next implementation candidate.

Do not consume a new fresh qualification cohort for PR #94 until its consumed-cohort E2E is green and Phase A is explicitly closed in repository documentation.

## 9. Do-not-repeat decisions

- Do not loosen exact website identity to recover recall.
- Do not treat generic careers pages as jobs.
- Do not revive guessed `.com` discovery without new evidence; prior H1f produced no useful net gain and namesake risk.
- Do not scrape LinkedIn/Facebook/Glassdoor for production.
- Do not rely on random review scraping.
- Do not use paid search/API services under the current $0 project constraint.
- Do not submit after every small patch.
- Do not tune against Builderr's checked collection.
- Do not use an old local scoring rubric when the live challenge page differs.

## 10. Session handoff protocol

Before doing implementation work, a new chat must:

1. read this file completely;
2. read `docs/70_PLUS_IMPLEMENTATION_PLAN.md`;
3. inspect current `main` SHA and open PRs;
4. reconcile this file first if GitHub is ahead;
5. verify any time-sensitive Builderr rule against the live official page when required;
6. continue from the exact `NEXT` item below.

At the end of every substantial work session, update this file before stopping.

Required fields to update:

- date/time;
- current `main` SHA;
- active branch;
- active PR and state;
- exact branch head SHA;
- what changed;
- tests/CI runs;
- live/qualification run IDs and artifacts;
- baseline vs new company-coverage metrics;
- precision findings;
- request/runtime/cost impact;
- blockers;
- exact next 1-3 actions.

Never write `done` merely because code exists. Distinguish:

- IMPLEMENTED
- TESTED
- QUALIFIED
- MERGED
- POST-MERGE GREEN

## 11. NEXT

**NEXT:** Complete the post-Phase-1 current-main family-coverage + remaining collected-vs-emitted audit. Close Phase A only if no meaningful zero-risk projection gaps remain. Then continue PR #94 as the Phase B/Phase C candidate, first through its consumed-cohort E2E and only afterward through a fresh disjoint promotion qualification.