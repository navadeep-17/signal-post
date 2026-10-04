# Signalpost Implementation Log

This is the append-only project history used for cross-chat continuity.

Rules:

- Add an entry only for material work: experiments, qualified milestones, merges, important failures, scoring feedback or roadmap changes.
- Keep entries factual and short.
- Record exact branch/PR/SHA/run IDs where known.
- Never rewrite old failures into successes; preserve why a path was rejected.
- Current actionable state belongs in `docs/CONTINUATION_STATE.md`.

---

## 2026-10-04 — Phase 1 exact BRREG lost-claim recovery merged

Status: **QUALIFIED + MERGED + POST-MERGE GREEN**

- PR #92: `Phase 1: recover evaluator-visible exact BRREG claims`
- branch: `phase1/lost-claim-registry-live`
- qualified semantics head: `381a370e36b2e40b36f48e405c5b122191cb199c`
- merge commit: `911ecef4f785bb5f2b5aa7cf75a52efd6f7c3051`
- qualification run: `37192494569`
- artifact: `phase1-fresh-disjoint-100`, ID `11299633898`
- artifact digest: `812941edf79709cc2324b907d9efc4b889fc56ee7df9e095bfad2890a9ba5f3d`
- post-merge Baseline CI: `37193327713`, PASS

What changed:

- retained exact-live BRREG registration date, activity, registered purpose, email, phone and mobile instead of discarding them during normalization;
- projected registration date, registered business address and registered contact fields with exact live source-field lineage;
- allowed registry narrative projection from exact-live `aktivitet` / `vedtektsfestetFormaal` with BRREG array cleanup;
- exposed registration date, registered address, registered purpose and registered contact fields in canonical company facts;
- added fail-closed exact-evidence, narrative-array, canonical and idempotence regressions.

Fresh 100-company results vs same-cohort baseline:

- company description: **100 vs 14**;
- registered purpose: **96 vs 0**;
- registration date: **100 vs 0**;
- registered address: **100 vs 0**;
- registered email: **21 vs 0**;
- phone: **17 vs 0**;
- mobile: **16 vs 0**;
- terminal outputs: 100/100;
- evidence audit: 100 rows, 0 errors;
- output-contract errors: 0;
- canonical errors: 0;
- synthesis errors: 0;
- logical requests: 669;
- conservative charge: 1,338/2,000;
- runtime: 449.589 s;
- third-party cost: $0;
- search requests: 0.

Decision:

- GO. This demonstrates that evaluator-visible recall can be increased materially with no new source and no request increase by recovering facts already present in exact official evidence.

Next:

- complete the remaining collected-vs-emitted and family-coverage audit on current main before choosing the next network/source feature.

---

## 2026-10-04 — C12 M4 current first-party jobs merged

Status: **MERGED + POST-MERGE GREEN**

- PR #90: `feat(c12): qualify current first-party job surfaces`
- branch: `feature/c12-current-first-party-jobs`
- qualified head: `c474be97e47ea19613b4301f027f1c03da86c858`
- merge commit / production main at time of entry: `fb4c8711b9a3c58c16c6ff1c26aada93c036938a`
- post-merge Baseline CI: run `37183602277`, PASS
- live proof run: `37183411443`
- proof artifact: `c12-m4-live-proof`, artifact ID `11295658686`
- proof digest: `b51f1ea151329ef3ad98f1c6f66ae09ced0b5d6aaa699e132312b580cac7fe4c`

What changed:

- explicit homepage vacancy-count signal can spend the bounded careers follow-up slot;
- generic careers page remains non-job evidence;
- company-owned role cards / `JobPosting` can produce concrete current jobs;
- specific role/application URL and exact employer context are required;
- expired roles abstain;
- parent targets do not inherit subsidiary jobs;
- C12 M3 news remains fallback when careers follow-up is not warranted;
- four-logical-site-request ceiling preserved;
- $0 third-party API spend preserved.

Live evidence:

- Granne `838797172`: vacancy count 0 -> no careers follow-up, no job claim.
- AF GRUPPEN ASA `938702675`: homepage vacancy count 31 -> bounded careers page -> current job claims within 4/4 site requests.

Decision:

- GO; merged after exact-head CI and live positive/negative proofs.

Next:

- stop feature-by-feature guessing;
- run current-main evaluator-shaped family-coverage and collected-vs-emitted audit before selecting the next recall feature.

---

## 2026-10-04 — 70+ continuity system introduced

Status: **DOCUMENTATION BRANCH**

Branch: `docs/70-plus-continuation-system`

Added:

- `docs/70_PLUS_IMPLEMENTATION_PLAN.md` — stable master roadmap toward 70+;
- `docs/CONTINUATION_STATE.md` — short living handoff state for every new chat;
- `docs/IMPLEMENTATION_LOG.md` — append-only milestone/experiment history.

Reason:

Conversation history had become a poor place to preserve critical implementation state. The repository is now explicitly the source of truth. Every substantial implementation session should update the living handoff before ending.

Next:

- merge this documentation system after review;
- future implementation chats read `CONTINUATION_STATE.md` + `70_PLUS_IMPLEMENTATION_PLAN.md` before touching code.
