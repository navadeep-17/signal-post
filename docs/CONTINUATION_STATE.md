# Signalpost Continuation State

Last updated: 2026-10-06

This file is the authoritative short handoff for the next implementation session. Live GitHub remains authoritative if any SHA/run below has advanced.

## Repository state

- production branch: `main`
- current qualified production SHA: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- post-merge Baseline CI: `37403437730` — **PASS**
- evaluator entry point: `scripts/run_signalpost_v8.py`
- certified V1 immutability remains preserved
- third-party API cost remains **$0**
- search API calls remain **0**
- PR #124 (Q8 attempt #4 qualification harness) is **closed without merge**
- working finalization branch: `docs/q8-release-finalization`

## Active stage

The main engineering/qualification track is **CLOSED / RELEASE-QUALIFIED**.

Q8 fresh release qualification attempt #4 passed both the machine gate and manual precision gate. No further source experiment or fresh cohort should be started before the release decision.

Current task: **release bookkeeping -> exact-head CI -> freeze release ref -> Builderr submission**.

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

1. Finish documentation-only release finalization on `docs/q8-release-finalization`.
2. Open a documentation-only PR against `main`.
3. Require exact-head Baseline CI.
4. Merge only if the diff remains documentation-only and CI is green.
5. Require post-merge Baseline CI on the final `main`.
6. Freeze a release ref for that exact final production revision.
7. Submit the frozen revision to Builderr.
8. After submission, record the submitted SHA/ref and official Builderr result separately.

No further feature work is on the critical path before submission.
