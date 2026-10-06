# V9 Website Discovery 3.0 — Nomination Contract

Status: **EXPERIMENTAL / ISOLATED**.

Branch: `experiment/v9-discovery-3`

This work package implements only the provider-agnostic nomination boundary from the V9 plan. It does not add a search provider to production, does not fetch nominated candidates, does not alter the exact-company verifier, and cannot publish an official website.

## Contract

Input:

- organisation number
- legal name
- optional municipality/address context supplied by a future provider adapter

Transient query strategy is organisation-number first:

1. exact 9-digit organisation number;
2. spaced organisation number;
3. explicit `Org.nr.` form;
4. legal name + exact organisation number;
5. legal name + `org nr`.

Output:

- at most three candidate URLs;
- registered-domain deduplication;
- obvious social/directory/marketplace/review surfaces rejected;
- no provider title, snippet, or plaintext query retained in the nomination result;
- `publication_authorized = false` always.

A nominated URL is **untrusted**. It may only proceed to an independent HTTP fetch and the existing exact-company identity verifier.

## Safety boundary

This module deliberately reuses the existing transient crawl-candidate scorer but strips provider text from its output. It does not create an evidence record. Provider output is nomination metadata, not company evidence.

The next work package must preserve:

```text
provider result
    ↓
untrusted URL nomination
    ↓
independent bounded fetch
    ↓
existing exact-company identity gate
    ↓
owner/conflict/multi-org guards
    ↓
publish or quarantine
```

## Current test result

Workflow `V9 Discovery Contract` run `37422106633` passed at head:

`a9f9ce2b6e7bd8397a1d6fcf56a6e89205d2fd9a`

The regression set covers:

- the exact V9 query forms;
- output sanitization;
- social/directory rejection;
- registered-domain deduplication;
- three-candidate hard ceiling;
- weak name-only result abstention;
- compatibility with existing search and organisation-number conflict regressions.

## Promotion status

**NOT PROMOTED.**

WP1's consumed baseline must complete successfully before this branch is merged into the V9 integration branch. WP3 must separately establish an evaluator-reproducible provider/key/cost/rights contract before any live search path is enabled.
