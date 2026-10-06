# Q8 Fresh Qualification — 2026-10-06

## Decision

**GO.**

Signalpost V8 production commit `200f056a5a60cad23610a3958b6bec62dfb624a5` passed a genuinely fresh 100-company evaluator-shaped qualification after the Q8 precision fixes. The exact production commit is frozen at `release/v8-qualified-2026-10-06`.

Builderr still owns the official checked collection and score. This record is engineering qualification evidence, not a claimed official score.

## Freshness

- qualification workflow: `37403982422`
- qualification head: `93d3501fe5216f70f246c9ac97905bf2a1b14a4a`
- production SHA under qualification: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- seed: `20261107`
- prior touched exclusion: **8,723 companies**
- overlap: **0**
- exclusion SHA-256: `891773d05f4dd35b7ba8bc31d56c714df0c23d66ffeb868efe42dc84c5b65b0c`
- fresh cohort SHA-256: `444304a8ac88154efceb121b61efecfa6541b16b4682f9f6bd5dc8f0b7c44b1b`

Seeds `20261104`, `20261105`, `20261106` and `20261107` are all permanently consumed.

## Frozen artifact

- artifact ID: `11386579108`
- artifact: `q8-fresh-release-attempt4-100`
- artifact digest: `sha256:74401ccf2e1c11832bc91563ce02c8cb4ff040491542c563052049205a1b995e`

All hashes in the artifact's `out/q8-deliverables.sha256` were independently reverified after download.

## Machine gates

- 100 / 100 terminal outputs
- 4,600 / 4,600 available claims have complete core evidence
- 4,600 / 4,600 have reopenable source URLs
- 164 / 164 identity-sensitive claims expose identity proof
- 164 / 164 expose extraction method
- evidence visibility issues: 0
- final external precision guard idempotent: yes
- precision-guard residual removals: 0
- contract errors: 0
- canonical errors: 0
- synthesis errors: 0
- dangling evidence references: 0
- support projection errors: 0
- observed conservative request charge: 1,376 / 2,000
- theoretical conservative request ceiling: exactly 2,000
- wall runtime: 629.722 seconds / 2,400 seconds
- third-party API cost: $0.00
- search API requests: 0

## Manual precision audit

The external audit queue contained 20 evaluator-visible rows across five companies:

- 5 official websites
- 9 company-declared social profile handles
- 4 social-link aggregates
- 2 same-domain contact emails
- 0 careers/job/activity publications

Every external row retained a source URL, retrieval time, SHA-256, supporting span, identity proof and extraction method. No wrong-company, shared-owner, tenant/profile/listing, generic-CMS or future-date publication was found.

The support audit contained 42 rows across 12 companies:

- 42 / 42 unique source-row keys
- 42 / 42 recipient legal names exactly matched the target cohort company
- primary recipient organisation number exactly matched the target organisation
- all award dates were inside the configured 365-day window
- all rows used the official Brønnøysundregistrene Støtteregisteret source
- 0 manual integrity issues

## Precision history

Q8 attempt #2 (seed `20261105`) exposed one legacy activity-provenance omission and was consumed/NO-GO.

Q8 attempt #3 (seed `20261106`) passed machine gates but manual audit found five evaluator-visible false positives: a service-work careers false positive, two tenant-profile careers false positives, one future-dated tenant profile activity false positive and one default WordPress `Hei verden!` activity false positive. Those mechanisms were fixed, replayed with zero network, and merged in PR #123.

Attempt #4 is the first fresh cohort after those fixes and passed both machine and manual gates.

## Release boundary

Use exactly:

- release ref: `release/v8-qualified-2026-10-06`
- production SHA: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- evaluator: `scripts/run_signalpost_v8.py`

Do not substitute the qualification branch SHA. The qualification branch contains only harness files and was intentionally not merged into production.
