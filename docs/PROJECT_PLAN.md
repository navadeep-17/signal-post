# Signalpost project plan

Status: Phase 0 baseline established on 2026-09-13.

## Source-of-truth order

When sources disagree, use them in this order:

1. Current live challenge page: <https://www.builderr.ai/challenges/signalpost>
2. This starter kit's `README.md` and `OUTPUT_CONTRACT.md`
3. Automated tests and frozen fixtures in this repository
4. Starter documentation under `docs/`
5. Sample product at <https://www.builderr.ai/signalpost>
6. Our own measured hypotheses and design ideas

Older indexed Builderr pages that describe Signalpost as a listed-equities/investment-research challenge are stale for this repository and must not drive implementation.

## What we are building

A reusable company-research agent that accepts a Norwegian organisation number, resolves the exact legal entity, finds and verifies permitted public sources, produces source-backed company intelligence, preserves honest missing states, and refreshes profiles without losing history or creating duplicate/false changes.

The UI and research assistant sit on top of the evidence engine. They are not the primary system.

## Current official competition constraints

As verified from the live challenge page on 2026-09-13:

- Public universe: 411,160 eligible companies in the frozen 2025-filer universe.
- Public entry: at least 1,000 completed company profiles plus the exact organisation-number manifest.
- Daily technical evaluation: 100 random companies using the same batch for every frozen agent.
- Runtime: 45 minutes on 8 vCPU, 16 GB RAM, 10 GB temporary disk.
- Requests: maximum 2,000 outbound requests per 100-company batch; redirects/retries count, cache hits are free.
- Third-party spend: maximum $10 per 100-company batch; Builderr-supplied official snapshots do not count.
- Revisions: up to four new commit hashes before October 18.
- Scoring: coverage/source discovery 35, accuracy/identity/evidence 30, refresh/extensibility 20, synthesis 10, UX 5.
- Qualification: at least 65/100, 21/35 coverage, 60% weighted external company recall, and 95% external precision, plus all hard gates.
- Hard gates include exactly 100 terminal outputs, no fabricated financials, claim-level provenance, distinct missing/blocked/not-applicable states, idempotent refresh/history, documented source rights, server-side secrets, and safe URL handling.

The local scorer in this starter is only a development proxy. It must never replace the official scoring contract.

## Development rules

1. Keep `main` stable. One bounded hypothesis per feature branch/PR.
2. Add the regression that catches the most dangerous failure before or with the implementation.
3. Measure before/after on the same development corpus.
4. Validate promoted changes on a zero-overlap validation corpus.
5. Never lower exact-entity safety merely to increase coverage.
6. Search/API results nominate candidates; they do not prove identity by themselves.
7. An external connector is not publishable until its acquisition rights and evidence path are documented.
8. Never use an LLM to invent or choose authoritative financial values.
9. Never tune on the held-out corpus.
10. Never edit a scorer just to make a feature look better.
11. Every meaningful PR reports coverage, precision/errors, requests, runtime and cost impact.
12. If a requirement is ambiguous, record it instead of silently guessing.

## Corpus strategy

Use increasingly expensive frozen slices:

- 10 companies: smoke/reproducibility only.
- 100 companies: normal development benchmark and failure buckets.
- Separate 100-company zero-overlap slice: promotion check for connector/identity changes.
- 600 development / 200 validation / 200 held-out: use the starter's 1,000-company split for larger experiments.
- 1,000+ companies: release candidate and submission artifact.

The held-out set is for release audit only, not iterative tuning.

## Milestones

### Phase 0 — Baseline and reproducibility (Sep 13–15)

- Preserve untouched starter commit/branch.
- Add CI with locked dependency sync, full tests and deterministic refresh replay.
- Run live 10-company smoke from the published universe.
- Record exact baseline behavior and contract gaps.
- Create requirements/decisions/connector-status documentation.

Exit: offline CI green, live smoke green, no feature code changed.

### Phase 1 — 100-company baseline and failure map (Sep 16–18)

- Run a frozen 100-company development batch.
- Produce module availability, website/identity buckets, request/runtime distribution and evidence/terminal-state report.
- Confirm final-output contract adaptation requirements.
- Rank the largest recoverable coverage losses.

Exit: the next feature is chosen from measured failure buckets, not intuition.

### Phase 2 — Company-site intelligence (Sep 19–24)

Likely candidates, only where Phase 1 confirms value:

- richer exact-entity corroboration without weakening thresholds;
- targeted careers/jobs pages;
- legal/contact/footer identity evidence;
- company-owned activity/news;
- verified social cross-links;
- selective JS fallback when deterministic completeness checks fail.

Exit: measurable supported coverage gain with no wrong-company regression on development and validation slices.

### Phase 3 — First qualified external connector (Sep 25–30)

Choose from measured gaps. Default candidate is an official Google Places path because the starter already contains normalization/matching experiments, but this is not pre-committed.

Exit: documented rights/acquisition mode, frozen audit, high exact-entity precision, supported evidence and positive validation-set gain.

### Phase 4 — Second external improvement (Oct 1–5)

Choose the highest measured return among permitted search/domain discovery, company jobs, official YouTube API, or licensed news/activity.

Exit: gain transfers to zero-overlap validation without weakening identity/evidence gates.

### Phase 5 — Integrate external evidence (Oct 6–9)

- Feed only qualified observations into refresh/snapshots.
- Extend evidence-bounded research/Q&A.
- Preserve abstention when evidence is absent.

Exit: repeatable refresh + cited research answers over both official and qualified external evidence.

### Phase 6 — Competition runner and resource control (Oct 10–12)

- Expose one end-to-end evaluator command.
- Implement/verify final output-contract adapter.
- Add global request/cost accounting and safe connector budgeting.
- Run locked 100-company test under official limits.

Exit: 100 terminal outputs, <45 min, <2,000 requests, <$10 declared third-party spend, with headroom.

### Phase 7 — Product and release candidate (Oct 13–15)

- Improve the provided static prototype only where useful.
- Make sources, gaps, changes and research answers easy to inspect.
- Generate 1,000+ completed profiles and exact manifest.
- Finalize model/API/licence/source-rights/cost documentation.

Exit: complete submission candidate.

### Phase 8 — Freeze (Oct 16–17)

- Run held-out/extension audit.
- Full regression suite.
- Freeze exact commit SHA and manifest.
- No speculative feature work.

October 18 is reserved for a proven serious correction, not normal development.

## Phase 0 measured baseline

The untouched 10-company live runner completed successfully on GitHub Actions:

- 10/10 terminal internal envelopes emitted.
- Built-in batch validation passed, including unique organisation numbers and zero silent drops.
- 56 research requests total.
- Request latency: p50 682 ms, p95 750 ms.
- Core company research completed in about 26 seconds once input snapshots were available.
- The official BRREG bulk snapshot download was about 148 MB and dominated CI wall time; do not confuse that download time with per-company research runtime.
- In this tiny smoke slice, financials/roles/locations were available for all 10, while only 1/10 had a registry-listed website. This is a signal only; Phase 1 must verify prevalence on 100 companies before prioritizing missing-site discovery.

## Confirmed contract gap

`OUTPUT_CONTRACT.md` documents the intended final claims/evidence envelope (`run.terminal_status`, `claims`, `evidence`, `changes`, `errors`, `operations.third_party_cost_usd`). The current `scripts/run_competition_batch.py` instead emits the starter's internal envelope (`state`, per-module terminal states, embedded `profile`). Repository search found no hidden adapter implementing the documented final fields.

Do not patch this ad hoc. Phase 1 must define a tested adapter/mapping from internal evidence/profile data to the final submission contract while preserving the existing runner diagnostics.

## Explicit non-goals for early phases

Do not rewrite the starter, build a new React/Next frontend, add a complex multi-agent framework, train an ML model just to look "AI", make experimental LinkedIn/Indeed/Glassdoor scraping a foundation, or prioritize sentiment before core coverage/identity/evidence are strong.
