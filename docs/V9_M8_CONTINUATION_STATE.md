# Signalpost V9 M8 Continuation State

Last updated: 2026-10-07

## Decision

**SHELVE NAV extension / retain existing strict first-party JobPosting behavior.**

M8 introduces no new production connector or publication path.

Code base:
`dc5907b27fb8844b0f690a166937bf908f058a73` (promoted M5).

Production `main`, V8 release/submission refs, and the fresh cohort remain untouched.

## Existing first-party specific-job behavior

The promoted code base already contains the strict first-party job behavior required by the V9
plan.

A specific job publication requires exact first-party company context plus specific vacancy
semantics. The implementation/tests enforce, among other things:

- generic careers pages do not become specific jobs;
- a role must have a specific title;
- structured `JobPosting` must expose a specific title, URL and currentness/deadline field;
- dated role-card fallback requires role-detail structure and an application/detail action;
- target-employer context must match the target company;
- a parent target does not inherit a subsidiary role merely because it appears on the same group
  careers surface;
- expired roles abstain;
- careers-surface presence and company-authored hiring intent remain separate from a specific job.

M8 therefore does not duplicate or relax this existing behavior.

## NAV exact-org path

The previous NAV Arbeidsplassen feasibility screen remains **SHELVE**:

- targets: **20**
- lookback: **90 days**
- feed pages: **30**
- feed items traversed: **30,000**
- active headers: **19,972**
- candidate employer headers: **7**
- vacancy-detail requests: **3**
- exact main/subunit organisation-number matches: **0**
- companies with exact active job: **0/20**
- logical requests: **54**
- third-party API cost: **$0**
- BRREG subunit lookup errors: **0**

The live promoted repository contains no new exact-employer NAV retrieval/index implementation.
The only production specific-job implementation remains first-party company-owned evidence.

The broad NAV feed scan must not be repeated unchanged.

NAV may reopen only if there is a materially different official retrieval primitive that can
deterministically retrieve/identify the target employer by organisation number (or an exact
registered subunit relationship) with acceptable request economics.

If NAV ever reopens:

1. name matching alone is nomination only;
2. exact employer organisation number or exact subunit-to-main relation is mandatory;
3. the official vacancy entry must be fetched/re-fetched live before publication;
4. the vacancy must still be current/active;
5. exact evidence, timestamp and source URL must be retained;
6. request theorem and cost gates must be re-proved before promotion.

## Why no new M8 code is added

The first-party part of M8 is already implemented and strict.

The NAV part has no new exact-org retrieval primitive in the current repository/project evidence,
while the previously measured broad-feed strategy produced zero exact target matches at material
request cost.

Adding another broad scan would repeat a stopped path and violate the V9 stop rule.

## Final M8 result

**SHELVE the NAV extension. Retain existing first-party specific-job behavior unchanged.**

No fresh cohort is consumed.

## Exact next milestone

Proceed serially to **M9 — optional organisation-number-first search**.

M9 is permitted only if Builderr explicitly supplies a reproducible provider/key. Without that,
the official production path remains credential-free and M9 must stay parked.
