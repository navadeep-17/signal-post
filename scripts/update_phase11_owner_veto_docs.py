from pathlib import Path

LOG = Path('docs/IMPLEMENTATION_LOG.md')
PLAN = Path('docs/70_PLUS_IMPLEMENTATION_PLAN.md')

log_marker = '## 2026-10-05 — Phase 11 seed 20261104 manual precision FAIL -> explicit website-owner veto RETUNE'
log_entry = r'''

---

## 2026-10-05 — Phase 11 seed 20261104 manual precision FAIL -> explicit website-owner veto RETUNE

Status: **FRESH MACHINE PASS / MANUAL PRECISION FAIL / RETUNE IMPLEMENTED + TESTED / CONSUMED REPLAY MONOTONIC / PR #99 MERGE GATE**

Fresh Phase 11 run `37309340028` used seed `20261104` after reconstructing an 8,423-company all-touched exclusion. Selection overlap was 0; exclusion SHA-256 was `fd1e5c7e54d6034821553a1903fd20bea76738dcf0d5e0c75eec93b4a724a298`; cohort SHA-256 was `394eaae1b43fbe5e951fc4a61c7185c068bfa6dad1d37a7223cefc507429dd99`; artifact ID `11346320812`, ZIP SHA-256 `9c9ab8bb8477c949a9491f7a672ad181f43566cd9b885a1f4fc6a2dd720165cf`.

Machine gates passed: 100/100 terminal; 11 support companies; 48 support claims = 48 canonical facts; 1 support request; 1 BRREG change-feed request; observed conservative charge 1,364/2,000; theoretical ceiling exactly 2,000; wall runtime 804.632 s; third-party API cost $0; search API requests 0; contract/canonical/synthesis/dangling-evidence/support-projection errors 0. The artifact correctly left `release_qualified=false` pending manual precision audit.

Manual audit found one material exact-company failure: target `INTERIØRKUPP AS` (`825188592`) was assigned guessed domain `interiorkupp.no`, while the fetched site explicitly states that the site is owned by `Rolf Sletvold Interiørsenter AS`, a different legal entity. Four external publications were contaminated: website, Instagram handle, social-links aggregate and `post@interiorkupp.no`. Decision for seed `20261104`: **FAIL / RETUNE / NO RELEASE**. The cohort is permanently consumed.

PR #99 implements a generic source-agnostic website-owner veto in `identity.py`: an explicit statement that the current fetched domain/site is owned by another named legal entity is hard negative identity evidence. There is no company/domain blacklist. Same-target owner statements pass; unrelated ownership text for another domain does not trigger the veto; exact target organisation-number proof remains stronger positive evidence. Adversarial regressions cover the discovered failure plus same-target and unrelated-owner controls.

Baseline CI `37314026333` passed on code/test head `532bb93f0c02b6da608bd070c7fa36349b5d8cfc`; Baseline CI `37314406825` also passed on replay-checksum head `a7e622a89fbde026205e544473e25d6efbfa67d2`.

Consumed-only replay `37314396820` / job `111777368735` ran the actual V8 path on the already-consumed seed-20261104 cohort. V8 itself passed. The workflow's final verifier failed only because it expected the observed owner string to equal exactly `Rolf Sletvold Interiørsenter AS`; the extractor retained trailing source prose. Replay artifact ID `11347753450`, ZIP SHA-256 `ff03b78a41372f368ace904a009e82eda5c42fd5aa3d74d37a91ccaee0684e01`, independently proves the production behavior is correct: target website unpublished, identity score 0.1, `publishable=false`, wrong-owner reason retained, old external audit 25 records -> replay 21 non-empty publications, exact set diff **4 removed / 0 added**, with the four removed records exactly the contaminated Interiørkupp website/social/email claims. Every other previously published external value is unchanged.

Decision: **PROMOTE THE PRECISION FIX through final clean PR CI/merge/post-merge CI, then rerun Phase 11 on a new untouched cohort.** The next all-touched exclusion must include the failed fresh 100, so the exclusion cardinality becomes 8,523 before seed `20261105` (or the next deterministic seed if repository state advances). Do not reuse seed `20261104` as fresh evidence and do not submit Builderr before a new fresh cohort passes machine + manual precision gates.
'''

log = LOG.read_text(encoding='utf-8')
if log_marker not in log:
    LOG.write_text(log.rstrip() + log_entry + '\n', encoding='utf-8')

plan = PLAN.read_text(encoding='utf-8')
plan = plan.replace(
    '- **Phase 11 — Fresh validation/release candidate:** **ACTIVE** — next main-track gate on a genuinely fresh disjoint 100-company cohort.',
    '- **Phase 11 — Fresh validation/release candidate:** **ACTIVE / RETUNE** — seed `20261104` passed machine gates but failed manual exact-company audit; PR #99 owner-veto precision fix is in merge qualification before a new fresh cohort.',
)
plan = plan.replace(
    '> Phase 11 fresh disjoint cohort -> actual V8 release qualification -> audit + exact artifact freeze -> Builderr release decision.',
    '> finish PR #99 owner-veto merge gate -> exclude 8,523 touched companies -> new fresh Phase 11 cohort -> actual V8 machine + manual precision qualification -> artifact freeze -> Builderr release decision.',
)
old_next = '**Phase 7 is merged and post-merge green. Execute Phase 11 on a genuinely fresh, disjoint evaluator-shaped 100-company cohort; require a clean actual-V8 release gate, manual support/external precision audit, exact SHA/artifact freeze and only then make the next Builderr release decision.**'
new_next = '**Phase 11 seed `20261104` is permanently consumed and failed manual precision audit despite green machine gates. Finish PR #99 exact-site-owner precision hardening through final clean-head CI, merge and post-merge CI; then construct an 8,523-company all-touched exclusion and run a genuinely new fresh cohort (planned seed `20261105`). Require both machine and manual precision gates before any Builderr release decision.**'
plan = plan.replace(old_next, new_next)

marker = '### 2026-10-05 Phase 11 fresh gate FAIL -> owner-veto retune'
if marker not in plan:
    plan = plan.rstrip() + r'''

### 2026-10-05 Phase 11 fresh gate FAIL -> owner-veto retune

Seed `20261104` was genuinely fresh against 8,423 previously touched companies and passed the complete V8 machine gate, but manual external precision audit found one wrong-company guessed site. `INTERIØRKUPP AS` (`825188592`) was assigned `interiorkupp.no` even though the page explicitly names `Rolf Sletvold Interiørsenter AS` as the site owner. Four derived external facts were therefore invalid. This is a release-blocking precision failure even though contract/canonical/runtime/request checks were green.

The retune is generic: explicit current-site ownership by a different named legal entity is now a hard identity veto. No blacklist was added. Full Baseline CI passed, and consumed-only replay of the failed cohort is monotonic: exactly the four contaminated Interiørkupp records disappear, zero new external records are added, every other prior published external value is unchanged, and the target candidate is retained only as quarantined evidence with `publishable=false`.

Roadmap consequence: Phase 11 remains active but is not release-qualified. Merge the precision fix only after a final clean durable diff + exact-head Baseline CI and post-merge CI. Then permanently include the failed 100 in the touched set (8,523 total exclusions) and spend a new fresh cohort. The failed seed must never be reused as qualification evidence.
'''

PLAN.write_text(plan.rstrip() + '\n', encoding='utf-8')
