# Signalpost Implementation Log

This is the append-only project history used for cross-chat continuity.

Rules:

- Add an entry only for material work: experiments, qualified milestones, merges, important failures, scoring feedback or roadmap changes.
- Keep entries factual and short.
- Record exact branch/PR/SHA/run IDs where known.
- Never rewrite old failures into successes; preserve why a path was rejected.
- Current actionable state belongs in `docs/CONTINUATION_STATE.md`.

---

## 2026-10-04 — C12 M4 current first-party jobs merged

Status: **MERGED + POST-MERGE GREEN**

- PR #90: `feat(c12): qualify current first-party job surfaces`
- branch: `feature/c12-current-first-party-jobs`
- qualified head: `c474be97e47ea19613b4301f027f1c03da86c858`
- merge commit / current production main at time of entry: `fb4c8711b9a3c58c16c6ff1c26aada93c036938a`
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
