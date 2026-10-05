# Qualification Sprint — External Gap Audit

Date: 2026-10-05

Status: **CONSUMED REPLAY PASS / Q4 SOURCE-REACH BOTTLENECK / Q5-Q6 UNCHANGED DESIGN NO-GO**

## Purpose

Measure the next qualification-sprint recall gaps before changing collectors or spending a fresh cohort.

The audit is read-only and uses only the already-consumed Phase-11 owner-veto replay. Missing signals remain unknown/unavailable; no negative company facts are inferred.

## Reproducible run

- consumed source workflow: `37314396820`;
- audit workflow: `37330340994` — PASS;
- audit artifact: `11353114644`;
- artifact digest: `sha256:175cc290cde6512a1e0fa685fe6e9da2f09c8e2ca26ba45b4d9de053914cdb53`;
- audit head: `e96449bc43ed1d1c3e7708164fa23dbc7c42acfa`.

## Company-level external coverage

| Field | Companies | Coverage |
|---|---:|---:|
| `official_website` | 6 | 6% |
| `external.profile_handle` | 4 | 4% |
| `social_links` | 4 | 4% |
| `external.contact_email` | 6 | 6% |
| `external.careers_page` | 0 | 0% |
| `external.job_posting` | 0 | 0% |
| `external.company_update` | 0 | 0% |
| `external.workforce_snapshot` | 99 | 99% |
| `official.support_award` | 11 | 11% |

## Conditional yield once a company site is verified

Verified company sites: **6/100**.

- profile-handle companies: **4/6 = 66.7%**;
- first-party contact-email companies: **6/6 = 100%**;
- homepages with careers links: **0/6**;
- homepages with news-detail links: **0/6**;
- homepages with explicit active-hiring markers: **0/6**;
- homepages with job-listing candidates: **0/6**.

## Q4 decision — social/contact

**Decision: do not spend another milestone retuning the current extractors.**

The company-level social/contact coverage looks low only because verified-site reach is low. Once a site is exact:

- contact extraction succeeds on all 6/6 sites;
- profile-handle extraction succeeds on 4/6 sites.

The primary Q4 bottleneck is therefore upstream exact-site reach, not evidence projection or the current first-party contact/social extraction logic.

Q4 status: **MEASUREMENT COMPLETE / SOURCE-REACH BLOCKED**.

## Q5 decision — hiring

**Decision: unchanged first-party hiring design is NO-GO for another fresh qualification attempt.**

None of the six verified homepages exposes:

- a careers link;
- an active-hiring marker; or
- a concrete job-listing candidate.

This does not prove such pages never exist elsewhere. It proves that repeatedly tuning the existing homepage-derived Q5 path against the same source reach has no measured transfer surface in this consumed sample.

Q5 status: **NO MEASURED SURFACE / UNCHANGED DESIGN HOLD**.

## Q6 decision — dated first-party activity

**Decision: unchanged first-party news/activity design is NO-GO for another fresh qualification attempt.**

None of the six verified homepages exposes a retained news-detail nomination, so the current exact-page/date projector has no additional consumed surface to exploit.

Official support awards remain valid typed official events and must not be relabelled as company-authored news merely to improve coverage.

Q6 status: **NO MEASURED SURFACE / UNCHANGED DESIGN HOLD**.

## Request-budget context

Observed consumed run:

- logical requests: **682**;
- conservative challenge charge: **1,364 / 2,000**;
- observed unused charge: **636**.

Structural theorem:

- theoretical conservative ceiling: **2,000 / 2,000**;
- structural headroom proven: **NO**.

This distinction is important: the actual cohort happened to use fewer requests than worst case, but production cannot add another unconditional request family until the theoretical ceiling is reallocated/re-proved.

Low-yield discovery context:

- H1g attempts: **74**;
- H1g verified sites: **0**;
- Wikidata candidate count: **0**;
- selected sites: 4 registry-linked + 2 deterministic-domain + 94 none.

These numbers identify potential future request-allocation candidates, but this audit does not change the budget theorem or production path.

## Sprint consequence

Q4-Q6 do not justify a fresh cohort in their unchanged forms.

The next qualification work should therefore focus on a genuinely different recall mechanism or on structural request reallocation, while preserving:

- exact-company publication precision;
- typed signal semantics;
- complete evaluator-visible provenance;
- one terminal result per company;
- explicit unknown/unavailable states.

Q8 fresh Phase-11 attempt #2 remains **BLOCKED** until consumed/dev transfer is materially stronger than current production.
