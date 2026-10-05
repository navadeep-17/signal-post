from pathlib import Path

LOG = Path('docs/IMPLEMENTATION_LOG.md')
PLAN = Path('docs/70_PLUS_IMPLEMENTATION_PLAN.md')

LOG_MARKER = '## 2026-10-05 — PR #97 exact-wrapper consumed qualification passes after report-counter fix'
LOG_ENTRY = '''

---

## 2026-10-05 — PR #97 exact-wrapper consumed qualification passes after report-counter fix

Status: **IMPLEMENTED + TESTED + CONSUMED-WRAPPER QUALIFIED / FINAL CLEAN-HEAD CI + MERGE GATE PENDING / NO FRESH COHORT**

- active PR: #97, `Phase 7: add exact-org Støtteregisteret support awards`;
- immutable V1/V2 boundary preserved: V1 blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`, V2 blob `5b69cc320c38e3aab13cf09fe2e2a09e62751433`;
- provenance-hardened Baseline CI `37257806967`: PASS;
- counter-fix/docs parent Baseline CI `37260229913`: PASS;
- first wrapper run `37257936472` remains FAIL because report accounting emitted 46 claims / 0 canonical facts despite 46 actual canonical facts; output/evidence audit itself had zero defects;
- report fix counts `canonical_field == public.official_support_award` and is regression-covered;
- definitive corrected V8 consumed run `37260381903`, job `111606171316`: PASS;
- qualification SHA `f47353a7f0b7eb63efa45a76c48850a7a648be2d`; production parent `22655265d3adc99bb2b73ef52d29caf6fa966d03`;
- artifact `phase7-v8-consumed-requalification-100-v2`, ID `11325335788`, ZIP digest `b60b0469ed31cc3b8651445dc786fd4ce34ad325044bebdd6572d5c261a85148`;
- cohort: already-consumed certified final-release-1000 chunk 0, 100 companies; no fresh cohort;
- 100/100 terminal; 11 support companies; 46 claims; 46 canonical facts; report 46/46;
- all 46 evidence rows audited: exact primary-recipient org, row hash, snapshot hash, row number/key, retrieval time, matching award/effective date, source-backed amount/interval currency; audit errors 0;
- support snapshot `8889b22ee01c7aaae1dd6a0c079977e00f4d390440ec0779f17d999dfbd951d1`;
- support requests 1; support bytes 305,978,976; BRREG change-feed requests 1;
- observed conservative charge 1,366/2,000; theoretical ceiling exactly 2,000/2,000;
- wrapper runtime 797.471 s/2,400; third-party cost $0; search API requests 0;
- contract/canonical/synthesis/support-projection errors 0;
- evaluator product 4,839,091 bytes and contains support facts/evidence;
- qualification-only workflow was removed after artifact capture.

Decision: **PROMOTE through final repository gate**. Verify clean durable diff, run final exact-head Baseline CI after docs/cleanup, merge with expected-head protection, require post-merge Baseline CI, then advance to Phase 11 fresh evaluator-shaped release qualification. Do not submit Builderr solely because this PR merges.
'''

log = LOG.read_text(encoding='utf-8')
if LOG_MARKER not in log:
    LOG.write_text(log.rstrip() + LOG_ENTRY + '\n', encoding='utf-8')

plan = PLAN.read_text(encoding='utf-8')
plan = plan.replace(
    '- **Phase 7 — Dated activity:** **ACTIVE PROMOTION** — Støtteregisteret support-award semantics consumed-qualified; PR #97 wrapper retune requires exact-head CI + consumed V8 requalification before merge.',
    '- **Phase 7 — Dated activity:** **CONSUMED-WRAPPER QUALIFIED / MERGE GATE** — Støtteregisteret exact-wrapper V8 qualification is green; final clean-head CI + merge/post-merge CI remain.',
)
plan = plan.replace(
    '> finish PR #97 exact-head CI -> exact-head consumed V8 wrapper requalification -> merge/post-merge CI -> Phase 11 fresh release qualification.',
    '> verify final PR #97 durable diff -> final exact-head Baseline CI -> merge/post-merge CI -> Phase 11 fresh release qualification.',
)
old_next = '**Finish PR #97 on the corrected wrapper architecture: require exact-head Baseline CI, then an exact-head actual-V8 consumed requalification and manual support-fact audit. Merge only after both are green, run post-merge CI, then advance to Phase 11 with a genuinely fresh evaluator-shaped cohort.**'
new_next = '**PR #97 is exact-wrapper consumed-qualified. Verify the final durable diff, require one final exact-head Baseline CI after qualification-workflow cleanup/docs, merge with expected-head protection, require post-merge Baseline CI, then advance to Phase 11 with a genuinely fresh evaluator-shaped cohort.**'
plan = plan.replace(old_next, new_next)

SUCCESS_MARKER = '### 2026-10-05 PR #97 exact-wrapper consumed qualification PASS'
if SUCCESS_MARKER not in plan:
    plan = plan.rstrip() + '''

### 2026-10-05 PR #97 exact-wrapper consumed qualification PASS

The corrected final V7 wrapper path is now consumed-qualified. Baseline CI `37260229913` passed on production parent `22655265d3adc99bb2b73ef52d29caf6fa966d03`, then actual-V8 consumed qualification `37260381903` / job `111606171316` passed on qualification SHA `f47353a7f0b7eb63efa45a76c48850a7a648be2d` with only a temporary workflow above the production parent.

Artifact `11325335788` (`phase7-v8-consumed-requalification-100-v2`, ZIP SHA-256 `b60b0469ed31cc3b8651445dc786fd4ce34ad325044bebdd6572d5c261a85148`) proves 100/100 terminal companies, 11 support companies, 46 support claims = 46 canonical facts, zero contract/canonical/synthesis/support-projection failures, one support request, one BRREG change-feed request, 1,366 observed conservative charge, exactly 2,000 theoretical conservative requests, 797.471 s wrapper runtime, $0 third-party cost and zero search API requests. All 46 support evidence rows were audited with exact primary-recipient identity plus row/snapshot provenance; audit errors were zero.

The earlier run `37257936472` remains recorded as a failed gate because its report incorrectly counted canonical facts as 0 despite 46 materialized facts. That report-only defect is fixed and regression-covered; failures are not rewritten into successes.

Roadmap consequence: Phase 7 source + wrapper qualification is complete. Remaining work is repository hygiene/final exact-head CI, merge/post-merge verification, then Phase 11 fresh evaluator-shaped release qualification. No Builderr revision is authorized merely by the Phase-7 merge.
'''

PLAN.write_text(plan.rstrip() + '\n', encoding='utf-8')
