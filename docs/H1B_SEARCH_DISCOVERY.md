# H1b search-based missing-domain discovery

Status: **EXPERIMENTAL TOOLING — offline-qualified, live frozen audit pending provider credentials**

H1b exists because the first frozen 100-company baseline had 93/100 companies without a registry website, while H1a can only help the subset with a useful non-consumer BRREG email domain.

H1b does **not** make search results company facts. Its only purpose is to nominate URLs that may be worth independently crawling.

## Safety invariant

```text
search provider result
        ↓
transient candidate scoring only
        ↓
provider title/snippet/query/rank discarded
        ↓
independently fetch destination URL
        ↓
ordinary website identity gate
        ↓
H1b page-only hardening gate
        ↓
exact legal entity? publish : quarantine
```

A provider result can never directly become an `official_website` claim.

## Current provider adapter

The first adapter is **SerpApi Google Search API**, but it remains experimental.

Public legal/product material was reviewed on 2026-09-14:

- SerpApi legal terms page reported an update date of 2026-08-27.
- The reviewed public terms did not contain the Brave Search API's explicit prohibition on evaluating/benchmarking AI services.
- SerpApi documents 31-day retention for ordinary search data.
- Enterprise ZeroTrace is documented as avoiding storage of search parameters/files/metadata on SerpApi systems.
- SerpApi markets web-search output for AI applications.
- Customer use remains responsible for lawful use of the returned data.

This is an engineering/source-policy review, **not legal advice** and not a final declaration that every plan/use is permitted. Before H1b can become part of the submission strategy, the exact account/plan and current terms must still be recorded.

## Data-retention boundary in our implementation

The H1b experiment deliberately does not persist:

- provider raw JSON response;
- result titles;
- result snippets;
- result ranks;
- plaintext search query.

It records only operational/discovery metadata such as:

- provider name/endpoint;
- SHA-256 of the query;
- result count;
- whether any result was selected for independent crawling;
- provider HTTP status;
- declared API cost;
- independently fetched page URL only when appropriate.

The independently fetched company page has its normal URL/time/hash/evidence record and is the only possible publication evidence.

## Candidate crawl gate

`score_search_candidate()` is intentionally a **crawl** gate, not publication.

It rejects known directory/social hosts and directory-style company-record URLs. A result can nominate a crawl when either:

1. the legal name aligns strongly with the hostname and the result contains strong legal-name/org evidence; or
2. the result contains the exact organisation number plus the full legal name and the URL looks like a plausible first-party homepage/page, allowing acronym/brand domains to be tested.

When confidence ties, legal-name-aligned hostnames rank ahead of provider search rank. Search rank itself is not treated as identity evidence.

## Independent publication gate

After fetching the candidate, H1b requires independently fetched page content to prove the exact company.

Strongest path:

- exact 9-digit organisation number appears in independently fetched page text.

Fallback path:

- complete distinctive legal name appears in independently fetched page content; and
- either the BRREG municipality also appears on the page or the final hostname exactly matches the normalized legal name.

Otherwise the result is downgraded to `review` and cannot publish.

This is intentionally conservative and is covered by regressions for:

- directory pages that repeat exact registry facts;
- provider/hosting pages;
- parent-company mentions;
- namesakes in the wrong municipality;
- acronym domains with exact-org result evidence;
- exact company-name domains;
- independently fetched exact organisation number.

## Code

- `src/norway_company_agent/discovery.py`
  - normalized SerpApi parser
  - transient candidate scoring/selection
  - H1b independent page identity guard
- `scripts/run_search_discovery.py`
  - live SerpApi experiment
  - transient provider result handling
  - independent crawl/promotion
  - request/runtime/cost report
- `tests/test_search_discovery.py`
  - H1b regressions
- `.github/workflows/h1b-search-discovery.yml`
  - automatic offline regression job
  - manual live frozen audit only

## Live audit configuration

The live workflow intentionally cannot run without two GitHub Actions secrets:

```text
SERPAPI_API_KEY
SERPAPI_COST_PER_SEARCH_USD
```

`SERPAPI_COST_PER_SEARCH_USD` must represent the declared marginal USD cost for the exact account/plan used. The experiment does not silently assume the API is free.

The manual workflow defaults to only **40 unresolved companies** for the first audit. It:

1. recreates the exact frozen first-100 manifest;
2. runs the official baseline + opt-in H1a first;
3. passes only still-unresolved profiles to H1b;
4. performs transient SerpApi search;
5. independently crawls selected candidate URLs;
6. extracts only independently verified promotions;
7. checks declared third-party spend remains below the challenge's $10/100 ceiling;
8. uploads a compact audit artifact for manual exact-company review.

The untouched final 200-company holdout is not used.

## Current offline status

The H1b-specific/domain regressions and complete starter test suite pass after preserving the starter's unknown-directory rejection behavior. The live provider job remains intentionally unrun until credentials/cost are configured.

## Promotion gate

Do not wire H1b into the competition runner or call it qualified until:

1. the exact SerpApi plan/current rights are recorded;
2. a frozen live development audit succeeds;
3. every promoted site in that audit is manually checked;
4. no wrong-company publication is found;
5. request/runtime/API cost fit with headroom;
6. gain transfers to a zero-overlap validation corpus;
7. provider-result data remains outside the company-evidence corpus;
8. the final strategy is frozen before touching the untouched release holdout.
