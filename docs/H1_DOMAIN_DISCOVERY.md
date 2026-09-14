# H1 domain discovery experiment

Status: **MERGEABLE EXPERIMENTAL INFRASTRUCTURE — not integrated into the competition runner**

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
6. Allow one narrow corroboration path only for an already-`review` result when a simple two-label email domain exactly matches the normalized distinctive legal name.
7. Promote only an `exact` result; keep review/uncertain/error cases quarantined.
8. Record request/latency/bytes and zero third-party API cost.

This path has no search-provider dependency and introduces no paid API spend.

The experiment deliberately does not hard-code service-provider domains observed in the sample; those domains are allowed through so the identity gate is tested against realistic negatives.

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

## Final frozen 200-company run

Final audited experiment logic was run at commit `9497f0c77d3c49856ae2d63b8dac8f6e5214477a` in GitHub Actions run `34774831144`.

Artifact digest:

`sha256:faf5ae8e547fb4921b730cf8f7d905ca4ade8609b6205fa7520b78c552077f21`

### Development 100

- eligible email-domain profiles: 14
- candidate domains fetched: 14
- exact/promoted: 1
- quarantined: 13
- requests: 74
- third-party API cost: $0
- request latency p50: 568 ms
- request latency p95: 15,150 ms

Promoted domain:

- `ARKITEKTFIRMA JON VIKØREN AS` / org `985589003` -> `arkjv.no`

Human audit: **correct**. The company site publishes the exact legal name, organisation number `985 589 003`, address and `post@arkjv.no` on its own company-information page.

### Zero-overlap validation 100

- eligible email-domain profiles: 7
- candidate domains fetched: 7
- exact/promoted: 1
- quarantined: 6
- requests: 30
- third-party API cost: $0
- request latency p50: 954 ms
- request latency p95: 15,000 ms

Promoted domain:

- `MASTER SURGERY SYSTEMS AS` / org `993550116` -> `mastersurgerysystems.no`

Human audit: **correct**. The company site identifies Master Surgery Systems AS at the Horten address and uses the same domain for company email; independent public records link org `993550116` and the company to `mastersurgerysystems.no`.

### Observed exact-domain audit result

- promoted cases manually audited: 2
- correct: 2
- wrong-company domains: 0
- observed precision on promoted cases: 100%

This **does not prove** the starter's conservative 99.5% production-precision target because two promoted examples are far too small a statistical sample. H1a therefore remains experimental and is not automatically called by the competition runner.

## Dangerous false positive found and fixed

An earlier validation run incorrectly marked `mesco.no` exact for `MESCO AS`. The domain resolved to a generic Norwegian hosting/webhotel placeholder; the single legal-name token matched the hostname and the previous gate treated enough placeholder text as substantive company content.

The fix is generic rather than company-specific:

- Norwegian registered-domain/webhotel placeholder language is now detected as parked/hosting content;
- a permanent regression test protects this class of false positive;
- the same frozen 200-company experiment was rerun after the fix;
- `mesco.no` now remains quarantined with identity score `0.1`.

This failure is the main reason H1 stays conservative even when recall is low.

## Experiment outputs

`.github/workflows/h1-domain-discovery.yml` produces separate development and validation artifacts:

- registry-only baseline profiles;
- H1a enriched profiles;
- compact candidate/prediction JSONL;
- request/runtime/cost report;
- exact input hashes.

The workflow does not use a search API and is manual-only after the qualification run so ordinary development commits do not repeatedly download the large BRREG snapshot.

## Merge decision

**Merge H1a tooling, tests, documentation and identity hardening into `main`, but do not wire H1a into `run_competition_batch.py` yet.**

Reasoning:

- the experiment uncovered and fixed a real wrong-domain failure mode;
- the final frozen dev and zero-overlap validation runs each retained one manually verified domain and zero audited wrong-domain promotions;
- the path is rights-safe and has zero third-party API cost;
- coverage uplift is real but small;
- sample size is insufficient to claim production-level 99.5% exact-domain precision;
- request p95 is high because dead/slow candidate domains can consume the timeout budget.

The next H1 step is a larger frozen hard-negative audit plus request/runtime optimization. H1b search-provider work remains blocked until a provider's current plan/terms are explicitly approved.

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
9. Refresh/idempotency behavior is covered before final production promotion.

Until those production gates are satisfied, H1 remains an experiment even though its reusable infrastructure may live on `main`.
