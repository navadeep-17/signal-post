# Signalpost V9 M7 Continuation State

Last updated: 2026-10-07

## Decision

**SHELVE / NO NEW PRODUCTION IMPLEMENTATION** for M7 secondary deterministic candidate sources.

M7 is resolved from existing measured project evidence plus live-code revalidation. It does not
justify another unchanged source experiment, another connector, or a fresh cohort.

Base:
`dc5907b27fb8844b0f690a166937bf908f058a73` (promoted M5).

Production `main` and all V8 release/submission refs remain untouched.

## Candidate-source review

### Exact-parent BRREG subunit homepage

Already measured and **DROP**.

Prior consumed screen:

- unresolved companies: 93
- companies with exact-parent subunit homepage hints: 3
- candidates attempted: 3
- accepted exact target sites: **0**
- wrong-company publications: 0
- screen logical requests: 6
- third-party cost: $0

This path must not be repeated unchanged.

### Exact-parent BRREG subunit email-domain

Already measured and **DROP**.

Prior consumed screen:

- exact-parent subunit email rows: 19
- unresolved companies with non-generic candidate domains: 10
- candidates attempted: 10
- accepted exact target sites: **0**
- wrong-company publications: 0
- screen logical requests: 16
- third-party cost: $0

The notable `AGILE SOLUTIONS AS` candidate matched legal-name text but lacked the predeclared
exact organisation-number or registry-location corroboration. The verifier was correctly not
weakened.

### NAV Arbeidsplassen as deterministic candidate source

Prior broad-feed experiment remains **NO-GO unchanged**:

- 20 target companies
- 30,000 feed items traversed
- 54 logical requests
- 3 vacancy-detail requests
- exact active-job matches: **0/20**
- third-party cost: $0

M7 does not rerun that feed scan. NAV can reopen only if a materially different official
exact-employer organisation-number lookup/index route becomes available.

### Wikidata exact organisation-number official-site candidate

This is not a new M7 feature. The live promoted base already contains bounded exact
`P2333 -> P856` candidate discovery, and publication still requires an independently fetched
company page to pass exact-company identity verification.

No duplicate Wikidata connector is added.

### Legal-name DNS/domain candidates

The promoted base already contains bounded deterministic legal-name candidates (H1c/H1g).
Historical-name `.no` expansion was previously stopped after negligible DNS survival and zero
verified target-site yield. Norid organisation-number lookup also remains outside the production
path under the prior access/rights review.

No unchanged DNS expansion is repeated.

## Promotion-bar result

No remaining M7 candidate source simultaneously offers:

1. a genuinely new deterministic retrieval primitive;
2. compatible rights/access;
3. independent exact target-company verification;
4. plausible material net-new scored-family coverage;
5. acceptable request economics inside the fixed theorem;
6. a reason to expect a different result from the already-consumed measurements.

Therefore implementation would violate the V9 rule against repeating stopped paths merely because
they are free or deterministic.

## Decision rationale

**SHELVE M7.**

This is a successful milestone decision: the correct action is to avoid adding code and requests
for candidate sources that have already failed the project's measured promotion bar.

Fresh qualification remains locked.

## Exact next milestone

Proceed serially to **M8 — specific hiring**.

M8 must distinguish:

- existing strict first-party `JobPosting` / role-detail behavior; and
- any NAV publication path, which may proceed only with exact target-employer organisation-number
  identity and current/live official-entry verification.

Name matching alone is nomination only. A broad NAV feed scan must not be repeated unchanged.
