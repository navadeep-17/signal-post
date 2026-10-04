# Signalpost 70+ Implementation Master Plan

Last updated: 2026-10-04

This document is the **canonical engineering roadmap** for the next Signalpost revision cycle. It is intentionally aligned to the full production-grade architecture and the explicit Phase 0-11 implementation order agreed for the project.

Use `docs/CONTINUATION_STATE.md` for the exact live branch/PR/run state. Use `docs/IMPLEMENTATION_LOG.md` for historical experiments and decisions. This file defines **where the architecture is going and in what order**.

---

## 0. Objective, authority and score target

The goal is not to keep adding features. The goal is:

> **Build the strongest possible Signalpost revision capable of scoring 70+ on Builderr while preserving exact-entity precision and evidence quality.**

When this repository conflicts with the live Builderr challenge page, the live Builderr page wins.

Current working score target:

- Recall / coverage: **22-24+/50**
- Precision / evidence: **28-29+/30**
- Synthesis: **12/12**
- UX: **8/8**
- Target total: **70-73+**

This is an engineering target, not a prediction of Builderr's hidden score.

Builderr revisions are scarce. Do **not** submit another version merely because a feature merged. The next submission should bundle coordinated recall improvements, transfer to fresh companies, preserve precision/evidence, and materially outperform the current baseline.

Core strategy:

> **ATTEMPT MORE -> VERIFY STRICTLY -> PUBLISH CONSERVATIVELY**

The dominant remaining score lever is **company-level external recall / coverage**.

Do not increase recall by weakening company identity.

A wrong-company publication can destroy qualification.

---

## 1. Architectural philosophy

Signalpost is being developed as a small production-grade, evidence-backed Norwegian company intelligence platform.

The useful architectural patterns are:

| Reference | Pattern to borrow |
|---|---|
| Sayari | canonical legal entity, candidate-vs-verified separation, relationship/source-document provenance, monitoring |
| OpenCorporates | sourced statements, primary registry preference, historical provenance |
| Diffbot Knowledge Graph | multi-page web enrichment, typed Organization/Person/JobPosting/NewsArticle observations, origins |
| Dun & Bradstreet | **resolve -> enrich -> monitor** lifecycle |
| Coresignal | separate typed company/people/jobs/headcount modules instead of one giant scraper |
| OpenSanctions | source ingestion, canonical entities, statement-level lineage, deterministic normalization |
| OCCRP Aleph | heterogeneous entity graph, structured + unstructured records, timelines, provenance |
| Firmaradar / Proff | useful Norwegian company-intelligence information architecture |

These are architectural references, not sources to scrape or implementations to copy.

The intended product behaves conceptually like a compact:

> **OpenCorporates + Sayari + Diffbot + D&B**

adapted to Norwegian legal entities, Builderr's evaluator, strict evidence requirements, deterministic refresh, and a bounded request budget.

---

## 2. Target architecture

```text
ORGANISATION NUMBER
        |
        v
EXACT ENTITY ANCHOR
BRREG / legal entity
        |
        +----------------------------------+
        |                                  |
        v                                  v
OFFICIAL SOURCES                    EXTERNAL DISCOVERY
registry                            registry website
financials                         registry email domain
roles                              deterministic domains
locations                          Wikidata exact-org hints
group                              stored domain hints
changes                            optional bounded discovery
        |                                  |
        |                                  v
        |                           CANDIDATE DOMAINS
        |                                  |
        |                                  v
        |                           EXACT IDENTITY GATE
        |                                  |
        |                            VERIFIED DOMAIN
        |                                  |
        |            +---------------------+--------------------+
        |            |                     |                    |
        |            v                     v                    v
        |         SITEMAP               HOMEPAGE             RSS/FEEDS
        |            |
        |       TARGETED PAGE CRAWL
        |            |
        |    +-------+--------+----------+----------+
        |    |       |        |          |          |
        |    v       v        v          v          v
        |  ABOUT   CONTACT   TEAM      CAREERS     NEWS
        |    |       |        |          |          |
        |    v       v        v          v          v
        | people   email    leaders   JobPosting  NewsArticle
        |          phone               jobs        dated activity
        |          social
        |            |
        +------------+------------------------------------------+
                             |
                             v
                       OBSERVATION LAYER
                  value + exact source page
                  retrieval timestamp
                  content SHA-256
                  claim span
                  extraction method
                  identity proof
                  effective/reporting date
                             |
                             v
                       CANONICAL CLAIMS
                             |
                 +-----------+-----------+
                 |           |           |
                 v           v           v
              PROFILE      HISTORY    SYNTHESIS/UX
                             |
                           CHANGES
```

This is the direction. New implementation work should be judged by whether it moves the production evaluator toward this architecture.

---

## 3. Non-negotiable identity and publication rules

1. Candidate generation is **not** publication evidence.
2. Exact organisation-number evidence remains the strongest legal-entity anchor.
3. A registry-filed website/domain is strong identity evidence.
4. Full legal name + strong full registered-address/location corroboration may qualify only when current rules permit it.
5. Legal name alone, municipality alone, postcode alone, brand similarity, keyword similarity, search ranking or URL similarity do not qualify a site.
6. Parent/group sites, franchise sites, directory pages, marketplaces and similarly named companies must not be treated as the target entity.
7. Ambiguous identity means **abstain**.
8. Every external fact must retain exact page-level provenance.
9. Do not use a homepage hash to support a fact found only on another page.
10. Missing / blocked / ambiguous is never converted to zero or false absence.
11. Financial and registry values remain deterministic official-source facts.
12. A source/network failure must never drop the company envelope.
13. Refresh must be deterministic and idempotent.
14. No experimental source enters production without meaningful net-new company coverage and a clean precision audit.
15. Third-party API spend remains **$0** unless the user explicitly changes that constraint.
16. Request/runtime accounting must remain explicit and evaluator-safe.

The guiding pattern is:

```text
many candidate attempts
        |
        v
strict verification
        |
        v
few false positives
        |
        v
higher true coverage
```

Never replace this with weak matching merely to publish more facts.

---

## 4. Observation layer vs canonical claims

This separation is central to the architecture.

### Observation

An observation is something seen in **one exact source**.

Example:

```text
source_page: https://company.no/contact
observed: email = post@company.no
identity: verified domain for org 123456789
retrieved_at: ...
content_sha256: ...
claim_span: "Kontakt oss på post@company.no"
extraction_method: mailto / structured / labelled text
```

### Canonical claim

A canonical claim is the normalized profile-level statement:

```text
company.contact.email = post@company.no
```

linked back to its source observation/evidence.

This architecture is required for safe multi-page extraction, source fusion, refresh/change detection and evaluator evidence.

If any new module cannot preserve this lineage cleanly, fix the lineage before expanding extraction.

---

## 5. Typed information-family architecture

Prefer typed internal modules/concepts such as:

```text
IdentityProfile
RegistryProfile
FinancialProfile
PeopleProfile
LocationProfile
WebsiteProfile
ContactProfile
SocialProfile
HiringProfile
ActivityProfile
ChangeProfile
```

Then project them into canonical claims.

Do not evolve the system into one giant loosely structured company scraper.

---

## 6. Current production foundation

The exact current SHA, active branch, PRs, CI runs and qualification state belong in `docs/CONTINUATION_STATE.md`.

The production foundation already includes:

- exact BRREG legal-entity anchoring;
- official financials;
- roles and people;
- registered locations/workplaces;
- registry/group context where available;
- exact-live and bulk registry handling;
- canonical claims/evidence/change output;
- deterministic refresh/change tracking;
- terminal-envelope behavior;
- request/runtime/cost accounting;
- hardened website candidate discovery using registry website, registry email domain, deterministic `.no`, Wikidata exact-org hints and hyphenated-domain fallback;
- strict exact-site verification;
- first-party contact email/social extraction;
- registry and annual-report workforce evidence;
- annual-report description fallback;
- bounded first-party dated-news detail logic;
- bounded current first-party job-posting logic;
- a strict site-request ceiling;
- $0 third-party API spend.

Recent Phase 1 work has also proved that significant recall can exist in data already fetched but not projected into evaluator-visible claims. Therefore **free/zero-request recall must be exhausted before adding unnecessary network work**.

---

# 7. Implementation order — Phase 0 through Phase 11

The following order is authoritative unless measurement justifies a documented change.

## PHASE 0 — Repository reality check

**Status: substantially completed; repeat whenever repository state materially changes.**

Goal: understand the actual production evaluator path before coding.

Trace:

```text
organisation number
    -> acquisition
    -> normalization
    -> observations/evidence
    -> canonical projection
    -> output contract
    -> final envelope/product UI
```

Audit the real execution path, including:

- `scripts/run_signalpost_v8.py`;
- V7/V5/V2/V1 delegation if still present;
- `scripts/run_signalpost_final.py`;
- `scripts/run_signalpost_v2.py`;
- canonical projection;
- registry projection;
- BRREG live/bulk handling;
- financials;
- roles;
- people;
- locations/subunits;
- group/company relationships;
- workforce;
- annual-report intelligence;
- website discovery/verification;
- Wikidata/fallback discovery;
- contact/social;
- careers/jobs;
- first-party activity/C12 news;
- sitemap/homepage extraction;
- evidence storage;
- request budget;
- refresh/change detection;
- synthesis;
- evaluator workspace;
- output-contract serialization.

Do not assume docs are current. GitHub and the actual code path are authoritative.

---

## PHASE 1 — Lost-claim / collected-vs-emitted audit

**Status: active / near completion.**

Goal: recover high-confidence facts already fetched internally but not projected/published.

Maintain a matrix:

| Information family | Acquisition source | Collected internally? | Canonical claim? | Evidence complete? | Companies covered | Weakness |
|---|---|---:|---:|---:|---:|---|

Audit at minimum:

- legal name;
- organisation form;
- NACE/industry;
- registered purpose/activity;
- registration/foundation/statutes dates;
- municipality;
- registered and postal address;
- bankruptcy/liquidation/forced-dissolution state;
- VAT/enterprise-register state and dates;
- institutional sector;
- registered capital;
- CEO / daglig leder;
- board chair/members/roles;
- financial periods, revenue, results, assets, equity, debt;
- workplaces/subunits;
- group relationships;
- workforce;
- verified website;
- email/phone/mobile;
- social;
- careers page;
- actual jobs;
- dated public updates;
- registry changes;
- annual-report description/workforce.

Promotion rule:

> Fix zero-risk projection/serialization omissions before adding new source requests.

Current active work belongs here until the fresh qualification gate is fully clean.

---

## PHASE 2 — Website discovery improvement

Goal: materially increase the number of companies with an **exact verified website** without weakening publication precision.

Candidate generation may use:

1. BRREG-declared website;
2. registry email domain;
3. deterministic legal-name domains;
4. Wikidata official website linked through exact organisation number;
5. existing stored domain hints;
6. annual-report domain hints only if measured useful;
7. optional bounded search only if allowed, rights-safe and demonstrably worthwhile.

Important:

> **Candidate generation != identity evidence.**

Measure:

- candidates attempted;
- exact verified websites;
- ambiguous candidates;
- rejected wrong-company candidates;
- net-new verified companies;
- request impact;
- runtime impact.

Do not revive previously failed guessed `.com` expansion without new evidence.

---

## PHASE 3 — Sitemap + targeted crawler

Goal: turn each already-verified company domain into a bounded multi-page intelligence source.

After verification, do **not** stop at the homepage.

Discover candidates through:

- homepage links;
- `robots.txt` sitemap declarations;
- `/sitemap.xml`;
- sitemap indexes;
- HTML `<link rel="alternate">`;
- RSS/Atom hints;
- common feed endpoints where bounded and justified.

Rank targeted page classes:

### About

Paths/hints:

- `/about`
- `/about-us`
- `/om`
- `/om-oss`

Potential families:

- description;
- business activity;
- leadership;
- address/location.

### Contact

- `/contact`
- `/kontakt`

Potential families:

- email;
- phone;
- address;
- social.

### Team / leadership

- `/team`
- `/people`
- `/ansatte`
- `/ledelse`

Potential family:

- named people/leaders, only when their relationship to the exact target company is explicit.

### Careers

- `/careers`
- `/jobs`
- `/jobb`
- `/karriere`
- `/ledige-stillinger`

Potential families:

- careers surface;
- specific current job candidates.

### News

- `/news`
- `/nyheter`
- `/aktuelt`
- `/press`
- `/presse`

Potential families:

- dated company updates;
- news detail candidates.

### Sitemap scoring

Do not crawl an entire sitemap.

Conceptual priority:

```text
job/career        high
news/press        high
contact           high
team/leadership   medium-high
about             medium
product pages     low
privacy/legal     near zero
```

The goal is not page coverage. The goal is **net-new scored information-family coverage per request**.

---

## PHASE 4 — Observation/evidence layer hardening

Goal: guarantee exact page-level lineage before aggressive multi-page extraction expands.

Every external observation must preserve:

- source URL;
- retrieval timestamp;
- SHA-256/content hash;
- exact relevant source span;
- effective/reporting/publication date where applicable;
- extraction method;
- identity proof;
- source family/class.

The canonical projection must never combine incompatible provenance across pages.

Structured extraction should inspect, where applicable:

- JSON-LD;
- OpenGraph;
- canonical tags;
- `<time datetime>`;
- semantic HTML;
- anchors;
- `mailto:`;
- `tel:`;
- `sameAs`;
- relevant metadata.

Recognize typed structures including:

- `Organization`;
- `LocalBusiness`;
- `Person`;
- `JobPosting`;
- `NewsArticle`;
- `Article`.

Prefer trustworthy structured data over fuzzy text heuristics.

---

## PHASE 5 — Contact + social enrichment

Goal: increase companies with exact first-party contact and social information.

Extract from verified company-owned pages:

- email;
- phone;
- address;
- social URLs.

Prefer:

- `mailto:`;
- `tel:`;
- labelled contact sections;
- JSON-LD;
- `sameAs`;
- company-owned footer/contact/about declarations.

Allowed social-publication semantics:

> The verified company-owned page declares this social URL.

Potential platforms:

- LinkedIn;
- Facebook;
- Instagram;
- YouTube;
- X/Twitter.

Do not scrape those social platforms for metrics/posts/followers.

Retain the exact company page that declared each profile.

Track **net-new companies**, not just extra links.

---

## PHASE 6 — Actual job-posting acquisition

Goal: increase company coverage for concrete current jobs while preserving the invariant:

> **careers page != active job posting**

Target pipeline:

```text
verified domain
      |
      v
careers surface / sitemap / homepage links
      |
      v
candidate job links
      |
      v
specific job detail
      |
      v
exact evidence
      |
      v
canonical job claim
```

Use:

- sitemap candidates;
- careers links;
- homepage job links;
- JSON-LD `JobPosting`;
- strongly structured job detail pages.

Require strong signals such as:

- specific role title;
- specific detail URL;
- exact target-employer context;
- company-owned verified domain or allowed exact action URL semantics;
- JobPosting JSON-LD or equally strong job-detail semantics;
- current/future deadline or other concrete current-job evidence when required.

Extract where supported:

- title;
- date posted;
- valid-through/deadline;
- employment type;
- location;
- application URL.

Never inherit subsidiary jobs to a parent target or vice versa without exact legal relationship semantics permitted by the evaluator.

---

## PHASE 7 — Dated public activity

Goal: increase companies with **at least one** reliable, dated first-party update.

Use:

- company-owned news detail pages;
- sitemap article candidates;
- RSS;
- Atom;
- JSON-LD `NewsArticle`;
- JSON-LD `Article`;
- `<time datetime>`;
- explicit page-local publication dates.

Avoid ambiguous date text and unrelated third-party news.

Optimization rule:

> One valid update across many companies is better than many updates for one company.

---

## PHASE 8 — NAV experiment

Goal: reconsider NAV only through an efficient batch-level exact-org architecture.

Do not repeat the earlier inefficient per-company NAV approach.

Potential architecture:

```text
once-per-run NAV vacancy feed scan
        |
        v
index vacancies by employer organisation number
        |
        v
map subunit -> parent only through exact BRREG relationship
        |
        v
identify matching target companies
        |
        v
fetch only matched job details
```

Promotion requires meaningful **net-new company coverage** on a fresh cohort.

If yield remains tiny, shelve/drop it.

---

## PHASE 9 — BRREG bulk request optimization

Goal: determine whether safe official bulk datasets can replace selected live calls and reserve scarce network budget for higher-yield external enrichment.

Candidate bulk families:

- entities;
- roles;
- subunits.

Before changing semantics verify:

- current Builderr cache rules;
- freshness requirements;
- evidence requirements;
- retrieval-timestamp semantics;
- source rights/licensing;
- reproducibility.

If allowed, use exact-org local lookups for low-risk official facts and spend freed request budget on:

- website verification/discovery;
- sitemap;
- jobs;
- news;
- contact/social.

Do not sacrifice required freshness.

---

## PHASE 10 — Adaptive request scheduler

Goal: maximize expected new scored information-family coverage per request.

Do not give every company a rigid identical crawl plan.

Each request candidate should conceptually carry:

```text
expected_score_or_company_coverage_gain
identity_risk
request_cost
time_or_latency_cost
```

Prioritize:

```text
high expected gain
low identity risk
low request cost
```

Examples:

### No verified website

Stop site enrichment early.

### Verified website, no sitemap

Use ranked direct homepage links.

### Verified website + sitemap

Rank useful candidates according to currently missing families, e.g.:

1. specific job detail;
2. specific news detail;
3. contact;
4. team/about.

### Company already has contact/social

Spend remaining requests on missing jobs/activity instead of duplicating already-covered families.

The scheduler may later use ML for ranking, but deterministic identity/publication gates remain authoritative.

---

## PHASE 11 — Fresh large validation and release candidate

Goal: prove that the coordinated revision transfers beyond development companies and is safe to submit.

Maintain three classes of cohorts:

### Development cohort

Tuning allowed.

### Validation cohort

Not used while implementing a change.

### Final untouched cohort

Reserved for release-candidate qualification only.

Track every previously touched organisation number and enforce no-overlap selection.

Before submission require:

- fresh evaluator-shaped 100-company run;
- 100/100 terminal envelopes;
- zero contract errors;
- zero evidence-validation errors;
- zero known wrong-company publications;
- manual audit of every newly introduced external family/case in the cohort;
- request/runtime/cost report;
- transfer to a fresh zero-overlap cohort where appropriate;
- exact commit SHA freeze;
- CI green on exact head;
- reproducible artifacts;
- synthesis/UX preserved or improved.

Only then consider consuming a Builderr revision.

---

## 8. Coverage and score-oriented measurement harness

Every experiment must report **company-level coverage**, not just claims.

Minimum report:

| Metric | Required |
|---|---|
| input companies | yes |
| completed terminal envelopes | yes |
| verified website companies | yes |
| contact-email companies | yes |
| phone companies | yes |
| social companies | yes |
| companies with >=2 social platforms | yes |
| careers-page companies | yes |
| actual job-posting companies | yes |
| dated-update companies | yes |
| leadership/people companies | yes |
| location/workplace companies | yes |
| financial companies | yes |
| workforce companies | yes |
| registry/change-history companies | yes |
| total published claims | yes |
| evidence-validation failures | yes |
| wrong-company publications | yes |
| ambiguous/rejected candidates | yes |
| logical requests | yes |
| conservative request charge | yes |
| requests/company | yes |
| p50 runtime/latency where available | yes |
| p95 runtime/latency where available | yes |
| third-party cost | yes |

Always compare:

```text
BASELINE -> NEW -> NET-NEW COMPANIES
```

Example:

```text
website +19 companies
social  +12
email   +9
jobs    +4
news    +11
```

Do not optimize claim count blindly.

```text
100 facts on 5 companies
```

can be less valuable than:

```text
1 useful scored fact on 50 companies
```

when the evaluator rewards information-family company coverage.

---

## 9. Promotion criteria for every strategy

Do not promote a source or strategy merely because it technically works.

It must satisfy all relevant gates:

1. meaningful net-new company coverage;
2. very high exact-entity precision;
3. complete page/source evidence;
4. deterministic output;
5. acceptable source rights;
6. refresh-compatible semantics;
7. request/time budget fit;
8. no meaningful regression elsewhere.

Decision must be explicit:

- **PROMOTE**
- **RETUNE**
- **SHELVE**
- **DROP**

Rejected experiments are valuable evidence and should remain in `docs/IMPLEMENTATION_LOG.md` so they are not repeated accidentally.

---

## 10. Adversarial entity validation

Maintain explicit tests/fixtures for:

- same legal name;
- similar legal name;
- parent/subsidiary;
- group umbrella site;
- chain/franchise;
- company-vs-brand collision;
- directory/listing;
- same municipality;
- same postcode;
- page containing multiple organisation numbers;
- former company name/rebrand;
- shared domains between entities;
- service-provider/hosting/parked pages.

These cases matter more than ordinary happy-path tests because one wrong-company publication can invalidate otherwise strong recall.

---

## 11. Failure resilience

The evaluator must never lose a company envelope because one external source fails.

Handle explicitly:

- timeout;
- connection reset;
- 403;
- 404;
- 410;
- 429;
- 500/502/503/504;
- redirect loops;
- robots blocks;
- invalid HTML;
- oversized pages;
- SSL failures.

Use bounded retry/backoff where justified.

One host must not consume the run budget.

A failed refresh must not automatically imply deletion of a previously known fact. Preserve last conclusive state where the product semantics require it.

---

## 12. Refresh and monitoring

The architecture must support deterministic refresh/change tracking for new enrichment families.

Important cases:

- new job appears;
- old job disappears;
- new article appears;
- contact email/phone changes;
- website changes;
- social link is withdrawn;
- role changes;
- financial period changes.

Monitoring semantics should follow the same observation -> canonical claim architecture and distinguish conclusive change from source failure.

---

## 13. Secondary official sources — later only

Only after website/multi-page enrichment is mature should we screen additional broad official sources such as:

- Patentstyret;
- BRREG Støtteregisteret;
- Doffin;
- other exact organisation-number keyed datasets.

Before implementation:

1. verify rights;
2. verify exact identity mapping;
3. estimate theoretical population reach;
4. run a 10-20 company feasibility screen;
5. promote to 100/300 only if random-company reach is meaningful and Builderr relevance is clear.

Do not spend primary engineering time on broad connectors merely because they exist.

---

## 14. Optional ML request ranking — only after deterministic gains

ML may rank discovery/page candidates but must **never authorize publication**.

Possible features:

- legal-name/domain similarity;
- acronym/hyphen similarity;
- organisation-number presence;
- municipality/postcode/address overlap;
- email-domain match;
- title/footer legal evidence;
- wrong-org-number flag;
- parked/hosting indicators;
- redirect behavior.

Start simple (e.g. logistic regression or gradient boosting) if measurement shows a real need.

The deterministic identity gate remains authoritative.

---

## 15. Optional evidence-bounded AI extraction — later only

AI may be used only on **already fetched, already verified** source text.

Required contract:

```text
verified source text
    -> strict structured extraction
    -> every fact includes supporting source span
    -> deterministic span verifier confirms support
    -> publish or reject
```

No supporting span = no fact.

Never use an LLM to establish company identity or invent official numeric values.

Possible later fields:

- description;
- products/services;
- named leaders;
- operating locations;
- jobs;
- dated activity.

---

## 16. Synthesis target — preserve/improve toward 12/12

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

Unknowns are first-class output.

Do not generate unsupported narrative merely to make the product feel complete.

---

## 17. UX target — preserve/improve toward 8/8

The evaluator-facing product should remain directly linked to generated data.

Important capabilities:

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
- desktop and mobile usability;
- compare companies if practical.

Do not spend major effort on visual redesign while recall remains the dominant score gap.

---

## 18. Things not to prioritize now

Do not spend primary engineering time on:

- broad frontend redesign;
- new color palettes/animations;
- cosmetic README work;
- architecture-diagram polish;
- generic AI chat;
- sentiment;
- LinkedIn/Facebook/Glassdoor scraping;
- Google Places scraping;
- random review scraping;
- random third-party news search;
- broad patent/grant/procurement connectors before a reach/rights screen.

The immediate score path is:

> **verified website -> multi-page enrichment -> contact/social/jobs/news -> adaptive request allocation -> fresh release validation**

while continuing to harvest any remaining safe zero-request official recall discovered by audits.

---

## 19. Report format after each phase/experiment

Every material phase or experiment should report:

### Change
What was implemented.

### Files
Files changed.

### Tests
Tests/CI/live runs and exact results.

### Baseline
Previous company-level coverage.

### New
New company-level coverage.

### Net gain
Explicit net-new companies by family.

### Precision
Wrong/ambiguous company findings and manual audit result.

### Budget
Requests, runtime, latency and cost impact.

### Decision
`PROMOTE`, `RETUNE`, `SHELVE` or `DROP`.

### Lifecycle
Explicitly distinguish:

- **IMPLEMENTED**
- **TESTED**
- **QUALIFIED**
- **MERGED**
- **POST-MERGE GREEN**

---

## 20. Submission strategy

Do **not** submit after each feature.

The next Builderr revision should ideally bundle:

- all safe lost-claim/serialization recovery;
- stronger exact website discovery if it clears precision gates;
- sitemap + targeted multi-page enrichment;
- materially improved contact/social coverage;
- useful actual-job acquisition;
- materially improved dated activity;
- complete page-level evidence;
- adaptive request allocation;
- preserved/improved synthesis and UX.

The desired release report should look like:

```text
CURRENT BASELINE
website: X%
social: X%
contact: X%
jobs: X%
dated activity: X%

NEW VERSION
website: materially higher
social: materially higher
contact: materially higher
jobs: non-zero and useful
dated activity: materially higher

wrong-company publications: 0 in held-out audit
evidence failures: 0
terminal envelopes: 100%
request budget: safe
runtime: safe
third-party cost: $0
synthesis: preserved/improved
UX: preserved/improved
```

Only then should another Builderr revision be considered.

---

## 21. Current phase mapping

Use `docs/CONTINUATION_STATE.md` for exact current run/PR state, but architecturally the project is currently here:

- **Phase 0 — Repository reality check:** substantially complete.
- **Phase 1 — Lost-claim audit:** active / near completion; current BRREG exact-live projection and qualification work belongs here.
- **Phase 2 — Website discovery improvement:** existing hardened foundation, systematic next-stage improvement not yet completed.
- **Phase 3 — Sitemap + targeted crawler:** upcoming major work.
- **Phase 4 — Observation/evidence hardening:** strong existing foundation; must be enforced across all Phase 3 multi-page extraction.
- **Phase 5 — Contact/social:** partial production foundation; multi-page expansion pending.
- **Phase 6 — Actual jobs:** C12 M4 foundation exists; broader sitemap/detail acquisition pending.
- **Phase 7 — Dated activity:** C12 M3 foundation exists; RSS/sitemap/structured expansion pending.
- **Phase 8 — NAV batch experiment:** later, measurement-gated.
- **Phase 9 — BRREG bulk optimization:** later, rules/freshness-gated.
- **Phase 10 — Adaptive scheduler:** future major layer after usable candidate surfaces exist.
- **Phase 11 — Fresh large validation:** release gate before submission.

The immediate transition after Phase 1 is:

> **Phase 2 exact website coverage -> Phase 3 sitemap/targeted pages -> Phase 4 page-level observation integrity -> Phase 5/6/7 contact/social/jobs/activity.**

Do not skip directly to optional ML/AI or broad new connectors.

---

## 22. Continuity protocol

Every implementation chat must begin with:

1. `docs/CONTINUATION_STATE.md`;
2. `docs/70_PLUS_IMPLEMENTATION_PLAN.md`;
3. current GitHub `main`, active branch and PR metadata.

If GitHub is ahead of the state document, reconcile the state first.

At the end of every substantial implementation session:

1. update `docs/CONTINUATION_STATE.md`;
2. append significant experiments/milestones to `docs/IMPLEMENTATION_LOG.md`;
3. update this master plan only when phase decisions or architecture materially change;
4. record exact branch/head/PR/run IDs/artifacts/metrics/blockers/next actions;
5. never leave critical project state only in chat history.

The repository, not conversation memory, is the source of truth.
