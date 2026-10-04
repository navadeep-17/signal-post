# Signalpost — Current Continuation State

Last updated: 2026-10-04

This is the **first file every new implementation chat must read**. It is intentionally short and current. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; strategy belongs in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Current production `main` SHA:

`911ecef4f785bb5f2b5aa7cf75a52efd6f7c3051`

Latest merged PR:

- PR #92 — `Phase 1: recover evaluator-visible exact BRREG claims`
- merge commit: `911ecef4f785bb5f2b5aa7cf75a52efd6f7c3051`

Post-merge Baseline CI:

- run `37193327713`
- status: **PASS**

Previous major milestone:

- PR #90 — C12 M4 bounded current first-party jobs
- merge commit `fb4c8711b9a3c58c16c6ff1c26aada93c036938a`

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

## 3. What is already productionized

### Official / canonical foundation

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

### Phase 1 lost-claim recovery now merged

PR #92 recovered evaluator-visible exact BRREG facts that were already available in live registry evidence but were previously discarded or insufficiently projected.

Production now retains/projects:

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

This is the first completed item under Phase A of the 70+ roadmap: **zero-risk collected-but-unpublished fact recovery**.

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

## 4. Previous major milestone — C12 M4 jobs

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

## 5. Known measured production strengths

- exact terminal-output behavior is strong;
- evidence completeness and hashes are strong;
- refresh/idempotency is strong;
- runtime/request accounting is strong;
- $0 third-party API policy is preserved;
- workforce coverage became near-universal after H2g;
- website precision has been protected through repeated manual audits and regressions;
- Phase 1 proved substantial evaluator-visible recall can be recovered without new sources or added requests.

Do not weaken these strengths to chase recall.

## 6. Primary remaining risk

**Recall / company coverage**, especially non-registry information families.

Phase 1 substantially improves official/canonical breadth, but we still need more distinct checked information families across more companies while preserving exact identity and evidence.

Optimize **net-new companies covered per information family**, especially:

- concrete jobs;
- dated first-party activity;
- contact/social/people/location facts unlocked by verified sites;
- any broad exact-ID official source that reaches companies without requiring a website.

Do not optimize merely for total claim count.

## 7. Exact next action

Phase A is **partially complete**: lost-claim BRREG recovery has shipped.

Next:

1. run/complete a current-main evaluator-shaped **family coverage matrix** after PR #92;
2. compare all internally collected data against canonical emitted facts to identify any remaining zero-risk projection gaps;
3. measure current M3/M4 company coverage for concrete jobs and dated activity on a fresh cohort;
4. measure website/contact/social/people/location company coverage on the same cohort;
5. select the next implementation only from measured net-new company opportunity.

If no meaningful projection gaps remain, move to **Phase B — verified-site enrichment 2.0 + adaptive request allocation** from `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 8. Do-not-repeat decisions

- Do not loosen exact website identity to recover recall.
- Do not treat generic careers pages as jobs.
- Do not revive guessed `.com` discovery without new evidence; prior H1f produced no useful net gain and namesake risk.
- Do not scrape LinkedIn/Facebook/Glassdoor for production.
- Do not rely on random review scraping.
- Do not use paid search/API services under the current $0 project constraint.
- Do not submit after every small patch.
- Do not tune against Builderr's checked collection.
- Do not use an old local scoring rubric when the live challenge page differs.

## 9. Session handoff protocol

Before doing implementation work, a new chat must:

1. read this file;
2. read `docs/70_PLUS_IMPLEMENTATION_PLAN.md`;
3. inspect current `main` SHA and open PRs;
4. verify any time-sensitive Builderr rule against the live official page;
5. continue from the exact `NEXT` item below.

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

## 10. NEXT

**NEXT:** Post-Phase-1 current-main family-coverage + remaining collected-vs-emitted audit. Then select Phase B only if no meaningful zero-risk projection gaps remain.
