# Q3 — Search-assisted exact-company website discovery

Last updated: 2026-10-05

Status: **EXPERIMENT IMPLEMENTED / PRODUCTION DISABLED / FRESH QUALIFICATION NOT CONSUMED**

## Why Q3 was reopened

The earlier project policy treated `$0 third-party API cost` and `0 search API requests` as release constraints. Builderr's current challenge page now explicitly states that LLMs are allowed, each official run has a small external API budget, and Builderr can supply a model key for scoring. It also makes recall/coverage the largest scoring component at 50/100 and uses lower third-party cost only after wrong-company publications and recall in the tiebreak order.

Therefore `$0` remains a useful optimization target but is no longer treated as a challenge requirement.

Current official challenge reference checked 2026-10-05:

- https://builderr.ai/challenges/signalpost

## Current OpenAI provider facts

The Q3 experiment uses the OpenAI Responses API only as a transient URL nominator.

Public OpenAI documentation checked 2026-10-05 supports:

- Responses API built-in `web_search`;
- `tool_choice = required`;
- `max_tool_calls` to bound built-in tool usage;
- `search_context_size = low|medium|high`;
- `gpt-6-luna` as a current low-cost model;
- web search price: $10 / 1,000 calls plus search-content tokens at model rates;
- Standard short-context `gpt-6-luna`: $0.10 / 1M input tokens and $0.50 / 1M output tokens.

References:

- https://platform.openai.com/docs/api-reference/responses
- https://platform.openai.com/pricing

The runner does not assume Builderr's exact dollar ceiling. A live run requires an explicit `--max-external-api-cost-usd` value confirmed for that run.

## Consumed-only Q3.1 source screen

No fresh validation company was consumed.

A deterministic 20-company subset of already-consumed unresolved Phase-11 profiles was manually searched only to answer whether search-assisted nomination still has plausible transfer under current rules.

Clear examples found:

1. **LØRENSKOG RENHOLD & SERVICE AS — 940762642**
   - search nominated `lorenskogrenhold.no`;
   - the first-party About page explicitly states the legal entity and organisation number `940 762 642`;
   - this is a high-confidence example where search solves candidate discovery and the fetched site itself supplies publication proof.

2. **XL-BYGG MATHISEN & CO AS — 997645359**
   - search surfaced an exact XL-BYGG store page with matching Alta address/contact context;
   - this is useful nomination evidence but shared-chain/store-domain semantics still require the ordinary exact-company publication gate and may abstain.

3. **BRAVO MATSENTER AS — 939067442 / SPAR Førde**
   - search surfaced the matching SPAR Førde store page;
   - third-party directory evidence maps the legal entity to the same store/address;
   - because this is a shared brand domain, it is not pre-authorized as an `official_website` and remains subject to independent first-party identity proof.

Decision from this screen: **continue the experiment**, but do not count these companies as fresh qualification evidence and do not relax shared-domain/franchise rules.

## Q3 experiment architecture

```text
exact organisation number + legal name
 -> one bounded OpenAI web-search call
 -> transient cited/source URLs
 -> reject directory/social hosts
 -> dedupe by registered domain
 -> at most two independently crawled candidates
 -> current bounded homepage fetch
 -> current website identity gate
 -> current search-discovered page corroboration
 -> conflicting explicit organisation-number veto
 -> publish only if exact-company proof survives
```

The model/search provider may nominate URLs. It may **never** establish legal identity.

## Persistence boundary

Never persist as company evidence:

- model answer text;
- search query text;
- provider raw response;
- provider citation titles;
- search rank as identity evidence;
- quarantined/ambiguous candidate pages.

Persist only:

- an operational discovery summary; and
- an independently fetched candidate page when it passes the current exact-company gate.

## Cost and request guards

Default provider bounds:

- <=1 hosted web-search tool call per queried company;
- `search_context_size=low`;
- <=180 provider output tokens per company;
- declared audit ceiling of 50,000 provider/search-content input tokens per company;
- <=2 independently fetched candidate domains per company.

At current public Standard pricing, the declared 100-company provider ceiling is approximately **$1.509**:

- search calls: 100 x $0.01 = $1.00;
- input/search-content ceiling: 5,000,000 tokens x $0.10/M = $0.50;
- output ceiling: 18,000 tokens x $0.50/M = $0.009.

This is an experiment-side ceiling, not a claim about Builderr's exact official-run allowance.

The production request theorem is unchanged because Q3 is not wired into V8 production. Any future production integration must explicitly reallocate request capacity before merge.

## Promotion gates

### Q3a — code safety

Require:

- exact-head Baseline CI green;
- provider output remains nomination-only;
- one web-search call hard ceiling;
- explicit provider dollar budget required at launch;
- independent current identity gate unchanged;
- quarantined pages not persisted.

### Q3b — consumed/dev live screen

Using evaluator-reproducible credentials only:

- run on already-consumed unresolved profiles first;
- measure verified sites / queried companies;
- manually audit every accepted site;
- record provider calls/tokens/cost and independent crawl requests;
- any wrong-company publication is a hard fail.

### Q3c — fresh transfer

Only after Q3b is materially positive and the exact Builderr provider/key/budget handoff is confirmed:

- consume one fresh bounded cohort;
- require a meaningful net-new verified-site gain;
- require zero wrong-company publications;
- then separately decide whether production integration deserves scarce request slots.

No fresh Phase-11 release cohort is consumed by Q3a/Q3b.
