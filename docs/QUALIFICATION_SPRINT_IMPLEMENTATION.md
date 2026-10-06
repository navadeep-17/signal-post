# Signalpost Qualification Sprint — Final Status

Last updated: 2026-10-06

## Objective

Raise the next Builderr revision above the qualification line without weakening exact-company precision.

Guiding rule:

> ATTEMPT MORE -> VERIFY STRICTLY -> PUBLISH CONSERVATIVELY

## Milestone status

- **Q0 — precision safety closure: COMPLETE.** Explicit wrong-site-owner publications are vetoed.
- **Q1 — evaluator-visible evidence audit: COMPLETE.** Core evidence was complete; hidden provenance was identified.
- **Q2 — evidence projection hardening: COMPLETE / MERGED.** Identity proof and extraction method are evaluator-visible with zero new requests.
- **Q3 — website reach recovery: SCREENED / HOLD.** Search-assisted nomination did not justify production promotion.
- **Q4 — social/contact: MEASUREMENT COMPLETE.** Extraction works conditionally on an exact verified site; site reach remains the upstream limiter.
- **Q5 — hiring: MEASURED NEGATIVE.** Homepage, ATS and NAV exact-org paths did not justify weaker attribution.
- **Q6 — dated first-party activity: COMPLETE / MERGED.** Bounded RSS/Atom spare-slot path transferred, followed by precision hardening for profile/listing/future/default-CMS cases.
- **Q7 — consumed/dev transfer: COMPLETE / GO.** Bundle improved evidence/provenance/activity without known precision regression.
- **Q8 — fresh qualification: COMPLETE / GO.** Final fresh seed `20261107` passed machine and manual gates.
- **Q9 — Builderr revision: ACTIVE.** Repository/release state is being frozen for the exact next submission.

## Q8 final result

Production code under qualification: `200f056a5a60cad23610a3958b6bec62dfb624a5`.

Workflow `37403982422`:

- prior exclusion: 8,723 companies
- fresh cohort: 100
- overlap: 0
- terminal: 100 / 100
- evidence complete/reopenable: 4,600 / 4,600
- identity proof: 164 / 164
- extraction method: 164 / 164
- evidence issues: 0
- precision-guard residuals: 0
- contract/canonical/synthesis/dangling-evidence/support-projection errors: 0
- observed request charge: 1,376 / 2,000
- theoretical request ceiling: 2,000 / 2,000
- runtime: 629.722 s
- third-party API cost: $0
- search API requests: 0
- external manual audit: 20 rows, 0 issues
- support manual audit: 42 rows, 0 issues

Artifact: `11386579108`
Digest: `sha256:74401ccf2e1c11832bc91563ce02c8cb4ff040491542c563052049205a1b995e`.

Decision: **Q8 GO**.

## Consumed seeds

Never reuse as fresh evidence:

- `20261104`
- `20261105`
- `20261106`
- `20261107`

Any future fresh qualification must append the successful attempt-4 cohort to the all-touched exclusion first.

## Q9 boundary

Production collector/evaluator semantics are frozen. Q9 may synchronize documentation and release metadata, but must not change the qualified data path.

Current qualified code ref:

- `release/v8-qualified-2026-10-06`
- code SHA `200f056a5a60cad23610a3958b6bec62dfb624a5`

After documentation synchronization passes Baseline CI, freeze a separate submission-ready ref at that documentation-complete `main` SHA. That final submission SHA may differ from the qualified code SHA only by documentation/release metadata.

## After Builderr

Do not pre-optimize blindly. Once Builderr returns the next official category breakdown:

- preserve zero known material wrong-company publications;
- preserve complete evidence/provenance;
- preserve synthesis/UX behavior unless the official score shows a problem;
- target only the measured remaining gap;
- reopen experimental sources only with explicit transfer, rights and request-budget proof.
