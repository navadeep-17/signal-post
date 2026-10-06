# Signalpost V9 Continuation State

Last updated: 2026-10-06

This document is the V9 engineering handoff. Live GitHub is authoritative if any recorded SHA advances.

## M0 freeze verification

- current production `main`: `72f1bf2892ec1c1e35674aa383433c9a37afdaca`
- frozen qualified SHA: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- frozen qualified ref: `release/v8-qualified-2026-10-06`
- frozen submission ref: `release/v8-submission-2026-10-06`
- submission ref currently equals `main`
- V9 branch: `experiment/v9-email-domain-substitution`
- V9 branch base: exact current `main`
- research branch: `research/bulk-exact-org-recall`
- live research relation observed at V9 start: **+293 / -67 vs main**
- the research branch remains an archive and must never be merged wholesale

The live relation differs from the planning PDF's earlier +289/-67 snapshot; live GitHub wins.

`docs/CONTINUATION_STATE.md` on `main` records the latest pre-cleanup Baseline CI run `37407690443` as PASS. The GitHub connector's commit-run wrapper exposes PR-triggered runs only and returned no directly attached run for the current main commit, so V9 branch CI is still a separate gate.

Decision: **M0 PASS**. V8 refs were not moved or rewritten.

## Active milestone

**M1 measurement harness + M2 budget-neutral strong BRREG registry-email-domain substitution.**

North-star:

> net-new exact-company coverage per Builderr-scored family per request

The V9 challenger must not optimize raw claim count.

## First implementation block

Implemented on the isolated V9 branch only:

1. A company-family measurement module/CLI that compares baseline and challenger on an identical cohort and reports:
   - verified website companies;
   - social companies;
   - external-contact companies;
   - careers-surface companies;
   - company-authored hiring-intent companies;
   - specific active-job companies;
   - dated first-party activity companies;
   - logical/conservative request charge;
   - terminal/error/cost summaries.
2. A strong BRREG email-domain selector that permits only `exact`, `multi`, or `acronym` legal-name/domain morphology.
3. The candidate remains nomination only. Independent fetch, existing exact-company verifier, wrong-org veto, registry-risk guard, and all publication evidence rules remain unchanged.
4. Weak/non-generic-but-unrelated registry email domains no longer deserve the M2 candidate slot.

## Safety boundary

Do not:

- move either V8 release ref;
- merge the research branch wholesale;
- weaken exact-company verification;
- use an email domain as ownership proof;
- consume a fresh cohort for M1/M2 tuning;
- add search/paid API requests;
- increase `MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE`;
- merge this branch before consumed baseline-vs-challenger transfer evidence exists.

## Required next gate

1. Make Baseline CI green on the V9 branch.
2. Replay baseline and challenger on consumed data.
3. Run the family measurement harness on exactly the same companies.
4. Manually audit every new external publication.
5. Confirm:
   - wrong-company publications = 0;
   - existing verified websites lost = 0;
   - net-new company-family coverage is positive;
   - contract/canonical/synthesis/evidence checks remain clean;
   - conservative request theorem is unchanged or lower.
6. Decision: PROMOTE / RETUNE / SHELVE / DROP.


## M4 isolated implementation branch

Branch: `experiment/v9-m4-zero-request-contacts`

Base: exact M2/M3 experiment head `04b6f2555d4e1a9b5da25ae325ead5a802967772`.

M4 is deliberately isolated from PR #142 while its consumed M2/M3 transfer run completes. The branch reimplements only the narrow zero-request contact behavior measured on the research archive:

- schema.org Organization email recovery from the already-retained exact-site snapshot;
- exact-node identity gate: exact target organisation number, or legal-name token match with no conflicting structured organisation number;
- same-registered-domain requirement for structured email;
- conservative Norwegian structured telephone normalization and recovery;
- evaluator-visible `external.contact_phone` projection;
- canonical `website.contact_phone` projection;
- zero new network requests, search requests, request classes, or paid APIs.

The existing footer/contact email path remains intact and takes precedence when the same address is also present in JSON-LD. Free-text JSON-LD contact strings are not scanned. A structured Organization node for a different legal entity is a hard abstention.

M4 added a dedicated consumed-data contact audit and a PR workflow that compares the challenger against the frozen M2/M3 head on the already-consumed 100-company cohort. Promotion requires zero lost contact publications, complete evidence for every new contact, unchanged theoretical request ceiling, zero contact-network requests, and manual review of every new contact publication.

No fresh cohort is authorized by M4.
