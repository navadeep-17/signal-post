# Signalpost V9 External Recall — Implementation Handoff

Updated: 2026-10-06

Status: **WP0/WP1 complete; WP2/WP3 merged into the V9 integration branch; Gate A remains in RETUNE at a 4/20 verifier-confirmed ceiling after additional source screens.**

This document is intentionally V9-specific. It does not rewrite V8 release history.

## Immutable V8 anchors

Verified directly against live GitHub before V9 branching:

- repository: `navadeep-17/signal-post`
- `main`: `72f1bf2892ec1c1e35674aa383433c9a37afdaca`
- qualified V8 code: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- qualified ref: `release/v8-qualified-2026-10-06`
- submission ref: `release/v8-submission-2026-10-06`
- submission ref SHA: `72f1bf2892ec1c1e35674aa383433c9a37afdaca`
- current evaluator: `scripts/run_signalpost_v8.py`
- post-submission Baseline CI: run `37408969941` — **PASS**

The qualified and submission refs are audit anchors. V9 must not move, rewrite, or merge into them while experimental.

## V9 branch

- integration branch: `experiment/v9-external-recall`
- created from exact V8 submission/main SHA `72f1bf2892ec1c1e35674aa383433c9a37afdaca`
- direct merges to `main`: **forbidden during experiment phase**

## Development rule

```text
ATTEMPT MORE
    ↓
VERIFY STRICTLY
    ↓
PUBLISH CONSERVATIVELY
```

Candidate nomination is untrusted. Exact-company publication authorization remains unchanged or stricter.

## WP1 consumed/dev baseline — PASS

The baseline uses only the already-consumed Phase 11 100-company manifest archived by workflow run `37314396820`:

- artifact: `phase11-owner-veto-consumed-replay`
- source manifest SHA-256: `394eaae1b43fbe5e951fc4a61c7185c068bfa6dad1d37a7223cefc507429dd99`
- V9 classification: **consumed/dev**
- fresh qualification credit: **none**
- V9 baseline workflow: `37421325313` — **PASS**
- exact baseline head: `a5799016bbdc84dd015e73bb09f92cccd5ef9bc8`
- artifact: `v9-consumed-baseline`
- artifact ID: `11393772677`
- artifact digest: `sha256:b7dd01b666470d155d2c70274bb8d1cb2695abc9d2f331d6a41eafe447c023f8`

### Current V8 family baseline on consumed 100

| Metric | Baseline |
|---|---:|
| Verified website companies | 6 / 100 |
| Social-profile companies | 4 / 100 |
| Contact-email companies | 6 / 100 |
| Careers-surface companies | 0 / 100 |
| Specific-job companies | 0 / 100 |
| Dated first-party activity companies | 1 / 100 |
| Social-link aggregate companies | 4 / 100 |

Website resolution states:

- available: 6
- ambiguous: 3
- blocked: 2
- not available: 89
- failed: 0

This confirms the V9 causal diagnosis: the upstream website bottleneck remains severe, and the downstream external families are correspondingly sparse.

### Baseline operations

- observed conservative challenge requests: **1,388 / 2,000**
- structural request ceiling: **2,000 / 2,000**
- wall runtime: **958.871 s / 2,400 s**
- third-party API cost: **$0**
- search API requests: **0**
- contract/canonical/synthesis checks: **PASS**

### Deterministic unresolved cohort

- unresolved companies: **94 / 100**
- unresolved manifest SHA-256: `3454f70c0dc9b78516ba4f84d3deb5c77a19ad1735d048c72ca80b76e3149993`
- Gate-A size: **20**
- Gate-A manifest SHA-256: `f2177abd0bd0d6202f9fe47fd00b8def06b21c01fdf4c864c1f3b68f80b160d5`
- Gate-A verified websites before V9: **0 / 20**
- Gate-A social/contact/careers/jobs/activity before V9: **0 across all families**

The Gate-A set is therefore a clean unresolved-site transfer test. It is consumed/dev evidence only.

Wrong-company publication count and evidence defects are **not inferred** by the baseline metric script. They remain manual/evidence-gate outputs and must be explicitly audited before any promotion decision.

## WP2 Website Discovery 3.0 nomination contract

Isolated branch:

`experiment/v9-discovery-3`

Draft PR:

`#132 — v9: add provider-agnostic Website Discovery 3.0 nomination contract`

The branch implements:

- organisation-number-first query plan;
- at most three candidate URLs;
- registered-domain deduplication;
- obvious social/directory/marketplace/review rejection;
- provider result text discarded from nomination output;
- `publication_authorized = false` invariant;
- compatibility with the existing crawl-candidate scorer;
- no production runner changes;
- no exact-company verifier changes.

Verification:

- V9 Discovery Contract workflow `37422106633` — **PASS**
- exact PR-head Baseline CI `37422478314` — **PASS**
- current WP2 head: `adaed550ace9e87c4f3c7b50d92ac223eb255a0c`

WP2 is safe to merge into the V9 integration branch now that WP1 passed. It is still not production code.

## WP3 provider gate

A further isolated branch now exists:

`experiment/v9-search-provider-gate`

It contains a generic provider-contract gate requiring:

- evaluator reproducibility;
- confirmed rights state;
- evaluator-accessible key/credential path when required;
- explicit cost per search;
- bounded search count;
- projected provider spend within the challenge budget.

Passing that gate permits only a bounded experiment, never production promotion. No concrete provider has been approved or enabled yet.

## WP2/WP3 integration status

The provider-agnostic nomination contract and generic provider gate are now merged into `experiment/v9-external-recall` only.

The latest V9 integration merge after nomination-recall retuning is:

`7699b7c44b1ff407893cfb8dba5571866050065e`

The nomination retune passed workflow `37425242213` with 40 focused regressions. It changes only which provider URLs are worth independently fetching; publication authorization remains entirely downstream of the unchanged exact-company verifier.

## Gate-A source screens

Two narrow consumed-only screens have now been completed against the frozen 20-company Gate-A manifest.

### BRREG annual-report domain screen

Workflow `37424227898` passed, but produced only one domain candidate and **0 / 20** new verified websites. The one candidate was independently rejected as another legal entity. Decision: **SHELVE as a primary website-discovery source**.

### Reconnaissance verifier calibration

Workflow `37426159410` passed. Eight candidate URLs were independently fetched and sent through the unchanged verifier. Exactly three organisations were machine-verified:

- AURSNES KIOSK AS → `aursneskiosk.no`
- FALEX FORVALTNING AS → `falex.no`
- PREG BARNEHAGER ÅLESUND AS → `pregalesund.barnehage.no`

Wrong/weak controls remained rejected, including `bravoseafood.no` for BRAVO MATSENTER AS, the SPAR Førde hosted store page without exact legal-entity proof, and `dg13.no` for DRONNINGENS GATE 13 AS.

This calibration is not provider qualification evidence: the candidate source was external reconnaissance rather than an evaluator-reproducible V9 provider.

Full record: `docs/V9_GATE_A_RETUNE.md`.


### Additional Gate-A source screens after fetch-relaxation closure

Two further rights-safe, consumed-only nomination hypotheses were tested on the unchanged frozen Gate-A 20.

**Registry-seeded sitemap screen**

- branch: `experiment/v9-registry-seed-sitemap`
- workflow: `37446354632` — **PASS**
- head: `393b39bfc0a567552b5e6d12222ea025e166dd91`
- final hardened nominations: **1**
- new verified websites: **0**
- logical requests: **26**
- conservative request charge: **52**
- runtime: **18.129 s**
- third-party API cost: **$0**
- decision: **SHELVE**

The scorer was hardened before the final run to reject host-brand leakage, generic legal terms, contact-person-only paths, manager-brand noise, and location-only sitemap nominations.

**BRREG subunit homepage screen**

- branch: `experiment/v9-brreg-subunit-discovery`
- workflow: `37447133224` — **PASS**
- workflow head: `389c6269c66579e13997deecad8f46c0066dca1d`
- parents with BRREG subunits: **17 / 20**
- parents with usable subunit homepage fields: **0**
- new verified websites: **0**
- logical requests: **20**
- conservative request charge: **40**
- runtime: **14.278 s**
- third-party API cost: **$0**
- decision: **SHELVE**

The parent→subunit relationship was explicitly forbidden from supplying parent-company identity proof; it could only nominate an independently fetched URL.

Neither experiment changes the current Gate-A ceiling of **4 / 20**.


### Exact-org OpenStreetMap/Overpass source screen

A further consumed-only experiment queried exact OpenStreetMap organisation-number references for the frozen Gate-A parents plus their exact BRREG subunits.

- branch: `experiment/v9-osm-orgnr-discovery`
- workflow: `37449173244` — **PASS**
- head: `bd65ed37b7a0ad4af946c76f5cac9eed1956a349`
- artifact ID: `11405280045`
- exact references queried: **37** (20 parents + 17 subunits)
- OSM elements returned: **1**
- website candidates nominated: **0**
- new verified websites: **0**
- logical requests: **21**
- conservative request charge: **42**
- third-party API cost: **$0**
- decision: **SHELVE**

The single exact-reference OSM element exposed only an email field for a PREG-related subunit and no website field. The experiment therefore does not change the Gate-A ceiling of **4 / 20**.

## Current decision

**RETUNE.**

The plan's Gate-A continuation minimum is **5 / 20** new verified websites. Current machine-verifiable candidate uplift is **3 / 20**, so Gate A has not passed.

No fresh cohort has been consumed. No production provider has been enabled. No V8 identity rule has been weakened. No V9 experiment has been merged to `main`.

## Exact next actions

1. Keep the exact frozen Gate-A 20; do not replace or cherry-pick the cohort.
2. Continue Website Discovery 3.0 source retuning for **one** additional independently verifiable exact-company site; the current ceiling is 4/20 and the gate is 5/20.
3. Prefer a rights-safe, evaluator-reproducible, organisation-number-anchored public source over another fetch relaxation. The next micro-screen should first inspect exact BRREG subunit names for trade/brand aliases, then test a bounded subunit-alias domain nomination path only if the aliases provide genuinely new candidate labels.
4. Require the generic provider gate before any conventional live search-provider experiment: evaluator reproducibility, permitted rights/use, evaluator-accessible credential path when needed, bounded calls, and declared cost.
5. Do **not** proceed to the consumed 100-company Gate B until Gate A reaches at least **5/20**, with **0 wrong-company publications** and **0 evidence defects**.
6. Do not consume a fresh cohort before Gate A, Gate B, request-theorem proof, and full V9 CI all pass.
