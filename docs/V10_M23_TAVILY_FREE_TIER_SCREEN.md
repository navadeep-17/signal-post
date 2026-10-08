# V10 M23 — Tavily free-tier domain nomination: offline-only preparation

Date: 2026-10-08  
Decision: **OFFLINE ADAPTER ONLY / LIVE RIGHTS GATE UNRESOLVED / NO PRODUCTION PROMOTION**  
Base: `release/v8-qualified-2026-10-06` at `200f056a5a60cad23610a3958b6bec62dfb624a5`

## Purpose

M21 proved on 300 previously consumed companies that exact-site reach—not re-tuning contact projection—is the bottleneck: 41/300 verified websites, 259/300 missing verified websites. M22 found a hypothetical four-site-slot search replacement (2,000 conservative requests/100) but SerpApi Free's 50 searches/hour cannot service 100 possible unresolved companies inside the 45-minute evaluator window.

M23 identifies a *different free-tier candidate* and tests only the **nomination and identity boundary** offline. No provider API, Norwegian company endpoints, company websites, or fresh cohort are queried by this milestone; no new claims are published.

## Official Tavily offering (reviewed 2026-10-08)

| Parameter | Published fact | Implication |
|---|---|---|
| Researcher Free | 1,000 API credits/month, no credit card | A basic 100-search cohort is within the nominal monthly quota **if** credits remain and the evaluator can use the account. The amount is not a reservation or access guarantee. |
| Basic Search | 1 credit/search | Request `search_depth=basic`; no answer or raw-content extraction. |
| Development API key | 100 requests/minute | Unlike SerpApi Free's 50/hour, this is not an obvious throughput disqualifier; 45-minute worst-case end-to-end performance still needs proof. |
| Production API key | 1,000 requests/minute | Published rate; no entitlement or production key is assumed. |
| API endpoint | `POST https://api.tavily.com/search` | Bearer token in server-side header. Query and `results[].url/title/content` are *transient* nominee data. |
| Response behavior | `results[].score`, raw content, answer, response timing, usage may appear | Provider search output is **never evidence or a company claim**; adapter discards unused fields and returns only aggregate-safe screen metadata. |

Primary provider documentation:
- https://www.tavily.com/pricing
- https://help.tavily.com/articles/6938147944-basic-vs-advanced-search-what-s-the-difference
- https://help.tavily.com/articles/3240802908-rate-limits
- https://help.tavily.com/articles/9170796666-how-can-i-create-an-api-key
- https://docs.tavily.com/documentation/api-reference/endpoint/search

## Rights and evaluator reproducibility **are not cleared**

Tavily's official **Platform Terms of Service (last updated May 4, 2026)** grant limited use with a customer application for internal business purposes and call out restrictions including:

- §3.2(x): no disclosure to a third party of performance information or analysis concerning Tavily's services. We cannot confidently claim this permits reporting retrieval-provider performance within public Builderr benchmark/audit material.
- §3.2(v)/(vi): no accessing the services to build a competing search product or competing with Tavily; Signalpost is an end-user company intelligence application, but intended use should be confirmed.
- §3.2(viii) allows reasonable gathering using Tavily APIs in accordance with the agreement (it does **not** authorize prohibited scraping or other uses).
- §2 disallows making the API key available to third parties without written permission. The exact Builderr evaluator's deployment/secret injection arrangement must be verified before promising evaluator reproducibility.
- §§6.5/9.2 permit Tavily and certain providers to process/retain customer inputs for development/training. Only publicly registered entity name, organisation number, and municipality should enter a potential query; no private user content.
- Any account/order-form or supplementary terms may control permissible quota and use.

**Conclusion: HOLD for written/contractually documented permission or a qualified legal determination covering this particular competition, third-party evaluation outputs, and evaluator API-key mechanics.** This is an engineering risk review, not legal advice.

Official terms: https://www.tavily.com/terms

An existing ChatGPT Tavily plugin connection does not make an API key available to the evaluator or make its account terms automatically applicable to the standalone code.

## Implemented strictly offline

`src/norway_company_agent/tavily_offline_candidate.py` is a fixture-only, no-network candidate adapter:

1. Derives the strict legal name + orgnr + municipality query from existing V8 code.
2. Shapes a basic, 1-credit-per-search request with answer/raw content/images disabled.
3. Converts only up to 10 provider result URL/title/content fields to *transient* shared H1b candidate-score input; drops search output scores, answers, raw content and images.
4. Reuses the existing shared candidate scorer to reject company directories/social networks and weak name-only brand/acronym matches. A nominated URL is **not published**.
5. Requires a previously fetched page record explicitly tied by its `requested_url` to the candidate. In the fixture screen it reuses the real V8 independent website identity gate and H1b page-proof gate, rejects conflicting organisation numbers, applies registry/foreign-entity risk rules, and then marks it only **eligible for future manual review**.
6. Returns only small audit flags: no raw provider result content, no orgnr, **zero published claims**, and zero network requests. It does not edit or invoke the production V8 runner.
7. `ProviderPrerequisites` defaults to all false and does not contain a live search client; current authorization always remains false.

`tests/test_v10_m23_tavily_offline_candidate.py` exercises strong/weak results, missing independent page, wrong candidate-to-page provenance, explicit different orgnr, directory pages, parent/group pages, holding-company and foreign legal entity traps, no-site/blocked-site cases and no provider-data persistence.

An offline all-green test run proves only that the synthetic boundary behaves as coded. No actual new verified sites, provider latency, safety at corpus scale, source rights or official score are established.

## Request theorem and important non-claims

The unchanged V8 worst-case per 100 is 100 × (5 official + 4 site) + 1 Wikidata + 97 workforce + 1 changes + 1 support = **1000 logical × 2 conservative = 2000/2000**.

M22's model showed one search + one independently fetched (robots+page) candidate may fit **within the existing four site slots**, at a cost of 1 + 2 = 3 logical, **only by substituting for other fallback requests**. M23's offline screen records three reserved site logical slots for that path, but is **not wired into V8** and **does not prove the complete runner's request cap, no regression from lost H1c sites, or 45-minute runtime**.

Naively adding search and crawl outside existing slots would require 2,600 conservative requests/100 and is forbidden.

## Next gate, no exceptions

Before any live Tavily call or query of even already-consumed company data, obtain and record:

1. Provider terms clearance for competition-style evaluation and public reporting, plus the relevant provider-plan rights, **including explicit clarification of §3.2(x)**.
2. A reusable server-side API key, established through the proper deployment secret mechanism; do not post any token in a PR, file or conversation.
3. Written evaluator access terms: who owns the account, whether the Builderr evaluator can call it under Tavily §2, monthly credit availability and reset reproducibility.
4. No-charge free plan confirmed **for the entire pilot and evaluator**; no pay-as-you-go enabled, fail closed on quota exhaustion.
5. Predeclared fully counted live request-slot substitution, realistic provider latency/rate errors, global 2400-second bound, independent page fetch and manual publication precision audit.
6. Then freeze 20 **already-consumed development** org numbers; target ≥2 net new independently qualified sites/20, 0 lost previously qualified sites, 0 wrong legal entities, 0 new claim regressions, full 100% manual review. A successful pilot still needs disjoint 100 transfer and fresh qualification.

**No live provider call is authorized by this research PR; keep all production and existing holdouts intact.**

## Suggested permission clarification (do not send without the user's direction)

Subject: Tavily Search API use in a Norwegian company-intelligence competition

We are considering Tavily's basic Search API solely to discover candidate public company URLs for a Norwegian organisation-number-indexed company intelligence application. We would independently fetch websites and require exact legal-entity proof before publishing any facts. Search snippets/ranks would not be displayed or retained as evidence. The application is evaluated in a third-party software challenge, which may include public aggregate reports about our application and its external data coverage.

Could you confirm in writing whether this use is permitted on the Researcher Free plan, especially with respect to Terms §3.2(x) on disclosure of performance information? Can our independently operated evaluation runner use a project API key managed as a server-side secret, or would the evaluator require separate written permission under §2? Are there additional restrictions on a third-party evaluator executing 100 basic searches per batch or on subsequent public release of the underlying project? We do not seek access to non-public data, caching of search results, or crawling your service.
