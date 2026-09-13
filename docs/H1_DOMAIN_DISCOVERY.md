# H1 domain discovery experiment

Status: **EXPERIMENTAL — not integrated into the competition runner**

This document records the first measured coverage hypothesis after the frozen 100-company baseline.

## Why H1 exists

The frozen development slice showed 93/100 companies without a registry website. Only 2/100 had a registry-linked website that already passed the exact-entity identity gate. The first useful optimization is therefore finding safe candidate official domains, not deepening crawling for the small set that already has a site seed.

The publication invariant does not change:

> Discovery may nominate a domain. Only independently fetched exact-entity evidence may publish it as the canonical company website.

## H1 is split into two stages

### H1a — official registry email-domain candidate

Before paying for or licensing search, inspect the public BRREG registry email field for companies whose registry website is missing.

Pipeline:

1. Read the public `epostadresse` value already present in official registry evidence.
2. Reject only clearly generic consumer mailbox domains.
3. Treat the remaining email domain as a candidate, not a fact.
4. Fetch the candidate website through the existing safe URL/robots/redirect controls.
5. Run the existing deterministic exact-entity website identity gate.
6. Promote only an `exact` result; keep review/uncertain/error cases quarantined.
7. Record request/latency/bytes and zero third-party API cost.

This path has no search-provider dependency and introduces no paid API spend.

The 2026-09-13 development baseline had 19 missing-website profiles with a parseable public registry email. The experiment deliberately does not hard-code service-provider domains observed in that sample; those domains are allowed through so the identity gate is tested against realistic negatives.

### H1b — licensed search-provider fallback

Only companies unresolved by registry website + H1a should reach search. Search results remain candidate discovery only and must never be treated as publication evidence.

H1b is currently **blocked on provider rights selection**.

## Current provider-rights review

### Brave Search API — standard terms blocked for our benchmark use

Reviewed: 2026-09-13

Current terms: https://api-dashboard.search.brave.com/documentation/resources/terms-of-service

The current Search API Terms of Use are dated 2026-09-01. The standard terms prohibit storage/cache/database creation from Search Results beyond transient operational storage and also prohibit using Search Results to create, evaluate, train, re-train, fine-tune, benchmark or otherwise improve AI models or services.

Because H1 requires a measured benchmark of our agent/service, standard Brave Search API terms are **not approved for H1 evaluation**. A custom/enterprise order form could change the permitted use, but that must be documented before use.

The existing `scripts/run_brave_discovery.py` remains reference/experimental code. Do not run it as the qualification benchmark under standard terms.

### Tavily — candidate, not yet approved

Reviewed: 2026-09-13

Terms: https://www.tavily.com/terms
Pricing: https://docs.tavily.com/documentation/api-credits

Tavily's current terms explicitly support Customer Applications that may include AI tools, require customers to verify outputs, and do not contain the same explicit standard-plan prohibition on evaluating the customer's own AI service found in Brave's current terms. However, Tavily also places responsibility for applicable third-party source terms on the customer.

Therefore Tavily is a **rights-review candidate**, not yet a promoted connector. If used later, keep search results transient, retain only independently fetched page evidence, and record the exact account/plan terms in effect for the run.

## Frozen H1 corpora

Development slice:

- first 100 companies of deterministic seed `20260823` entry manifest
- SHA-256: `51a96f25f79532b9ba285304d540887e0f17410907909dbe6c85c0b41b8341d3`

Zero-overlap validation slice:

- rows 101–200 of the same deterministic 1,000-company manifest
- SHA-256: `5cdbe6e976eb7e7011dd47b0617e80410b4410de13819465c21c9cc099a325c7`

The H1 workflow recreates both manifests and fails if either hash changes.

## Experiment outputs

`.github/workflows/h1-domain-discovery.yml` produces separate development and validation artifacts:

- registry-only baseline profiles;
- H1a enriched profiles;
- compact candidate/prediction JSONL;
- request/runtime/cost report;
- exact input hashes.

The workflow does not use a search API.

## Promotion gate

H1a or any later H1b provider may enter the competition runner only when all are true:

1. Acquisition rights are documented for the exact plan/mode used.
2. Candidate discovery and publication evidence remain separate.
3. Every published domain has an independently fetched page URL, retrieval time, content hash and exact-entity reason.
4. Human audit finds zero wrong-domain publications on the frozen development and zero-overlap validation sets.
5. A larger frozen audit includes parent/franchise/namesake/service-provider hard negatives.
6. Exact-domain precision meets the starter's conservative 99.5% target with zero wrong-company publications.
7. Recall/coverage gain transfers to the zero-overlap validation corpus.
8. Request/runtime/cost remain comfortably inside the final 100-company budget.
9. Refresh/idempotency behavior is covered before final promotion.

Until then, H1 remains an experiment even if local coverage rises.
