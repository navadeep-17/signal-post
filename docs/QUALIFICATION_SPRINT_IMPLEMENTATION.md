# Signalpost Qualification Sprint — Final Status

Last updated: 2026-10-06

## Objective

Raise the next Builderr revision above the 65/100 qualification line without weakening exact-company precision.

Guiding rule:

> ATTEMPT MORE -> VERIFY STRICTLY -> PUBLISH CONSERVATIVELY

## Final milestone status

- **Q0 precision safety closure — COMPLETE.** Explicit wrong-site-owner publication is vetoed.
- **Q1 evaluator-visible evidence audit — COMPLETE.** Core evidence was already complete; hidden provenance was identified.
- **Q2 evidence projection hardening — COMPLETE / MERGED.** Identity proof and extraction method are visible without new requests.
- **Q3 website reach recovery — SCREENED / HOLD.** Search-assisted nomination did not justify production promotion.
- **Q4 social/contact — COMPLETE AS MEASUREMENT.** Conditional extraction works; verified-site reach remains the upstream limiter.
- **Q5 hiring — MEASURED NEGATIVE.** Homepage/ATS/NAV exact-org paths did not justify weaker attribution.
- **Q6 dated first-party activity — COMPLETE / MERGED.** A bounded RSS/Atom spare-slot path transferred; later precision guards reject profile/listing/future/default-CMS false positives.
- **Q7 consumed/dev transfer — COMPLETE / GO.** Qualified bundle added evidence/provenance/activity value without regressions.
- **Q8 fresh qualification — COMPLETE / GO.** Final successful fresh seed `20261107`.
- **Q9 Builderr revision — ACTIVE.** Freeze release, synchronize submission docs, then submit the exact qualified revision.

## Q8 final fresh result

Production under qualification: `200f056a5a60cad23610a3958b6bec62dfb624a5`.

Workflow `37403982422`:

- exclusion: 8,723 prior touched companies
- fresh cohort: 100
- overlap: 0
- terminal: 100 / 100
- evidence complete/reopenable: 4,600 / 4,600
- identity proof: 164 / 164
- extraction method: 164 / 164
- precision guard residuals: 0
- all contract/canonical/synthesis/evidence/support integrity errors: 0
- requests: 1,376 / 2,000 observed; 2,000 theoretical ceiling
- runtime: 629.722 s
- third-party cost: $0
- search API requests: 0
- external manual audit: 20 rows, 0 issues
- support manual audit: 42 rows, 0 issues

Artifact: `11386579108`, digest `sha256:74401ccf2e1c11832bc91563ce02c8cb4ff040491542c563052049205a1b995e`.

Decision: **GO**.

## Consumed seeds

Do not reuse:

- `20261104`
- `20261105`
- `20261106`
- `20261107`

## Q9 release boundary

Use exactly:

- release ref: `release/v8-qualified-2026-10-06`
- production SHA: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- evaluator: `scripts/run_signalpost_v8.py`

Q9 must not change collector/evaluator semantics. Documentation/release-state changes require Baseline CI.

## After Builderr

Do not pre-optimize blindly. Once Builderr returns the new official category breakdown:

- preserve 0 known material wrong-company publications;
- keep evidence/synthesis/UX regressions at zero;
- target only the measured official recall/evidence gap;
- reopen experimental source families only with explicit transfer, rights and request-budget proof.
