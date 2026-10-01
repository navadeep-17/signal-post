# V6 public competitor teardown

Date: 2026-10-02

Scope: public GitHub repositories and public vendor/challenge information only. No private competitor work, no evaluator internals, and no attempt to infer hidden reference data.

## Executive conclusion

The strongest repeatable public signal is **not “add every connector.”** It is:

> **Aggressive candidate discovery, conservative exact-company publication, then bounded first-party extraction only after the site is proven.**

Our V5 fresh-100 has excellent official-data coverage but only **7 verified websites / 100**, **4 companies with contact email**, **2 with social handles**, and no strict jobs or company-authored updates. Its observed conservative request charge was **1,382 / 2,000** and its site-discovery mix was 3 registry websites, 1 registry-email-domain site, 3 deterministic `.no` sites, 0 Wikidata sites and 93 unresolved companies.

The public implementations with the clearest measured website gains all widen *discovery* while retaining an independent identity gate:

- **AnSa30-06/signalpost-norway**: registry website -> registry email domain -> deterministic `.no/.com` guesses -> optional Brave fallback -> independent exact-company gate -> bounded first-party crawl. Revision 4 measured 110 exact websites / 1,000 without Brave. Earlier provisional Builderr evaluations were high but were blocked by wrong-company websites; later identity hardening explicitly removed domain/name-only proof.
- **vishwajitpatil5144-cloud/Signalpost_builderr**: wider `.no/.com` name permutations + fetch resilience increased a documented fresh-100 discovery result from 27 to 34 verified websites (+7) at $0; their enhanced first-party extraction reported 3 hiring signals and 6 site-news signals. Their current public-board score supplied by the project owner is nevertheless only about 42.29, so the presence of NAV/Wikidata/Nominatim/site crawling does not by itself prove hidden-evaluator recall.
- **ashokwebs/signalpost-agent**: legal-name `.no/.com` candidates measured +28 verified sites on the first 200 companies (17 -> 45), still behind an identity gate.
- **biswajeetdev/signalpost-agent**: broader full/partial name labels across `.no/.com`, registry email-domain uniqueness checks, and bounded site crawling; its published 1,000-company artifact reports 225 verified websites, but its older identity gate accepts some evidence routes that are looser than our current safety standard, so candidate generation is interesting while publication logic should not be copied.

The highest-value V6 move is therefore to improve candidate nomination **without weakening the V5 publication gate**. The first implementation should be a bounded, zero-cost candidate expansion / fetch-resilience experiment. Search-assisted discovery remains the next high-value experiment, but public repositories do not yet provide a clean measured Brave-backed recall result, and a production benchmark needs an API key.

## Repository search census

Broad GitHub repository searches found the following public Signalpost/Builderr implementations or starter derivatives:

1. `AnSa30-06/signalpost-norway`
2. `vishwajitpatil5144-cloud/Signalpost_builderr`
3. `ashokwebs/signalpost-agent`
4. `biswajeetdev/signalpost-agent`
5. `officialarghya29/kildespor`
6. `TusharTechs/fotavtrykk`
7. `akayyt786/signalpost-agent`
8. `Rakesh-Tummala/signalpost-company-agent`
9. `mayuresh-1979/signalpost`
10. `DanKam0001/signalpost-agent`
11. `Balram-1/signalpost-norway-agent`
12. `martyn-in/signalpost-agent`
13. `divyanshAgarwal123/signalpost-company-research-agent`
14. `iamjaydatt2006/signalpost`
15. `divya683/signalpost-agent`
16. `DG10911/signalpost-agent`
17. `softpeanut/signalpost-agent`
18. `mmansii/builderr-signalpost`
19. `24f1000587/signalpost-company-agent` (empty at review time)

The last five non-empty repositories in the list are close to the published starter architecture or expose little measured external-recall differentiation. They are included below but are not treated as independent evidence that a technique improves recall.

## Master architecture matrix

Legend: `Y` implemented/documented, `O` optional/experimental, `N` absent/not documented in reviewed public material, `B` essentially starter/baseline behavior.

| Repository | Website discovery | Search API | Domain generation | Exact-company gate | First-party deep crawl | NAV jobs | News/RSS/sitemap | Social/contact | Structured data | Refresh/evidence | Public measured external result |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Our V5** | registry + email domain + compact `.no` + hyphenated `.no` + Wikidata | N | narrow | exact org / full legal name + strong BRREG corroboration; conflict guard | very shallow retained pages | N production jobs | strict projection only; effectively 0 news | Y, homepage/retained page only | JSON-LD org extraction | strong | **7/100 sites, 4/100 email companies, 2/100 social companies, 0 jobs/news** |
| **AnSa30-06** | registry + email + `.no/.com` guesses + Brave fallback | **Brave O** | compact, hyphen, first token; `.no/.com` | strongest reviewed: orgnr OR exact legal name + strong address OR registry-filed domain + name; multiple wrong-company caps | **Y** bounded prioritized pages | **Y**, parent or official subunit orgnr | **Y RSS + sitemap + dated page/news** | **Y** | **Y** JSON-LD/microdata | very strong | R4: **110/1000 exact sites**, 4 NAV jobs, 9,877 req, $0 without search |
| **Vishwajit** | registry + expanded deterministic candidates | N production | `.no/.com`, municipality/partial variants | orgnr / name-based gates + liveness/parking guards | **Y** careers/news/leadership | Y | Y site news | Y | Y | strong | documented enhanced 100: **27 -> 34 sites**, hiring 1 -> 3, news 5 -> 6, $0 |
| **Ashok** | registry email + legal-name domains | N | `.no/.com`, max 3 | orgnr or same-domain/legal-name routes | Y | Y index | **Y RSS + HTML news** | Y | partial | strong | first 200: **17 -> 45 sites (+28)**; 1,000 run 5,982 req |
| **Biswajeet** | registry + email + full/partial labels | N | `.no/.com`, two Norwegian folds, full + partial labels | older name/org gate; shared-domain guard | bounded contact/about pages | N | N | Y | Y | strong | 1,000: **225 sites**, 259 social profiles; 5,745 req, $0 |
| **Fotavtrykk** | registry/site + batch external connectors | N documented | not established in reviewed README | orgnr proof; address/phone corroboration; inferred tier dropped | Y | Y | Y company activity | Y | Y | strong audit framework | 1,000 representative run: 5,320 req; external families sparse; warns audit-set coverage overstates random coverage |
| **Kildespor** | primarily registry-listed website | N | N | three strict gates: registry domain / orgnr / name+address | limited | token-dependent NAV | N | limited | Y | strong | 1,000: website **8.6%**, jobs 0 public tier, ~2 requests/company |
| **Akayyt** | registry -> email -> DIBK/Wikidata/NAV refs -> DNS name guess | N | Y last-resort | orgnr or exact legal name + address/phone; conflict hard reject | Y | **Y exact ad orgnr** | company-site activity; Google News disabled | Y | Y | SQLite claim/evidence store | no comparable official score in reviewed public material |
| **Rakesh** | registry + optional search providers | **Tavily/Exa O** | starter + search | exact-entity publication gate | Y | O | Y | Y | Y | strong saved-snapshot evidence | fresh 100 documented 647 req / 422 s / $0 default; search coverage unmeasured |
| **Mayuresh** | verified candidate websites | N documented | not established | strict exact-entity | limited | audited connector files exist | audit docs mention hiring/reviews | Y | Y | strong | 1,000 6,121 req; local proxy 56.869, not official |
| **DanKam** | registry + own website | N | not documented | orgnr or legal name + address/phone | **Y** description/social/careers/jobs/news | N documented | Y site news | Y | Y | strong | web inaccessible in dev smoke; external recall not measured |
| **Balram** | BRREG + Playwright site discovery | N | not clear | Jaro-Winkler + postcode, LLM extraction | Playwright | Y | LLM/site | LLM | LLM schema | bi-temporal SQLite | 100-company benchmark says 100 req / 3.75 min, but proxy + LLM architecture has higher reproducibility/precision risk |
| **Martyn** | official declared website / priority subpages | N | limited | conflict-org + foreign/parked guards | limited | N | N | N | Y | strong | benchmark mostly offline snapshot; external recall not measured |
| **Divyansh** | registry + optional Brave/Tavily-like licensed path | **Brave O** | starter + provider candidates | independent fetched-page gate | Y | O NAV | Y | Y | Y | strong | fresh 100: 647 req / 422s / $0 default; search unmeasured |
| **Iamjaydatt** | starter + company-site enrichment | connectors gated | starter | starter | Y | disabled unless rights accepted | site activity/news | limited | starter | strong | no comparable external-coverage benchmark found |
| **Divya683** | starter baseline | N | B | B | B | N | N | B | B | B | no external-yield delta documented |
| **DG10911** | starter baseline | N | B | B | B | N | N | B | B | B | no external-yield delta documented |
| **Softpeanut** | starter baseline | N | B | B | B | N | N | B | B | B | no external-yield delta documented |
| **Mmansii** | starter baseline | N | B | B | B | N | N | B | B | B | no external-yield delta documented |

## Detailed 28-point profiles

### 1. AnSa30-06/signalpost-norway

1. Website discovery: registry `hjemmeside`, registry email domain, legal-name guesses, optional Brave fallback.
2. Search API: optional Brave Search API.
3. Domain generation: normalized legal tokens; compact/hyphen and selected first-token forms; `.no` and `.com`; at most four guesses.
4. Exact-company verification: final strict routes are target org number; exact legal name + strong registered address; or registry-linked domain + complete legal-name evidence. Multiple other org numbers, group/listing pages and another company named as page owner cap to ambiguous.
5. BRREG endpoints: entity, accounts, roles, subunits, group, updates, annual-account years/copies.
6. Financial sources: BRREG Regnskapsregisteret with up to multiple periods.
7. Annual-report extraction: filed-account copies are part of the architecture; public docs emphasize accounting periods rather than OCR as a primary external discovery source.
8. Workforce: registry employees plus official sources.
9. Leadership: BRREG roles plus leadership extracted from verified site pages.
10. Locations: BRREG subunits plus structured/site locations.
11. NAV jobs: yes; builds a shared active-feed index and accepts exact parent orgnr or an official BRREG subunit orgnr.
12. Careers-page extraction: yes, but generic careers pages are explicitly not job postings.
13. Company news: yes, dated first-party news pages.
14. RSS: yes.
15. Sitemap: yes; sitemap URLs inform targeted pages and newest `lastmod` activity.
16. Social: links / JSON-LD `sameAs` only from verified site.
17. Contact: same-domain email and Norwegian phone from verified site.
18. Structured data: JSON-LD + microdata + OpenGraph.
19. Search-result candidates: yes, transient Brave URLs only; result content is never evidence.
20. Evidence architecture: stored snapshots, hashes, verbatim spans, explicit absence states.
21. Refresh/change: typed diff; source failures do not become fake removals.
22. Requests: R4 published 9,877 / 1,000; 100 smoke 1,153.
23. Runtime: R4 36.2 min / 1,000; smoke 5.7 min / 100.
24. Cost: $0 without search; public estimate about $4–$7 / 1,000 with Brave depending unresolved count.
25. Reported performance: early Builderr provisional 74.67 then 69.57 in an older scoring phase; both had wrong-company site failures. R4 public local run: 110 exact websites / 1,000 and four NAV jobs.
26. Failure modes: group sites, chain sites, company mentions on third-party pages, `THE FJORDS DA -> fjords.com`, pages with several org numbers, one-word namesakes.
27. Has that V5 does not: `.com` candidates, optional search fallback, sitemap/RSS, deep first-party page crawl, site leaders/locations/phones, NAV subunit mapping.
28. V5 has that it does not: our qualified annual-report OCR workforce layer reaches ~98%; our current canonical projection / BRREG registry-change layer is more central and already qualified under our own test discipline.

### 2. vishwajitpatil5144-cloud/Signalpost_builderr

1. Website discovery: registry + deterministic domain permutations.
2. Search API: production claims zero paid search.
3. Domain generation: expanded normalized `.no/.com`, Norwegian transliteration, compound/hyphen, municipality-stripped/partial variants.
4. Verification: org number / legal-name evidence plus liveness, short-acronym and foreign-grounding guards.
5–10. Official foundation: BRREG bulk/live, accounts, roles, subunits/group; OSM and Wikidata extras.
11. NAV: yes.
12. Careers: yes, including outbound ATS signatures.
13. News: yes.
14–15. RSS/sitemap: not a defining measured feature in reviewed public docs.
16–17. Social/contact: yes from company-site extraction.
18. Structured data: yes.
19. Search-result discovery: not production.
20–21. Evidence/refresh: hashed evidence and idempotent diff.
22. Requests: README reports 5,660 for submitted 1,000; fresh 100 target <600; experiment domain discovery 347 outbound probes.
23. Runtime: enhanced 100 33m58s; README fast benchmark around 13m for another 100 run.
24. Cost: $0.
25. Measured gains: enhanced discovery 27 -> 34 websites on 100 (+7); enhanced full run published 25 websites vs 18 baseline in its envelope comparison, hiring 1 -> 3, site news 5 -> 6.
26. Failure modes: SSL hostname mismatch, 403/WAF, dead TCP candidates, short acronym collisions, parked domains, foreign namesakes, generic real-estate path false positives.
27. Missing in V5: broader `.com`/partial candidate set, HTTP/SSL resilience, richer bounded careers/news page discovery.
28. V5 strengths over it: stronger current exact-company hardening from our false-positive history; much higher workforce via official annual reports; strong official registry-change feed.

### 3. ashokwebs/signalpost-agent

1–4. Registry/email/legal-name website discovery with `.no/.com` guesses behind exact identity gating.
5–10. BRREG official registry/accounts/roles/subunits/group; no distinctive annual-report OCR advantage documented.
11. NAV feed index: yes.
12. Careers: yes in roadmap/connector evolution.
13–15. Dated company activity: RSS/Atom and HTML news/nyheter/aktuelt.
16–18. Social/contacts/structured page evidence supported by starter-derived site layer.
19. Search API: explicitly none.
20–21. Evidence + refresh retained from strong starter architecture.
22. 1,000 run: 5,982 requests.
23. Runtime not central in reviewed README.
24. $0.
25. Measured website gain: +28 on first 200 (17 -> 45) from legal-name candidates.
26. Risks: name-token proof can still be weaker than our V5 gate; we should borrow nomination strategies, not publication thresholds.
27. Missing in V5: `.com` candidate layer; RSS/HTML-news extraction.
28. V5 ahead: workforce and official change coverage.

### 4. biswajeetdev/signalpost-agent

1. Website discovery: registry URL, registry email domain, deterministic full/partial labels.
2. Search: no.
3. Domain generation: `.no/.com`; two transliteration mappings; full core/name forms and partial first/last sequences.
4. Gate: name/org evidence; shared registry email domains marked administrator/group when used by >=5 registry entities.
5–10. BRREG bulk caches for entity, roles, subunits; live accounts.
11–15. Jobs/news/RSS/sitemap: not production in reviewed README.
16. Social profiles: links from verified website.
17. Contact: registry email/phone/site evidence.
18. Structured data: yes.
19. Search candidates: no.
20–21. Evidence + refresh: strong terminal contract and resumable chunking.
22. 1,000: 5,745 requests; 100 measured 599.
23. 100 ~4 min; 1,000 ~40 min.
24. $0.
25. 1,000 reports 225 verified websites and 259 company-linked social profiles.
26. Known limits: per-company website allowance exhausted on 39/1,000; older identity routes are looser than our current V5 safety bar.
27. Missing in V5: wider candidate generation and registry-wide email-domain reuse count.
28. V5 ahead: annual-report workforce, official change activity, stricter company-site publication guard.

### 5. officialarghya29/kildespor

1–4. Registry-first website with G3 registry URL, G1 org number, G2 legal-name + address gate; no aggressive search discovery.
5–10. Entity + accounts; limited external breadth; workforce mostly registry.
11. NAV architecture present but public feed was treated as unusable for exact orgnr without token in that implementation.
12–19. Little first-party breadth compared with Anmol/Vishwajit; no search API.
20–21. Excellent evidence and typed diff architecture.
22. ~2 requests/company on published 1,000 run (2,015 total stated).
23. Not a bottleneck.
24. $0.
25. Website 8.6%, jobs 0 in measured public run.
26. Low recall deliberately accepted for precision.
27. Missing in V5: little high-value discovery not already covered.
28. V5 ahead: wider website nomination, annual workforce, roles/locations breadth, registry changes.

### 6. TusharTechs/fotavtrykk

1–4. Identity proof rooted in orgnr; inferred/name-only tier was measured and removed after 84% exact precision in its audit.
5–10. BRREG foundation; multiple external connector experiments.
11. NAV exact-org connector.
12–15. Company activity connector; broader external/news concepts, no evidence that generic third-party buzz solves random-company recall.
16–18. Wikidata and declared handles; site-derived dependents inherit root proof.
19. Search API not a primary architecture.
20–21. Strong risk-weighted audit and typed change system.
22. Representative 1,000 run reports 5,320 requests.
23. ~4 minutes reported for that artifact.
24. Artifact reports $35 when Google Places was enabled, which exceeds our desired $10 evaluator budget and should not be copied.
25. Important empirical result: representative random-company external coverage was much lower than the web-heavy audit corpus; workforce/jobs remained 0 in the shown representative table.
26. Failure mode: registry/name-only website roots cascade errors into social observations; this is why the inferred tier was dropped.
27. Missing in V5: mature risk-weighted external-identity audit methodology; possible TED/places-like connectors are lower priority.
28. V5 ahead: much lower cost, higher workforce, official changes, already-safe site publication.

### 7. akayyt786/signalpost-agent

1. Registry -> email -> DIBK/Wikidata/NAV cross-reference -> DNS name guess.
2. Search API: none by default.
3. Domain generation: last-resort DNS-verified legal-name guess.
4. Gate: org number or legal name + registry address/phone, hard reject conflicting org numbers; single-token names require orgnr.
5–10. BRREG core.
11. NAV exact employer orgnr with live detail re-check.
12–15. Company-site public activity; Google News RSS exists but disabled pending precision audit.
16–18. Site social/contact and structured data; DIBK/Wikidata exact-ID references.
19. No search-result discovery.
20–21. SQLite claims/evidence/current-state and careful deferred refresh.
22–24. Budget-aware, $0 by default.
25. No comparable public official score found.
26. Explicitly avoids restricted platforms and disables unqualified Google News connector.
27. Missing in V5: DIBK/TED exact-ID external facts; better budget-pressure ladder.
28. V5 ahead: stronger measured official coverage; these extra sources have uncertain hidden-recall value.

### 8. Rakesh-Tummala/signalpost-company-agent

1. Registry + candidate discovery + optional search-provider path.
2. Optional Tavily and Exa for website discovery.
3. Starter deterministic candidates plus search results.
4. Independent exact-company gate remains publication authority.
5–10. BRREG core + annual-report OCR workforce/prior-year finance.
11. Optional NAV.
12–15. Deeper site crawl and company-owned dated activity.
16–18. First-party signals and structured extraction.
19. Search results are candidates only.
20–21. Saved snapshots, exact spans, refresh carry-forward.
22. Fresh 100 default: 647 requests.
23. 422 s documented.
24. $0 default; search provider path cost-bounded but unmeasured in public fresh coverage.
25. No official Builderr score documented in README.
26. Search coverage still needs independent clean benchmark.
27. Missing in V5: optional broad search nomination.
28. V5 ahead: currently qualified internal production path and stronger current scorer-aligned canonical surface.

### 9. mayuresh-1979/signalpost

1–4. Verified company-site architecture; reviewed README does not expose a distinctive search/candidate method.
5–10. Very broad BRREG foundation including bulk roles/subunits and extra official registration/capital/VAT/purpose fields.
11–19. Repository includes hiring/review/external audit suites, but public README does not establish a high-yield external architecture result.
20–21. Strong evidence and refresh.
22. Historical 1,000 run 6,121 requests; 100 benchmark about 318–684.
23. 100 about 1.5–3.5 min.
24. $0.
25. Local optimization proxy 56.869, explicitly not official.
26. Main risk is breadth that may not map to hidden external-positive families.
27. Missing in V5: some extra official fields, low priority for our stated goal.
28. V5 ahead: workforce and official change feed; clearer external-recall bottleneck targeting.

### 10. DanKam0001/signalpost-agent

1–4. Registry plus own website; orgnr or legal name + address/phone proof.
5–10. Strong BRREG official foundation.
11. NAV not documented as a main source.
12–15. Site careers/jobs/news extraction described.
16–18. Social/contact/structured site extraction.
19. No search API.
20–21. Immutable snapshots and typed refresh.
22. 100 smoke 514 requests.
23. 47 seconds, but site egress was mostly unavailable in that environment.
24. $0.
25. External recall explicitly unmeasured.
26. Sandbox egress is the documented blocker.
27. Missing in V5: richer site-layer output once a site is known.
28. V5 ahead: live qualified external-site discovery and annual workforce/change coverage.

### 11. Balram-1/signalpost-norway-agent

1–3. BRREG-driven site discovery, Playwright/proxy browsing; domain/search details are not the main differentiator.
4. Jaro-Winkler name similarity >=0.80 plus postcode check before LLM-extracted facts.
5–10. BRREG identity/roles and NAV.
11. NAV yes.
12–18. Browser + LLM extraction from company websites.
19. No decisive search-API result documented.
20–21. Bi-temporal evidence/current-state SQLite.
22. Claimed 100 requests / 100 benchmark.
23. 3.75 min / 100, 33.49 min / 1,000.
24. OpenRouter/proxy credentials are required for intended architecture; reproducibility/cost depends on services.
25. No public Builderr score found in reviewed material.
26. Main risk: fuzzy name gate + LLM/proxy dependency is weaker than our exact-company standard.
27. Potentially richer extraction after site verification.
28. V5 ahead: deterministic identity, evidence, no private proxy dependency.

### 12. martyn-in/signalpost-agent

Mostly a strong official/snapshot baseline with identity guards, deterministic synthesis and UI. Public benchmark focuses on offline snapshot execution (317 accepted claims / 100 on one sample); external website/jobs/news recall was not established. No missing technique outranks candidate discovery for V6.

### 13. divyanshAgarwal123/signalpost-company-research-agent

Optional Brave discovery and NAV exist, but default fresh 100 is $0 and the README explicitly says registry-linked sites remain sparse and search coverage is unmeasured. Useful architectural confirmation, not empirical proof.

### 14–18. Iamjaydatt / Divya683 / DG10911 / Softpeanut / Mmansii

These public repositories retain large parts of the reference/starter architecture. Iamjaydatt adds bounded company-site activity/news connectors; the others do not document a measured external-recall change large enough to influence V6 priority.

### 19. 24f1000587/signalpost-company-agent

Empty repository at review time; excluded from technique scoring.

## Technique value ranking for our V6

| Technique | Rating | Why |
|---|---|---|
| **Broader deterministic domain nomination (`.com`, full-name variants, conservative partial variants)** | **HIGH VALUE** | Multiple public implementations report measured website gains; no third-party API cost. Keep our stricter V5 gate unchanged. |
| **Protocol/SSL/transient fetch resilience** | **HIGH VALUE** | Our fresh-100 already contains an SSL hostname-mismatch miss and several network failures; Vishwajit measured recoveries from this class. Must remain bounded and SSRF/robots safe. |
| **Brave search candidate fallback, transient results only** | **HIGH VALUE / NEEDS KEY BENCHMARK** | Likely solves brand-vs-legal-name cases that deterministic domains cannot. Public Brave price is low enough for a 100-company run, but the strongest public repo does not publish a key-backed recall measurement. Candidate fetch must pass our existing exact-company gate. |
| **Bounded first-party sitemap + targeted pages + RSS** | **HIGH VALUE once website coverage rises** | One verified site can unlock contacts, social, real JobPosting JSON-LD and dated updates. Anmol/Vishwajit show non-zero jobs/news. |
| **NAV parent/subunit exact mapping** | **MEDIUM VALUE** | Safe and real, but Anmol's 1,000-company result produced only four jobs; useful after web multiplier, not first. |
| **Registry-wide email-domain uniqueness / administrator detection** | **MEDIUM VALUE** | Improves ranking and reduces false positives for email-domain discovery at zero network cost. |
| **Wikidata exact P2333 extras** | **LOW–MEDIUM** | Very safe but sparse: our fresh 100 had zero website candidates; Vishwajit reported only 2/100 profiles on one benchmark. |
| **DIBK/TED exact-org external facts** | **LOW–MEDIUM** | Precise but unclear overlap with the hidden external-positive set; implement only after website multiplier. |
| **Nominatim/OSM geocoding** | **LOW VALUE** | High reach but likely duplicates location facts already strong in BRREG and did not rescue Vishwajit's current official recall. |
| **Generic careers-page-as-hiring** | **REJECT** | Challenge/evaluator expects concrete openings; all stronger repos explicitly separate generic careers from jobs. |
| **Name-only website promotion / fuzzy Jaro-Winkler root identity** | **REJECT** | Public wrong-company failures demonstrate unacceptable cascading precision risk. |
| **Google Places / broad ratings at current stage** | **REJECT for V6 priority** | Cost/rights and hidden-overlap uncertainty; Fotavtrykk's representative external coverage remained sparse while a $35 1,000 run exceeds our intended evaluator budget. |
| **LLM deciding company identity or official numbers** | **REJECT** | Adds a non-deterministic failure mode where exact identity is the disqualification risk. AI can later extract only after identity is fixed and spans are verified. |

## Brave feasibility under the current public budget

Current Brave Search pricing publicly states **$5 per 1,000 Search requests** and includes $5 monthly credits. A single query for each of 100 unresolved companies is about **$0.50 list price**; even two queries each is about **$1.00**, below a $10 run budget.

Request budget is more important than dollar cost. V5 fresh-100 observed 691 logical requests plus its conservative redirect accounting, with a reported conservative charge of 1,382 / 2,000. A V6 search path must be integrated into the **existing site-request slots**, not simply added to the theoretical ceiling. The preferred architecture is:

```text
registry-declared site (if present)
  -> otherwise strong official-domain candidate if worth the slot
  -> otherwise ONE search query
  -> choose at most one high-quality candidate URL transiently
  -> robots + independent page fetch
  -> existing V5 exact-company identity gate
  -> publish or abstain
```

Search snippets, rank, titles and query text are not evidence and should not be persisted. Brave's public documentation says API result storage requires a plan that grants storage rights; therefore V6 should hold search results transiently and retain only evidence from the independently fetched company page.

A Brave benchmark is blocked only by the absence of a reproducible API key in this repository/environment. The implementation can be optional and cost-bounded, but it must not become the default submission path until Builderr can reproduce the credential and a fresh zero-overlap run measures a real gain.

## V5 rejection audit from the exact fresh-100 artifact

This teardown also inspected the retained V5 fresh-100 profiles, not only competitor code.

- verified websites: **7 / 100**;
- deterministic compact `.no` candidates attempted for 96 companies;
- 66 compact `.no` hosts did not resolve;
- 5 produced network-unreachable errors;
- 3 were robots-blocked;
- 1 returned HTTP 500;
- 1 exceeded the page byte cap;
- 1 timed out;
- **1 failed TLS hostname validation**;
- 18 compact `.no` pages were fetchable, but only 3 ultimately became the canonical verified site;
- hyphenated `.no` fallback was attempted for 64 companies and produced **0 verified sites**; 63 did not resolve;
- registry-email discovery had 14 candidates and produced 1 verified site;
- Wikidata exact-org lookup returned 0 candidate websites for this 100.

This makes the immediate weakness concrete: V5 spends most of its website budget probing deterministic `.no` names that simply do not exist. The next experiment should improve **candidate quality and protocol resilience**, not weaken identity verification.

## V6 implementation decision

### First experiment — implement now

**V6-P0A: bounded zero-cost candidate expansion + safe fetch resilience.**

Independent design:

1. Keep existing registry-site and exact registry-email-domain paths.
2. Replace the low-yield hard-coded compact/hyphenated `.no` sequence with a ranked candidate planner that can nominate:
   - full legal-name compact `.no`;
   - full legal-name hyphenated `.no`;
   - full legal-name compact `.com`;
   - full legal-name hyphenated `.com`;
   - carefully bounded full-name variants that remove obvious geographic/legal filler only when at least two distinctive tokens remain.
3. Do **not** add more than the existing per-company site request budget. Candidate ranking changes what receives the request; it does not raise the ceiling.
4. Keep the current V5 exact-company publication gates unchanged.
5. Add safe HTTPS->HTTP recovery only for TLS/certificate/connectivity cases where the target registered domain stays identical; still honor SSRF checks, robots and redirect limits.
6. Add telemetry for every candidate strategy and rejection reason.
7. Run a development cohort, fix precision failures, then a new zero-overlap fresh 100 and compare against V5.

### Second experiment — only after P0A measurement

**V6-P0B: optional one-query Brave search fallback** inside existing request slots. Search candidate only; no result evidence. Benchmark only when a reproducible evaluator-safe key is available.

### Third experiment — only if website coverage materially improves

Bounded verified-site mining: sitemap -> targeted contact/about/team/careers/news pages -> RSS -> strict JobPosting + dated first-party updates + social/contact extraction.

## Stop / promotion criteria

Promote P0A only when a fresh zero-overlap cohort shows a meaningful website increase with no wrong-company publications in manual audit, zero contract/canonical errors, and request/runtime margins intact. If the gain is tiny, reject it and move to search-assisted discovery rather than accumulating more domain heuristics.
