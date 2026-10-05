from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs" / "IMPLEMENTATION_LOG.md"
PLAN = ROOT / "docs" / "70_PLUS_IMPLEMENTATION_PLAN.md"

LOG_MARKER = "## 2026-10-05 — PR #97 CI catches immutable-V1 violation; support moved to V7 wrapper"
LOG_ENTRY = r'''

---

## 2026-10-05 — PR #97 CI catches immutable-V1 violation; support moved to V7 wrapper

Status: **RETUNED / EXACT-HEAD CI + CONSUMED V8 WRAPPER REQUALIFICATION PENDING / NOT MERGED**

- active PR: #97, `Phase 7: add exact-org Støtteregisteret support awards`;
- first exact-PR Baseline CI: run `37255960174`, job `111592968992`: **FAIL**;
- pytest result: **459 passed, 1 failed, 5 subtests passed**;
- sole failure: `tests/test_submission_bundle.py::test_repository_only_submission_verifier_passes`;
- failure cause: the first promotion shape modified `scripts/run_signalpost_final.py`, violating the immutable certified V1 collector pin;
- certified V1/V2 audit stages after pytest were skipped; no merge occurred;
- the verifier/pin was **not** weakened or repinned.

Architecture correction:

- certified V1 `scripts/run_signalpost_final.py` restored exactly to blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`;
- current V2 `scripts/run_signalpost_v2.py` remains unchanged at blob `5b69cc320c38e3aab13cf09fe2e2a09e62751433`;
- Støtteregisteret moved to the newer V7 wrapper layer;
- V7 now reserves the one shared support request, invokes unchanged V2 with the reduced budget, then projects support claims, canonical facts and synthesis before building the V6 evaluator surface;
- support-specific CLI flags terminate at V7 and cannot leak into pinned V2/V1;
- wrapper/budget tests were rewritten around this boundary;
- code/test retune head before documentation commits: `338730d3ddf562955c967468983bd8cb3f0cc590`.

Corrected 100-company request theorem:

- V8 -> V7 budget: 2,000 conservative;
- V7 reserves Støtte: 1 logical / charge 2 -> V2 receives 1,998;
- V2 reserves BRREG change feed: 1 logical / charge 2 -> V1 receives 1,996;
- immutable V1 fixed company + Wikidata ceiling: 901 logical;
- H2g annual-report capacity: 97 logical;
- V1 theoretical total: 998 logical / 1,996 conservative;
- + change feed: 999 / 1,998;
- + Støtte: **1,000 logical / exactly 2,000 conservative**.

The prior consumed actual-V8 run `37254237936` / artifact `11321344340` remains valid semantic/evidence proof for primary-recipient-only Støtte publication and its 46 manually audited claims. Because the integration layer changed, it does **not** substitute for an exact-head wrapper requalification.

Decision: keep PR #97 blocked until the retuned exact head passes full Baseline CI **and** an actual-V8 consumed requalification. Then merge with expected-head protection, run post-merge CI, pin production state, and only then advance to Phase 11 fresh evaluator-shaped release qualification.
'''

log = LOG.read_text(encoding="utf-8")
if LOG_MARKER not in log:
    LOG.write_text(log.rstrip() + LOG_ENTRY + "\n", encoding="utf-8")

plan = PLAN.read_text(encoding="utf-8")
plan = plan.replace("Last updated: 2026-10-04", "Last updated: 2026-10-05", 1)
plan = plan.replace(
    "- **Phase 7 — Dated activity:** production C12 M3 foundation remains; Phase-3 RSS/sitemap expansion did not transfer.",
    "- **Phase 7 — Dated activity:** **ACTIVE PROMOTION** — Støtteregisteret support-award semantics consumed-qualified; PR #97 wrapper retune requires exact-head CI + consumed V8 requalification before merge.",
)
plan = plan.replace(
    "> consumed-only rights/reach/exact-ID source-selection audit -> choose one deterministic high-yield family/source if justified -> Phase 10 allocation if needed -> Phase 11 fresh release qualification.",
    "> finish PR #97 exact-head CI -> exact-head consumed V8 wrapper requalification -> merge/post-merge CI -> Phase 11 fresh release qualification.",
)
old_next = "**Run a consumed-only deterministic source/family selection audit. Screen rights, exact-ID join quality, likely evaluator-shaped reach and request/runtime budget for Doffin, Støtteregisteret, Patentstyret or another official source before implementing a connector. No fresh cohort yet.**"
new_next = "**Finish PR #97 on the corrected wrapper architecture: require exact-head Baseline CI, then an exact-head actual-V8 consumed requalification and manual support-fact audit. Merge only after both are green, run post-merge CI, then advance to Phase 11 with a genuinely fresh evaluator-shaped cohort.**"
plan = plan.replace(old_next, new_next)

CORRECTION_MARKER = "### 2026-10-05 PR #97 immutable-layer correction"
if CORRECTION_MARKER not in plan:
    plan = plan.rstrip() + r'''

### 2026-10-05 PR #97 immutable-layer correction

The first clean promotion shape modified the certified V1 collector. Baseline CI run `37255960174` correctly blocked it: 459 tests passed and the repository-only submission verifier was the sole failure because `scripts/run_signalpost_final.py` drifted from its immutable blob.

The production architecture is therefore corrected, not repinned: V1 is restored byte-for-byte (`9be89b9827135b1ed703318e1d189d5d3b8ca604`), V2 remains unchanged (`5b69cc320c38e3aab13cf09fe2e2a09e62751433`), and Støtteregisteret lives in V7. V7 reserves one shared support request before invoking V2, V2 reserves its existing BRREG change-feed request before invoking V1, and the 100-company theorem remains 1,000 logical / exactly 2,000 conservative requests with 97 H2g slots.

The earlier consumed V8 artifact `11321344340` remains the semantic/evidence proof for primary-recipient-only support publication, but the wrapper relocation requires a new exact-head consumed V8 requalification before PR #97 can merge. Phase 11 remains the next fresh-cohort gate after merge + post-merge CI.
'''

PLAN.write_text(plan.rstrip() + "\n", encoding="utf-8")
