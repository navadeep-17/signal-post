# Signalpost 70+ Implementation Master Plan

Last updated: 2026-10-04

This document is the canonical engineering roadmap for the next Signalpost revisions. It exists so implementation can continue across ChatGPT conversation limits without reconstructing strategy from old chats.

## 0. Authority and score target

When anything in this repository conflicts with the live Builderr challenge page, the live Builderr page wins.

Current Builderr rubric as verified on 2026-10-04:

- Recall & coverage: 50
- Precision & evidence: 30
- Synthesis: 12
- UX: 8
- Qualification: >=65 overall on an official run
- A material wrong-company publication can block qualification
- First submission + up to four revised commit hashes = five versions total

Internal engineering target for the next major revision:

- Recall: 22-24+/50
- Precision/evidence: 28-29+/30
- Synthesis: 12/12
- UX: 8/8
- Target total: 70-73+

This is an engineering target, not a prediction of Builderr's hidden score.

## 1. Core strategy

The project should optimize for:

> ATTEMPT MORE -> VERIFY STRICTLY -> PUBLISH CONSERVATIVELY

Do not optimize by lowering identity thresholds. Discovery may be aggressive; publication must remain exact.

The main remaining score lever is company-level recall across external information families. The system should maximize **net-new companies covered per information family**, not total claim count.

## 2. Production-grade architecture model

Signalpost should converge toward a small evidence-backed company intelligence platform inspired by mature systems, without copying their proprietary implementations.

Production references and the architectural lesson to borrow:

| Reference | Relevant lesson |
|---|---|
| Sayari | canonical legal entity, candidate-vs-verified separation, relationship/source-document provenance |
| OpenCorporates | sourced statements, primary-register preference, historical provenance |
| Diffbot Knowledge Graph | verified web pages -> structured organization/person/article observations -> entity fusion with origins |
| Dun & Bradstreet | resolve -> enrich -> monitor lifecycle |
| Coresignal | typed company/people/jobs/headcount information families instead of one giant scraper |
| OpenSanctions | source ingestion, canonical entities, statement-level lineage, deterministic normalization |
| OCCRP Aleph | heterogeneous entity graph, timeline/events, source-backed relationships |
| Firmaradar / Proff | useful Norwegian company-intelligence information architecture |

Target architecture:

```text
ORGANISATION NUMBER
        |
        v
EXACT LEGAL ENTITY (BRREG)
        |
        +-------------------------------+
        |                               |
        v                               v
OFFICIAL SOURCES                 EXTERNAL DISCOVERY
financials/roles/etc.            registry website
                                 email-domain hints
                                 deterministic domains
                                 Wikidata exact-org hints
                                 other bounded candidates
                                         |
                                         v
                                  CANDIDATE DOMAINS
                                         |
                                         v
                                  EXACT IDENTITY GATE
                                         |
                                         v
                                    VERIFIED SITE
                                         |
                      +------------------+------------------+
                      |                  |                  |
                      v                  v                  v
                  HOMEPAGE           SITEMAP/RSS      TARGETED PAGES
                                                          |
                              +-----------+-----------+----+----+
                              |           |           |         |
                           CONTACT      PEOPLE      CAREERS    NEWS
                              |           |           |         |
                              v           v           v         v
                            email       leaders      jobs    activity
                            phone       locations
                            social
                              \           |           |        /
                               +----------+-----------+-------+
                                          |
                                          v
                                  SOURCE OBSERVATIONS
                                  exact source URL
                                  retrieved_at
                                  content hash
                                  evidence span
                                  extraction method
                                  identity proof
                                  reporting/effective date
                                          |
                                          v
                                   CANONICAL CLAIMS
                                          |
                          +---------------+---------------+
                          |               |               |
                          v               v               v
                       PROFILE         CHANGES         SYNTHESIS/UX
```

## 3. Non-negotiable safety invariants

1. Candidate discovery is never identity evidence by itself.
2. Exact organisation-number evidence is strongest.
3. Registry-filed domain is strong identity evidence.
4. Full legal name + strong registered-location/address corroboration may qualify when current rules permit it.
5. Name-only, municipality-only, brand similarity, directory pages, parent/group sites and franchise sites must not qualify.
6. Every external claim keeps exact page-level provenance.
7. Do not use a homepage hash to support a value found only on another page.
8. Missing/blocked/ambiguous never becomes zero.
9. Financial values remain deterministic official-source facts.
10. One source/network failure must not drop a company envelope.
11. Refresh must be deterministic and idempotent.
12. No experimental source enters production without measurable net-new company coverage and a clean precision audit.
13. Keep third-party API spend at $0 unless the user explicitly changes this project constraint.
14. Respect the evaluator request/runtime envelope and preserve explicit request accounting.

## 4. Current production foundation

As of main commit `fb4c8711b9a3c58c16c6ff1c26aada93c036938a`:

- exact BRREG entity anchoring is productionized;
- official financials, roles, locations and other registry data are productionized;
- canonical claims/evidence/change output exists;
- deterministic refresh/change tracking exists;
- one-command evaluator runner and request accounting exist;
- exact website discovery/verification includes hardened deterministic, email-domain, Wikidata and hyphenated-domain paths;
- verified company-declared social links and first-party contact emails are productionized;
- official registry and annual-report workforce evidence is productionized;
- C12 M3 retains bounded dated first-party news detail evidence;
- C12 M4 now publishes bounded current first-party jobs from verified company-owned hiring surfaces;
- the site-request ceiling remains intentionally bounded;
- third-party API spend remains $0.

The current public Builderr board may reflect an older submitted SHA. Never assume the public score represents current `main` until that exact SHA has been officially evaluated.

## 5. 70+ work program

### Phase A — Current-main score/coverage audit (mandatory before new features)

Goal: establish what `main` already collects and what it actually publishes.

Tasks:

- [ ] run a fresh evaluator-shaped cohort on the current M4 `main`;
- [ ] produce a field-family matrix: collected internally -> canonical claim -> evidence -> companies covered;
- [ ] identify any collected-but-unpublished facts;
- [ ] measure unique companies covered for website, contact, social, jobs, dated activity, people, locations, workforce and registry changes;
- [ ] record request/runtime/cost and wrong-company audits;
- [ ] compare against the last submitted/evaluated version without tuning on Builderr's checked collection.

Promotion principle: fix zero-risk projection/serialization omissions before adding new network work.

### Phase B — Verified-site enrichment 2.0

Goal: make every already-verified website yield more high-confidence families while preserving exact page provenance.

Implement or audit:

- sitemap discovery from `robots.txt`, `/sitemap.xml`, sitemap indexes;
- RSS/Atom discovery from HTML and sitemap hints;
- ranked same-domain targeted pages:
  - about / om-oss
  - contact / kontakt
  - team / ansatte / ledelse
  - careers / jobs / jobb / karriere / ledige-stillinger
  - news / nyheter / aktuelt / presse / press
- structured extraction:
  - `Organization`
  - `LocalBusiness`
  - `Person`
  - `JobPosting`
  - `NewsArticle`
  - `Article`
- OpenGraph, canonical tags, `<time datetime>`, `mailto:`, `tel:` and `sameAs`;
- exact page URL + hash + evidence span for every promoted fact.

Do not perform an unbounded crawl. Rank pages by expected score-relevant yield.

Success metrics:

- net-new companies with contact/social/jobs/activity/people/location facts;
- no wrong-company publication;
- no evidence-span mismatch;
- acceptable added requests per net-new company.

### Phase C — Adaptive request scheduler

Goal: spend the limited request budget where it can add a missing information family.

A request candidate should conceptually have:

```text
expected_company_coverage_gain
identity_risk
request_cost
latency_risk
```

Rules:

- no verified site -> stop site enrichment early;
- verified site with missing contact/social -> prioritize contact/about;
- explicit vacancy count or structured job candidate -> job detail before generic news;
- missing activity and no hiring signal -> news/RSS detail;
- already-covered families should not consume scarce requests merely to produce more claims;
- stop when the remaining expected gain is low.

Keep deterministic publication gates even if ranking later uses ML.

### Phase D — Job coverage expansion

Current M4 gives us a safe company-owned path. Next, measure whether it transfers to random-company cohorts.

Tasks:

- [ ] measure M4 current first-party job company coverage on fresh 100/300 cohorts;
- [ ] audit concrete `JobPosting` JSON-LD support;
- [ ] preserve generic-careers-page != active-job invariant;
- [ ] require specific role title and specific role/application URL;
- [ ] require current/future deadline or equally concrete current-job evidence where the rule supports it;
- [ ] preserve exact target-employer context; parent companies cannot inherit subsidiary jobs.

Secondary experiment only if worthwhile:

- shared NAV feed scan once per batch;
- index by exact employer organisation number;
- map BRREG subunit -> parent only through official exact relationships;
- fetch details only for exact target matches;
- promote only if net-new company coverage is meaningful.

Do not repeat the old inefficient per-company NAV architecture.

### Phase E — Dated activity expansion

Goal: increase companies with at least one reliable, dated first-party update.

Use:

- company-owned news detail pages;
- RSS/Atom items;
- sitemap candidates;
- `NewsArticle` / `Article` JSON-LD;
- explicit `<time datetime>` or equivalent structured publication date.

Avoid random date text and third-party news unless rights and identity are exceptionally strong.

Optimize for one supported update across many companies, not many articles on one company.

### Phase F — Official broad-source screens

Only after the above, screen sources that can reach companies without requiring a discovered website.

Candidate families:

- BRREG Støtteregisteret / state-support activity;
- Doffin procurement/contract activity;
- Patentstyret IP activity;
- NAV jobs using the improved shared-feed architecture.

Process:

1. rights and exact-ID check;
2. theoretical population reach check;
3. 10-20 company feasibility screen;
4. only then 100/300 qualification;
5. drop if random-company reach is weak.

### Phase G — ML request ranking (optional, after deterministic gains)

Use accumulated labelled identity examples to rank candidates/pages, never to authorize publication.

Possible features:

- legal-name/domain similarity;
- acronym/hyphen similarity;
- org-number presence;
- municipality/postcode/address overlap;
- email-domain match;
- page-title/legal-footer evidence;
- wrong-org-number flag;
- parked/hosting indicators;
- redirect behavior.

Start with logistic regression or gradient boosting. Keep the deterministic identity gate authoritative.

### Phase H — Evidence-bounded AI extraction (optional)

Use AI only on already-fetched, already-verified source text.

Required contract:

```text
verified source text
    -> strict structured extraction
    -> each fact includes supporting source span
    -> deterministic span verifier finds exact support
    -> publish or reject
```

No supporting span = no fact.

Never use the LLM to establish company identity or invent official numeric values.

Potential fields: description, products/services, named leaders, operating locations, concrete jobs, dated activity.

### Phase I — Synthesis to 12/12

Every company brief should answer, using only canonical evidence:

- what the company does;
- latest financial state;
- who runs it;
- where it operates;
- workforce status;
- current hiring status;
- recent public activity;
- what changed;
- what remains unknown;
- freshness/source dates.

No unsupported prose. Unknowns are first-class output.

### Phase J — UX to 8/8

The submitted product surface must be directly data-linked to generated output, not merely a builder script.

Required evaluator-facing capabilities:

- search/select company;
- clear company brief;
- financial periods and units;
- people and locations;
- verified website/contact/social;
- hiring and recent activity;
- evidence drill-down;
- retrieval/effective dates;
- changes/history;
- explicit unavailable/ambiguous/blocked states;
- desktop + mobile verification;
- compare companies if practical.

### Phase K — Release qualification and submission

Before consuming another Builderr revision:

- fresh evaluator-shaped 100-company run;
- 100/100 terminal envelopes;
- zero contract/evidence errors;
- zero known wrong-company publications;
- exact manual audit of every new external family in the cohort;
- request/runtime/cost report;
- fresh zero-overlap transfer cohort;
- exact commit SHA freeze;
- CI green on exact head;
- only then submit.

Bundle multiple meaningful recall improvements into a revision. Do not burn a revision for cosmetic changes or one tiny source patch.

## 6. Measurement harness

Every experiment must report **company coverage**, not just claim count.

Minimum report:

| Metric | Required |
|---|---|
| companies input | yes |
| terminal outputs | yes |
| verified website companies | yes |
| contact-email companies | yes |
| phone companies | yes |
| social-profile companies | yes |
| companies with >=2 social platforms | yes |
| actual job-posting companies | yes |
| dated-activity companies | yes |
| leadership companies | yes |
| location/workplace companies | yes |
| workforce companies | yes |
| registry-change companies | yes |
| total claims | yes |
| evidence validation errors | yes |
| wrong-company publications | yes |
| ambiguous candidates | yes |
| logical requests | yes |
| conservative request charge | yes |
| p50/p95 runtime/latency where available | yes |
| third-party cost | yes |

Always include baseline -> new -> **net-new companies** by family.

## 7. Validation discipline

Use disjoint cohorts:

- development cohort: tuning allowed;
- validation cohort: promotion gate;
- final untouched cohort: release audit only.

Maintain adversarial cases:

- same-name legal entities;
- parent/subsidiary;
- group umbrella sites;
- franchises;
- company-vs-brand collisions;
- directories/listings;
- same municipality;
- pages containing multiple org numbers;
- former names/rebrands;
- shared domains.

A green unit test is never sufficient to qualify a data-source strategy.

## 8. What not to prioritize now

Do not spend primary engineering time on:

- broad frontend rewrites;
- cosmetic README work;
- sentiment;
- LinkedIn/Facebook/Glassdoor scraping;
- Google Places scraping;
- random review sources;
- guessed third-party news;
- broad connector hunting without a reach/rights screen.

The near-term score path is:

> more exact companies -> verified site/source -> more distinct scored families -> complete evidence -> better synthesis/UX

## 9. Submission strategy

Builderr revisions are scarce. Treat each submission as a release event.

Preferred next submission characteristics:

- current C12 M3/M4 first-party activity/jobs included;
- measurable recall increase on fresh cohorts;
- evidence/precision preserved or improved;
- synthesis/product surface fully evaluator-visible;
- request/runtime limits safe;
- no material wrong-company case;
- exact SHA frozen and reproducible.

Do not submit merely because a branch merged.

## 10. Continuity protocol

Every implementation chat must read these first:

1. `docs/CONTINUATION_STATE.md`
2. `docs/70_PLUS_IMPLEMENTATION_PLAN.md`
3. current branch/PR metadata from GitHub

At the end of every substantial work session, the implementing chat must:

1. update `docs/CONTINUATION_STATE.md`;
2. append a material milestone/experiment entry to `docs/IMPLEMENTATION_LOG.md`;
3. update checkboxes/decisions in this master plan if the roadmap changed;
4. record exact branch, head SHA, PR, CI/live-run IDs, metrics, blockers and next actions;
5. never leave critical state only in conversation text.

The repository, not chat memory, is the project source of truth.
