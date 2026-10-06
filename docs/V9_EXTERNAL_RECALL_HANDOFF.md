# Signalpost V9 External Recall — Implementation Handoff

Updated: 2026-10-06

Status: **WP0 complete; WP1 consumed baseline complete; WP2 nomination contract qualified on its isolated branch.**

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

## Current decision

**CONTINUE.**

No fresh cohort has been consumed. No provider search has been run. No V8 identity rule has been weakened.

## Exact next actions

1. Merge WP2 into the V9 integration branch after its already-green exact-head checks.
2. Finish/verify the WP3 provider-gate branch.
3. Confirm a concrete evaluator-reproducible provider/right/cost contract before any live search.
4. If a provider qualifies, run only the deterministic Gate-A 20 unresolved companies.
5. Continue only if Gate A reaches at least **5/20 new verified sites**, with **0 wrong-company publications** and **0 evidence defects**.
