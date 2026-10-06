# Signalpost V9 External Recall — Implementation Handoff

Updated: 2026-10-06

Status: **WP0 complete; WP1 implementation started on consumed/dev data only.**

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

## WP1 baseline policy

The first baseline must use only previously touched companies.

The selected source cohort is the already-consumed Phase 11 100-company manifest archived by workflow run `37314396820`:

- artifact: `phase11-owner-veto-consumed-replay`
- manifest: `phase11-fresh-100.jsonl`
- manifest SHA-256: `394eaae1b43fbe5e951fc4a61c7185c068bfa6dad1d37a7223cefc507429dd99`
- V9 classification: **consumed/dev**
- fresh qualification credit: **none**

Current V8 will be rerun on that exact manifest. The resulting output will be measured for:

- verified website companies
- social-profile companies
- contact-email companies
- careers-surface companies
- specific-job companies
- dated-activity companies
- website ambiguous/blocked/not-available states
- observed conservative requests
- structural request ceiling
- wall runtime
- third-party API cost
- search API request count

A deterministic unresolved-site manifest and Gate-A 20-company manifest are then derived from the rerun using a frozen seed. Gate-A companies must all lack a published `official_website` in the current V8 rerun.

Wrong-company publication count and evidence defects are **not inferred** by the offline metric script. They remain manual/evidence-gate outputs and must be explicitly audited before any promotion decision.

## Implementation started

Added on V9 integration branch:

- `scripts/build_v9_baseline.py`
- `tests/test_v9_baseline.py`

The baseline builder:

1. validates output and manifest company sets;
2. measures company-level external-family coverage rather than raw claim count;
3. classifies website resolution states;
4. deterministically ranks unresolved companies;
5. writes the full unresolved-site manifest;
6. writes the 20-company Gate-A manifest;
7. hashes both manifests;
8. records runtime/request/cost metadata when a V8 run report is supplied;
9. marks the cohort explicitly as consumed/dev and not fresh qualification evidence.

## Current decision

**CONTINUE WP1.**

No V9 discovery logic has been implemented yet. No provider/search experiment has started. No fresh cohort has been consumed.

## Exact next action

Run the new V9 consumed baseline workflow on the archived Phase 11 100-company manifest, inspect the resulting family metrics and Gate-A manifest, and only then begin WP2 Website Discovery 3.0 abstraction.
