# V10 M22 — Domain Search Provider Feasibility and V8 Request-Allocation Screen

Reviewed: 2026-10-08  
Decision: **CONDITIONAL RESEARCH ONLY / NO LIVE CONNECTOR / NO PRODUCTION PROMOTION**  
Production parent: immutable qualified V8 `200f056a5a60cad23610a3958b6bec62dfb624a5`

## Why this milestone exists

M21's reproducible 300-company diagnostic found 41 verified websites, 259 without a verified website, 25 companies with qualifying social profiles, 22 with contact emails, five with careers pages and zero with active job postings. Existing .no guessing has negligible additional recall. M19 and M20 were both shelved under their own disjoint transfer gates. M22 asks whether an actually different, **licensable org/name → candidate homepage search signal** could justify a new consumed-development experiment.

This is a read-only source/terms analysis and static budget feasibility certificate. We **did not execute** an external search-provider request, collect Norid data, run a new company acquisition, consume M20 Gate B, or authorize a fresh cohort.

## Sources screened (primary sources)

| Candidate | Technical relevance | Policy, cost and access finding | Decision |
|---|---|---|---|
| **SerpApi Google Search API** | Existing exploratory adapter in `scripts/run_search_discovery.py`; transient organic URL/title/snippet candidates, independent first-party fetch and strict page-only proof. | Published general terms and pricing do not show Brave's explicit AI-service benchmark prohibition, **but are not account-specific legal clearance**. Free plan: 250 searches/month and **50/hour**; Starter: **$25/month**, 1,000 searches/month, 200/hour. Ordinary search-data retention 31 days. No `SERPAPI_API_KEY` or declared account-level cost/rights attached to the evaluator. | **Best conditional integration reuse; live evaluation BLOCKED** until legal use, account, repeatability, $0 policy and runtime are resolved. |
| **SerpApi Search Index (preview)** | Distinct 6-billion-page in-house search index and API engine `search_index`; a new provider **engine** but not evidence that it finds more exact Norwegian company sites. | Described by SerpApi as suitable for benchmarking; preview/endpoint semantics may change. Uses the same provider account/credits; no measured Norwegian random-company site lift. | Offline-only candidate; no trial without same credential/rights gates. |
| **Exa Search API** | Broad web/company index; nominal search price ~$4–$7/1,000 and free monthly credits; developer API-key independent of the connected ChatGPT plugin. | Published Exa ToS §4.2(a) restrict copying/downloading information obtained through the service absent permission, and §4.2(f) restricts development of competitive products. Scope of transient domain nomination into this particular benchmark is **not clearly licensed** by those terms alone. No independently usable `EXA_API_KEY` present for evaluator. | **HOLD** pending written permission on the exact workflow and supplied evaluator credentials. ChatGPT plugin connection ≠ evaluator API key. |
| **Brave Search API** | Technically suitable search endpoint; $5/1,000. | Standard Search API terms §3(b)(xiii) prohibit using Search Results to evaluate/benchmark AI models or services. | **NO-GO** under reviewed terms without bespoke written permission. |
| **Norid .no domain directory/RDAP** | Technical org-number → registered-domain path. | Directory bans commercial reuse and bulk extraction; RDAP inverse identity lookup is registrar-scoped. | **NO-GO**; do not scrape. |
| **Brreg mirrors / firm data APIs** | orgnr → `hjemmeside` registered site. | Licensed registry field is already used by Signalpost; repackaging Brreg does not demonstrate new independent domain reach. | **NO NEW RECALL HYPOTHESIS**. |
| **Common Crawl URL Index** | Open Parquet index of crawl URL/registered-domain; available for bulk analysis. | URL index alone cannot query arbitrary organisation-number mentions in body text without scanning WARC content at scale. Previous project Common Crawl pipeline found 2 additional exact sites for 5,900 consumed. | **DO NOT REPEAT** prior large WARC crawl unchanged. |

### Direct reviewed references

- SerpApi general terms (27 Aug 2026): https://serpapi.com/legal
- SerpApi free/Starter quotas: https://serpapi.com/pricing
- SerpApi Google endpoint: https://serpapi.com/search-api
- SerpApi Search Index preview: https://serpapi.com/search-index-api
- Exa official terms PDF, §4.2 (rights restriction; written permission path): https://exa.ai/assets/Exa_Labs_Terms_of_Service.pdf
- Exa official API pricing: https://exa.ai/pricing
- Brave Search API terms §3(b)(xiii): https://api-dashboard.search.brave.com/documentation/resources/terms-of-service
- Brreg open data, NLOD: https://www.brreg.no/en/use-of-data-from-the-bronnoysund-register-centre/datasets-and-api/
- Common Crawl URL Index: https://commoncrawl.org/url-index
- Norid review already in `docs/V10_M21_NORID_RIGHTS_SCREEN.md` on M21 draft PR #171.

The terms are source-specific engineering/legal-risk findings, not formal legal advice. Verify account-specific provider terms *at the point of actual implementation*.

## A real blocker: SerpApi free-tier throughput

A 100-company random cohort can have **100 missing websites**, so a proposed one-search-per-eligible-company policy must be safe at 100 queries. A published limit of **50/hour** is not a 100-query guarantee inside the evaluator's **45-minute** wall-clock cap; it is insufficient even if all other Signalpost work takes zero time. Starter's 200/hour is more plausible, but it incurs a fixed monthly payment and is not consistent with the project's current $0 third-party-cost policy. A *paid plan's* amortized rate is not proof of zero API cost or free evaluator access.

This is a worst-case feasibility screen, not an inference that 100 searches actually occur in typical cohorts. Search volume, per-request latency and acquisition runtime must be profiled live on the exact permitted plan, with headroom and fail-closed timeouts. Free-tier credits also have monthly/account state and cannot be presumed to refresh for Builderr.

## Rigorous conservative request accounting

Qualified V8 per 100-company structural ceiling:

```text
100 companies × (5 official + 4 website) = 900 logical
Shared Wikidata                              =   1
Annual workforce reservation                =  97
BRREG changes (shared)                      =   1
Støtteregisteret (shared)                    =   1
-----------------------------------------------------
MAX logical                                  = 1000
Conservative charge (1 redirect/request)    = 2000 / 2000
```

Naively appending **one provider request + a two-logical-request robots/homepage fetch** for every company would produce `(1000 + 100×3)×2 = 2600` and break the ceiling. Merely removing H1g without accounting for the replacement homepage crawl is **not** a proof.

A **hypothetical structurally safe allocation** is possible **without adding an unconditional request family** by replacing the existing low-yield deterministic fallback calls *within* the four already-reserved website slots, rather than appending calls to the qualified runner:

- Registry-linked site (or qualified BRREG email-domain candidate) keeps its original first priority; no search after a full two-request failed attempt. Preserve the remaining current website slots and unknown status.
- Only for profiles with no registry/email site seed: at most **one search** (1 logical); if a domain candidate is nominated, at most one independent bounded first-party homepage crawl (2 logical). Total **3 of 4 website slots**. If the page lacks enough identity proof, abstain; a two-request secondary corroboration would exceed the four-slot cap and is not permitted.
- If search returns no acceptable crawl candidate: allow the existing H1c homepage candidate within the remaining capacity (1+2=3); disallow H1c secondary and H1g when those would exceed four.
- Search title/snippet/rank is always *transient*; it can nominate a crawl, never become a company claim. Existing owner-veto, exact-entity, source rights and evidence guards remain mandatory.

`scripts/audit_v10_m22_search_slot_budget.py` checks all eight enumerated branch patterns, validates the exact 2,000 ceiling, and intentionally demonstrates the invalid 2,600 naive scheme. **This is only an abstract allocation proof.** It does *not* prove that an edited production runner enforces those slots; implementing the semantics would require focused tests, a new exact-code request theorem, worst-case runtime tests, and a disjoint precision qualification. It may trade away valid H1c sites or secondary corroboration. No source/score lift is claimed.

## Next allowable step — provider qualification gates

1. Obtain explicit approved provider account/plan plus a separately configured evaluator-usable API key and accurate price accounting. Confirm whether the exact benchmark-related transient domain nomination is authorized. Do not place secrets in Git or chat.
2. Resolve the **$0** local project policy against the provider's quotas and subscription. A plan exceeding that policy needs explicit approval before use, even if under challenge's maximum allowable spend.
3. Measure the exact provider's 100-query throughput/rate-limit and 45-minute worst-case envelope; compute fallback and provider-error behavior under bounded timeouts. Do not infer viability from average throughput alone.
4. Only then freeze a **10–20-company already-consumed development screen** from allowed material. Pre-register gross and net verified-site uplift, full precision audit, lost prior sites, request charging and costs. Minimum advancement suggestion: at least **2 net-new independently qualified exact-company websites / 20** *and* no wrong-company publications, no lost baseline claims or downstream semantic regressions. A short pilot alone cannot justify fresh qualification.
5. After a successful development screen, freeze a disjoint consumed 100 cohort and later a genuinely untouched cohort only when the previous gate passed. Manual audit 100% of any new published external evidence.
6. Keep **qualified V8/main immutable** and all PRs **draft**, with no new provider calls or production merge unless these gates are met.

## Decision

**NO-GO for live provider search today.** SerpApi remains the least invasive conditional technical candidate because Signalpost already has a search nomination scaffold, but the **published free throughput is incompatible with all-100 worst-case 45-minute delivery**; paid access conflicts with the local $0 policy. Exa lacks sufficient permission certainty; Brave/Norid are unsuitable under reviewed standard terms. The site-slot accounting has a conditional safe option **only as a design**, without measurable recall evidence.

No production commits, external search calls, additional API costs, manual company audits or fresh qualification took place in M22.
