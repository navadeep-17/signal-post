# Signalpost Continuation State

Last updated: 2026-10-06

This is the authoritative short engineering handoff. Live GitHub remains authoritative if any SHA/run below advances.

## Repository / release state

- production branch: `main`
- freshly qualified production SHA: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- frozen evaluator release ref: `release/v8-qualified-2026-10-06`
- evaluator entry point: `scripts/run_signalpost_v8.py`
- PR #123 manual-precision fix: merged
- post-merge Baseline CI on production SHA: `37403437730` — **PASS**
- Q8 attempt #4 qualification PR #124: **closed, not merged**; qualification-only harness
- no official Builderr score is claimed for this revision yet

## Current stage

**Q8 is GO. Q9 release/submission finalization is active.**

The production path has now passed a genuinely fresh 100-company evaluator-shaped cohort after the evidence/provenance and manual-precision hardening work.

The immediate engineering task is no longer collector retuning. It is release packaging, repository-state synchronization and preparing the exact revision for the next Builderr evaluation.

## Fresh Q8 qualification — GO

Workflow run `37403982422`:

- qualification head: `93d3501fe5216f70f246c9ac97905bf2a1b14a4a`
- production SHA under qualification: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- seed: `20261107`
- all-touched exclusion: 8,723 companies
- overlap: 0
- fresh cohort: 100 companies
- exclusion SHA-256: `891773d05f4dd35b7ba8bc31d56c714df0c23d66ffeb868efe42dc84c5b65b0c`
- fresh cohort SHA-256: `444304a8ac88154efceb121b61efecfa6541b16b4682f9f6bd5dc8f0b7c44b1b`
- artifact ID: `11386579108`
- artifact digest: `sha256:74401ccf2e1c11832bc91563ce02c8cb4ff040491542c563052049205a1b995e`

Machine result:

- 100 / 100 terminal outputs
- 4,600 / 4,600 core evidence complete
- 4,600 / 4,600 reopenable
- 164 / 164 identity proof visible
- 164 / 164 extraction method visible
- evidence issues 0
- precision guard idempotent
- residual precision removals 0
- contract / canonical / synthesis / dangling-evidence / support-projection errors all 0
- observed request charge 1,376 / 2,000
- theoretical ceiling exactly 2,000
- runtime 629.722 s / 2,400 s
- third-party cost $0
- search API requests 0

Manual audit:

- 20 external rows across 5 companies: clean
- 42 support rows across 12 companies: clean
- 42 / 42 unique support source-row keys
- exact recipient organisation/name match for every support row
- no wrong-company, shared-owner, profile/listing, generic-CMS or future-date external publication found
- all frozen artifact hashes reverified

Decision: **Q8 GO**.

## Consumed fresh seeds

Never reuse these as fresh evidence:

- `20261104` — manual wrong-site-owner failure
- `20261105` — legacy activity provenance failure
- `20261106` — machine pass, manual five-false-positive failure
- `20261107` — successful final Q8 qualification

Any future fresh cohort must append the successful attempt-4 100 to the touched set before selection.

## Production changes now included

Since the old October 3 release, production now includes:

- Støtteregisteret exact primary-recipient support facts
- evaluator-visible identity/extraction provenance projection
- first-party RSS/Atom dated-activity path using spare verified-site request slots
- legacy activity provenance normalization
- explicit wrong-site-owner veto
- stricter careers nomination
- tenant/profile/listing rejection for news/careers fallback
- future publication-date rejection
- generic/default CMS post rejection
- final zero-network external precision guard
- newer social declaration identity hardening

Exact-company precision remains the primary invariant.

## Request theorem

For 100 companies:

1. V8 supplies 2,000.
2. V7 reserves one Støtteregisteret logical request = conservative charge 2.
3. V2 reserves one BRREG change-feed logical request = conservative charge 2.
4. The remaining base/annual-report allocation preserves the exact 2,000 conservative structural ceiling.

Do not add a request without re-proving this theorem.

## Q9 next actions

1. Keep `release/v8-qualified-2026-10-06` pinned to `200f056a…`.
2. Update submission/readme/requirements/qualification documentation to point to the qualified release.
3. Add a machine-readable qualification manifest for the Q8 artifact.
4. Require Baseline CI for documentation/release-state changes.
5. Do not alter production collector/evaluator semantics during Q9.
6. Prepare the exact release SHA/ref and evaluator command for Builderr revision submission.
7. After Builderr returns the new official score/category breakdown, optimize only the measured remaining gap.

## Historical / shelved work

- broad deterministic website guessing remains shelved
- search/model-assisted website nomination remains experiment-only
- homepage careers and public ATS/NAV paths did not justify weakening attribution
- historical policy-support data did not solve recent-activity recall
- old certified 1,000-company artifacts remain immutable historical compatibility evidence

See `docs/Q8_FRESH_QUALIFICATION_2026-10-06.md` for the final fresh qualification record.
