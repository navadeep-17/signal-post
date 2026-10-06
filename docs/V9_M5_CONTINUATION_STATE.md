# Signalpost V9 M5 Continuation State

Last updated: 2026-10-06

## Decision

**PROMOTE** M5 hiring semantics into the next isolated V9 lineage.

Qualified code head: `9165c2c9e02ab06010fb615fc1406fb0fac640b1`.

M5 remains stacked on the promoted integrated M2+M4 candidate. Production `main`, the V8
qualified ref, and the V8 submission ref remain untouched.

## What M5 adds

M5 makes the hiring semantics explicit and non-overlapping:

1. `external.careers_page` / `hiring.careers_page` means a verified company-owned careers
   surface exists.
2. `external.hiring_intent` / `hiring.company_authored_intent` means exact first-party
   company-authored text explicitly expresses recruitment intent.
3. `external.job_posting` / `hiring.job_posting` remains the existing strict specific-job
   layer.

A careers surface is not treated as hiring intent. Hiring intent is not treated as proof of a
specific active vacancy.

The M5 projector is zero-network. It uses only already-retained exact-site page evidence and
does not add a search request, paid API, request class, or site-fetch slot.

## Precision rules

The hiring-intent gate is fail-closed:

- source must belong to an already-verified exact company website;
- source URL must remain same-company-host;
- evidence must be page-local, hashed and timestamped;
- generic careers/navigation wording is insufficient;
- explicit negative hiring language vetoes the candidate;
- broad phrases such as `vi søker` / `looking for` require nearby people-or-role context;
- publication never creates `external.job_posting`.

Specific job publication remains governed by the pre-existing strict job contract.

## Qualification evidence

Exact-head Baseline CI run `37506125456`: **PASS**.

Exact-head M5 consumed-1000 replay run `37506125575`: **PASS**.

Replay artifact:

- artifact ID: `11432295633`
- digest: `sha256:544af758c0d0a461981b9aa4bb5ef520e2eeaec78a4e0bbe7cc092e938b6da18`
- fresh companies used: **0**

The full repository suite also passed on the exact qualified head:

- diagnostic run `37506120561`
- **579 passed + 5 subtests passed**
- frozen V2 product reconstruction remained byte-compatible after the no-intent synthesis
  compatibility fix.

Consumed-1000 replay result:

- careers-surface companies: **0 -> 0**, lost **0**
- company-authored hiring-intent companies: **0 -> 1**, net-new **+1**
- specific-job companies: **0 -> 0**, lost **0**
- new hiring-intent claims: **1**
- non-intent claims changed: **0**
- contract/canonical/synthesis errors: **0**
- network requests added: **0**
- search API requests: **0**
- third-party API cost: **$0**
- all new hiring-intent evidence complete: **true**

## Manual precision audit

Every new M5 publication was manually reviewed.

The single new publication is organisation `927097532`, **ENTALPY AS**, source
`https://entalpy.no/`.

The retained exact-site identity proof is score **1.0**, publishable, with exact organisation
number `927097532` explicitly observed. The page contains explicit first-party recruitment
language beginning with `Vi søker` and nearby role/person context including kuldeteknikere,
mekanikere, administrative/logistics personnel, production planning and leadership.

The publication is accepted only as company-authored hiring intent. It explicitly does not assert
that a specific vacancy is currently open, and no `external.job_posting` claim is created.

Manual result: **1 reviewed / 1 accepted / 0 wrong-company / 0 semantic overclaim**.

## Promotion boundary

M5 is promoted because it adds one new scored-family company at zero request/cost and with no
regression in careers, jobs, non-intent claims, contract, canonical mapping, synthesis, or frozen
artifact compatibility.

Fresh qualification remains locked.

The exact next milestone is **M6 structured dated first-party activity**, isolated from the cleaned
M5-promoted head. M6 must preserve strict page-local/structured publication-date semantics and may
not reuse sitemap/index timestamps or one page hash for another page's fact.
