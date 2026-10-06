# Signalpost Continuation State

Last updated: 2026-10-06

This file is the authoritative short handoff for the next implementation session. Live GitHub remains authoritative if any SHA/run below has advanced.

## Repository state

- engineering: **CLOSED**
- qualification: **GO / RELEASE-QUALIFIED**
- release finalization: **COMPLETE pending only final docs-cleanup merge/ref move described by the current release PR**
- qualified production SHA: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- qualified code ref: `release/v8-qualified-2026-10-06`
- final submission ref: `release/v8-submission-2026-10-06`
- evaluator entry point: `scripts/run_signalpost_v8.py`
- latest pre-cleanup main Baseline CI: `37407690443` — **PASS**
- certified V1 immutability remains preserved
- third-party API cost remains **$0**
- search API calls remain **0**
- PR #124 (Q8 attempt #4 qualification harness) is **closed without merge**
- official Builderr score for the newly qualified revision: **OPEN**

The latest official Builderr result for the previously evaluated revision is **49.99/100** (Recall 8.99/50, Precision and evidence 21.00/30, Synthesis 12.00/12, UX 8.00/8). The older public-board snapshot may still show **52.41/100**. Qualification requires **65/100 overall** on an official Builderr run; local Q8 GO is not an official Builderr score.

## Active stage

The engineering and fresh-qualification tracks are closed. No feature/source experiment or fresh cohort is on the submission critical path.

Current task: **submit the exact frozen `release/v8-submission-2026-10-06` revision to Builderr after its final post-merge Baseline CI is green, then record the official result.**

## Q8 attempt #4 — release qualification PASS

Freshness:

- prior exclusions: **8,723**
- seed: `20261107`
- fresh companies: **100**
- prior-overlap: **0**
- fresh cohort SHA-256: `444304a8ac88154efceb121b61efecfa6541b16b4682f9f6bd5dc8f0b7c44b1b`
- seed `20261107` is permanently consumed

Execution:

- workflow: `37403982422` — **SUCCESS**
- exact qualification head: `93d3501fe5216f70f246c9ac97905bf2a1b14a4a`
- exact-head Baseline CI: `37403985583` — **PASS**
- artifact ID: `11386579108`
- artifact ZIP SHA-256: `74401ccf2e1c11832bc91563ce02c8cb4ff040491542c563052049205a1b995e`

Machine result:

- 100/100 terminal outputs
- 4,600/4,600 core evidence complete
- 4,600/4,600 reopenable sources
- 164/164 identity-sensitive claims with identity proof
- 164/164 with extraction method
- 0 evidence-visibility issues
- precision guard idempotent, 0 residual removals
- 42 support claims across 12 companies
- 1,376/2,000 observed conservative request charge
- 629.722 s wall runtime
- $0 third-party API cost
- 0 contract/canonical/synthesis/dangling-evidence/support-projection errors

Manual precision result:

- 20/20 evaluator-visible external publications manually reviewed
- 42/42 Støtteregisteret support rows reviewed
- wrong-company publications: **0**
- support audit anomalies: **0**

Decision: **GO / RELEASE-QUALIFIED**.

See `docs/Q8_RELEASE_QUALIFICATION.md` for the frozen qualification record.

## Production boundary

Do not:

- merge PR #124;
- reuse seed `20261107` as fresh evidence;
- consume another fresh cohort before release;
- add a new source or production behavior before the release decision;
- weaken exact-company identity/evidence gates.

R&D branches such as model/search website discovery, NAV variants, Common Crawl, OSM/Norid investigations, and other source screens remain outside the release path unless separately requalified later.

## NEXT

1. Submit the exact SHA referenced by `release/v8-submission-2026-10-06` to Builderr.
2. After submission/evaluation, record the actual submitted SHA/ref and official Builderr result separately.
3. Use the official category breakdown to choose any later engineering work.

No further feature work, source addition, experimental merge or fresh cohort is on the critical path before submission.
