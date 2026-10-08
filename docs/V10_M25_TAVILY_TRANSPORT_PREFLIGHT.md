# V10 M25 — Tavily Basic Search bounded transport, offline CI only

Reviewed: 2026-10-08
Disposition: **TECHNICAL TRANSPORT PREPARED; NO LIVE QUERY; NO PRODUCTION PROMOTION**
Experimental base: M23 draft PR #173, itself based on qualified V8 commit `200f056a5a60cad23610a3958b6bec62dfb624a5`.
Related consumed-only development 20: M24 draft PR #174.

## Permission development

Tavily Support responded to the Signalpost team's direct email on 2026-10-08 (subject `Re: Permission clarification: Tavily Search API in student Signalpost challenge`):

- Student challenge with third-party evaluation is **generally fine** under current Platform Terms.
- Aggregate Signalpost coverage may be published **without identifying or comparing providers**. Do not publish Tavily-specific benchmark performance.
- An external evaluator may use the API key **strictly server-side**.
- Up to 100 basic requests per batch is allowed **within the remaining monthly credit budget**.
- Releasing project source without credentials or provider search outputs is allowed.
- Extra free student credits are offered if the team emails from a student address or supplies proof of valid student status plus the desired Tavily account email.

The response explicitly qualifies itself as *general informational purposes only*, not a signed contractual amendment. This reduces the main rights risk but is **not an account, key, credit allocation, or integrated production source**.

Never include a student identity document, credit dashboard screenshot, real API key, or search outputs in the public repository. Do not copy any student ID into chat.

## Provider primary API sources

- Official authentication and endpoint: https://help.tavily.com/articles/4840311948-tavily-search-api
- Official current Basic Search parameters: https://github.com/tavily-ai/skills/blob/main/skills/tavily-best-practices/references/search.md
- Official free-plan account and monthly-credit language: https://www.tavily.com/pricing
- Platform Terms: https://www.tavily.com/terms

Note: Tavily's SDK documents a limited **keyless mode** as of 2026; it is not used here. Its unidentified evaluator-wide limits and rate restrictions are not a production substitute for explicitly authorised key/credit accounting.

## What M25 actually implements

`src/norway_company_agent/tavily_bounded_transport.py` is one `execute_bounded_search` function and its request-budget helper:

1. Constructs the same legal name, nine-digit org number and registry municipality query used by M23.
2. Sends a single POST to **exactly** `https://api.tavily.com/search`, using `Authorization: Bearer` with a key explicitly passed by a future caller. No environment key auto-discovery, and no import-time execution.
3. Pins `search_depth=basic`, `auto_parameters=false`, `include_answer=false`, `include_raw_content=false`, `include_images=false`, and at most ten organic results to avoid extra credits and provider-generated claims.
4. Does not follow redirects, does not use environment proxies, makes **no retry**, rejects non-JSON, malformed schemas, cross-origin response redirects, and responses larger than 512 KiB; max configured deadline per request is eight seconds.
5. Failures including 429/quota exhaustion and 5xx still incur one conservative logical search-attempt slot (2 challenge-charged requests). No raw provider response/error is copied into audit summaries.
6. Only nominal candidate data is transiently passed in memory for M23's independent first-party identity assessment. `SearchResult.audit()` excludes query, title, snippet, response body and key; it never publishes company facts.
7. `SiteSlotBudget` separately verifies one provider search (1 logical) plus at most one first-party robots/homepage path (2 logical) consumes 3/4 site slots. This is a **hypothetical replacement accounting**, not permission to append requests to the qualified runner.

`tests/test_v10_m25_tavily_transport.py` fakes all HTTP responses in memory, including timeout-like transport error, provider 429, key errors, HTTP redirects, a fake 200 redirected origin, oversized JSON, malformed response and unsafe company input. Other tests re-run all M23 identity gates and original H1b search discovery assertions. CI has **no real API key and makes zero Tavily requests**.

## Explicit non-claims

- This does **not** integrate Tavily into `scripts/run_signalpost_final.py` or the qualified V8 site discovery runner.
- It does **not** execute the already-consumed 20-company test, produce any new website candidate for a real company, establish independent factual recall, measure provider latency, or establish a complete 2,400-second evaluator path.
- No account key or live free credits have been verified; project third-party provider cost remains zero only because there has been no paid request or plan.
- The syntactic four-slot budget helper does **not** prove all actual production request paths are charged, especially mixed registry/H1c/secondary identity branches, redirects, failures, global workforce calls and timeouts.
- No rights permission from Tavily authorises publication of **provider-specific** performance analysis. Public summaries must be provider-agnostic.
- V8/main remain immutable and previously unused independent qualification sets must remain sealed.

## Next actual action, in order

1. The user signs up for / accesses a **Tavily Researcher Free** account at https://app.tavily.com/ (do not put the API key in messages). Confirm zero billing exposure and available Basic Search credits. If requesting extra student credits, use an institutional email or send student credentials **privately to Tavily support**, not via public GitHub.
2. Verify precisely how the Builderr evaluator executes this application and whether it can receive a server-only `TAVILY_API_KEY` secret. If not, the provider-dependent version is **not evaluator reproducible** and may remain a developer-only experiment.
3. Only after account/evaluator prerequisites are confirmed, build a separately reviewed and **explicitly activated** pilot runner with a real request ledger. It must reserve one search + at most two homepage logical requests **inside existing four site slots** for eligible seedless companies; reserve charges *before* network sends and fail closed on 429/quota exhaustion, provider timeouts or insufficient remaining global wall time.
4. Run only the pre-frozen **already-consumed** 20-company development list in PR #174, audit every newly proposed exact-company site against directly fetched legal-entity identity and page provenance. Predeclared advancement gate ≥2 net new exact websites/20, zero wrong-company matches, zero lost prior valid claims, no evaluator contract regressions.
5. If successful, run one separate **already-consumed, zero-overlap** 100-company transfer gate, then fresh qualification only after material improvement proven. No production merge or claims before this.

Decision: **M25 engineering scaffold complete in draft only; account/key and exact integration still pending.**
