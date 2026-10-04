# Signalpost 70+ Implementation Master Plan

Last updated: 2026-10-04

This document is the canonical engineering roadmap toward a Builderr 70+ result. `docs/CONTINUATION_STATE.md` owns exact live branch/PR/run state; `docs/IMPLEMENTATION_LOG.md` owns historical experiments and decisions. GitHub and the live Builderr challenge rules outrank stale documentation.

## 0. Objective and score target

Goal:

> Build the strongest possible Signalpost revision capable of scoring 70+ while preserving exact-company precision, evidence quality and evaluator reproducibility.

Working engineering target:

- Recall / coverage: 22–24+/50
- Precision / evidence: 28–29+/30
- Synthesis: 12/12
- UX: 8/8
- Total: 70–73+

This is a target, not a score prediction.

Core strategy:

> ATTEMPT MORE -> VERIFY STRICTLY -> PUBLISH CONSERVATIVELY

Primary optimization target: **net-new companies covered per scored information family**, not raw claim count.

## 1. Architectural philosophy

Signalpost should behave as a compact evidence-backed Norwegian company-intelligence platform:

```text
organisation number
    -> exact BRREG legal entity
       -> official exact-ID sources
       -> bounded external candidate sources
            -> candidate domains/pages
            -> exact identity gate
            -> verified domain/page
                 -> typed observations
       -> evidence-backed canonical claims
       -> history/changes
       -> synthesis/product
```

Useful architectural lessons come from systems such as Sayari, OpenCorporates, Diffbot, Dun & Bradstreet, Coresignal, OpenSanctions and OCCRP Aleph: legal-entity anchoring, candidate-vs-verified separation, typed observations, statement-level provenance, source fusion and deterministic monitoring. These are architectural references, not sources to scrape.

## 2. Non-negotiable identity and publication rules

1. Candidate generation is never publication proof.
2. Exact organisation number is the strongest legal-entity anchor.
3. Registry-filed website/domain is strong identity evidence, but external candidates still require independent page verification where the current gate requires it.
4. Full legal name + strong registered-address/location corroboration may qualify only under existing documented rules.
5. Legal name alone, municipality alone, postcode alone, brand similarity, search ranking and URL similarity do not qualify a site.
6. Parent/group/subsidiary/subunit/franchise relationship alone never authorizes inheritance of a website, job or public-activity fact.
7. Ambiguous identity means abstain.
8. Every external fact retains exact page URL, retrieval timestamp, content SHA-256 and supporting span/structured evidence.
9. Never use one page's hash to support a fact observed only on another page.
10. Missing/blocked/ambiguous never becomes zero or false absence.
11. Official and financial values remain deterministic source-backed facts.
12. A source failure must never drop the terminal company envelope.
13. Refresh/change processing remains deterministic and idempotent.
14. No experimental source enters production without meaningful transfer, precision audit, rights review and budget fit.
15. Third-party API spend remains $0 unless explicitly changed.
16. The four-logical-site-request ceiling/profile remains authoritative until separately requalified.
17. Fresh cohorts are scarce: once used, they are permanently consumed.

## 3. Observation layer and typed information families

External acquisition should create page-local observations before canonical claims. Observation contracts preserve source URL, retrieval timestamp, content hash, supporting span/structured node, extraction method, identity proof, effective/publication date and source family.

Typed internal families remain conceptually separate:

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

The system must not devolve into one loosely structured scraper.

## 4. Current production foundation

Production already includes:

- exact BRREG legal-entity anchoring
- exact-live and bulk registry handling
- financials, roles, people, locations/workplaces and group context
- canonical claims/evidence/change output
- terminal-envelope behavior
- deterministic refresh/change tracking
- request/runtime/cost accounting
- registry website, registry-email-domain, deterministic `.no`, exact-org Wikidata and hyphenated-domain website discovery
- strict exact-site verification with namesake/parent/franchise/hosting hardening
- first-party contact email/social observations
- registry and annual-report workforce
- annual-report company-description fallback
- bounded dated first-party news detail
- bounded current first-party job posting logic
- $0 third-party API spend

Phase 1 recovered broad exact-live BRREG facts already present in fetched data but previously not evaluator-visible: registration/address/purpose/contact facts, postal address, foundation/articles dates, enterprise/VAT states and dates, institutional sector, capital and forced-dissolution state.

## 5. Phase status map

- **Phase 0 — Repository reality check:** substantially complete; repeat when repo state changes materially.
- **Phase 1 — Lost-claim / collected-vs-emitted recovery:** **CLOSED / QUALIFIED / MERGED / POST-MERGE GREEN**.
- **Phase 2 — Website discovery improvement:** **SHELVED / CANDIDATE-SOURCE CONSTRAINED under current $0 rights-safe sources**.
- **Phase 3 — Sitemap/RSS + targeted crawler:** **ACTIVE**.
- **Phase 4 — Observation/evidence hardening:** active invariant for every new multi-page extractor.
- **Phase 5 — Contact/social:** partial production foundation; no generic contact fallback without new evidence.
- **Phase 6 — Actual jobs:** C12 M4 foundation exists; NAV batch experiment did not transfer on consumed 100.
- **Phase 7 — Dated activity:** **ACTIVE WITH PHASE 3**; C12 M3 foundation exists, RSS/sitemap expansion next.
- **Phase 8 — NAV batch experiment:** **SCREENED / DROP on consumed 100**.
- **Phase 9 — BRREG bulk request optimization:** later, cache/freshness/evidence-rule gated.
- **Phase 10 — Adaptive request scheduler:** after more useful verified-domain surfaces exist.
- **Phase 11 — Fresh large validation/release candidate:** final promotion gate.

Immediate path:

> Phase 3/7 verified-domain RSS/sitemap activity -> Phase 4 page-local evidence integrity -> selective Phase 5/6 enrichment only where new surfaces justify it -> Phase 10 adaptive allocation -> Phase 11 fresh release qualification.

## 6. Phase 0 — repository reality check

Trace the evaluator path whenever production changes materially:

```text
organisation number
 -> acquisition
 -> normalization
 -> observations/evidence
 -> canonical projection
 -> output contract
 -> final envelope/product
```

Verify `scripts/run_signalpost_v8.py`, delegated runners, official modules, site discovery/identity, external observations, evidence storage, budgets, refresh/change, synthesis and final serialization. Repository code and live GitHub state override assumptions.

## 7. Phase 1 — collected-vs-emitted recovery

Status: **closed**.

Reusable rule:

> Recover high-confidence facts already fetched before spending new network requests.

Phase 1 proved this can materially improve evaluator-visible coverage at zero new source/request cost.

## 8. Phase 2 — website discovery improvement

Status: **shelved under the current source constraints**.

Goal was to materially increase companies with an exact verified website without weakening identity precision. Consumed-cohort website reach remains about 7–8/100.

Existing production candidate families remain:

1. BRREG-declared website
2. registry email domain
3. deterministic legal-name `.no`
4. Wikidata official website linked through exact organisation number
5. hyphenated `.no`
6. stored/official hints only when rights-safe and evidence-safe

Rejected/do-not-repeat paths without genuinely new evidence:

- guessed `.com` expansion
- broad legal-name rule/ML candidate ranking that produced no useful net-new exact sites
- annual-report domain hints after zero-yield screen
- Norid organisation-number lookup because rights/purpose terms are incompatible
- exact-parent BRREG subunit homepage hints: 0/3
- exact-parent BRREG subunit email domains: 0/10
- same-domain secondary identity verification for loaded quarantined registry sites: 0/4
- provider/model-search PRs #78/#84 unless Builderr resolves provider/key/budget and the $0 constraint changes

Measured root cause on the frozen consumed 100:

- H1c deterministic `.no`: 96 attempts, 78 DNS non-resolution failures, 12 loaded, 3 verified
- H1g hyphenated `.no`: 73 attempts, 73 DNS non-resolution failures, 0 verified

Conclusion:

> The dominant Phase-2 gap is candidate-source quality, not a too-strict verification gate.

Do not weaken identity rules or keep inventing speculative legal-name domains. Reopen Phase 2 only if a genuinely new rights-safe candidate source appears.

## 9. Phase 3 — sitemap/RSS + targeted crawler

Status: **active**.

After an exact domain is verified, discover a tiny bounded set of high-yield pages through homepage hints, robots sitemap declarations, `/sitemap.xml`, sitemap indexes, RSS/Atom hints and justified common feed endpoints.

Current frozen-site inventory across 7 exact verified domains:

- homepage careers links: 0
- homepage news-detail links: 0
- structured job candidates: 0
- explicit publication-date candidates: 0
- social links: present on 3
- identity/contact-type links: present on 6

The prior generic contact-page fallback failed to add net-new contact-family coverage, so Phase 3 starts with **dated activity**, not another contact fallback.

### Active experiment: bounded dated first-party activity discovery

Rules:

- consumed cohort only; publication disabled
- exact verified domains only
- at most one discovery fetch + one detail fetch per eligible company
- prefer declared RSS/sitemap hints; deterministic same-domain `/sitemap.xml` or common feed path only when request budget permits
- never crawl an entire sitemap
- retain only a tiny bounded set of likely recent news/article candidates
- detail URL must stay on the already verified registered domain
- require an explicit page-local publication date and concrete article/update content
- prefer `NewsArticle`/`Article` JSON-LD, OpenGraph article timestamps, `<time datetime>` and equally strong page-local semantics
- preserve exact detail URL, timestamp, content hash and supporting evidence
- do not use sitemap `<lastmod>` alone as the published-company-update fact unless the detail page independently supplies valid publication evidence
- stay within the four-logical-site-request theorem through adaptive use of currently idle final slots

Promotion requires meaningful net-new **companies with dated activity**, zero wrong-company findings, complete page-local evidence and acceptable runtime/request cost.

## 10. Phase 4 — page-level observation/evidence hardening

Every multi-page fact must remain bound to the exact page that supplied it. Prefer structured data when trustworthy:

- JSON-LD `Organization`, `LocalBusiness`, `Person`, `JobPosting`, `NewsArticle`, `Article`
- OpenGraph
- canonical tags
- `<time datetime>`
- semantic HTML
- `mailto:` / `tel:` / `sameAs`

No supporting page-local evidence means no publication.

## 11. Phase 5 — contact and social enrichment

Extract from verified company-owned pages only. Prefer structured or explicitly labelled declarations. A social publication means only that the verified company page declared the profile URL; do not scrape social platforms for follower counts/posts.

Do not revive a generic idle contact-page request without a new multi-family or structured-data hypothesis; the prior phone/contact fallback did not transfer.

Track net-new companies, not number of links.

## 12. Phase 6 — actual job-posting acquisition

Invariant:

> careers page != active job posting

Require a concrete role, specific detail/application URL, exact employer context and current-job evidence such as `JobPosting` or equally strong structured detail. Never inherit parent/subsidiary jobs without explicit permitted exact semantics.

The NAV batch screen is not a production path after zero consumed-cohort transfer.

## 13. Phase 7 — dated first-party activity

Status: **active with Phase 3**.

Goal: at least one reliable dated company-owned update across as many verified-domain companies as possible.

Use exact news details, RSS/Atom, sitemap article candidates, `NewsArticle`/`Article` JSON-LD and explicit page-local publication dates. Avoid ambiguous date text and third-party news.

## 14. Phase 8 — NAV batch experiment

Status: **DROP on consumed 100 / not merged**.

Measured branch `experiment/nav-exact-org-vacancy-screen`, head `c156fda6a5ac711b285e864270273446262d19ac`, run `37214017085`:

- complete 180-day feed traversal
- 38 feed requests / 181,234,775 bytes
- 368,428 raw events / 90,917 unique vacancies / 9,723 active
- 0 target/subunit name shortlist candidates
- 0 detail requests
- 0 exact active-vacancy target companies
- 39 NAV logical requests / 78 conservative
- projected combined baseline charge 1,410/2,000
- $0 and zero wrong-company publications

The architecture was exact-ID safe—detail acceptance required exact main `employer.orgnr` or an exact BRREG subunit mapped to the target parent—but no candidate reached detail lookup. The public JWT is also experiment-only rather than a resolved stable production credential.

Do not broaden matching post-hoc or spend a fresh cohort. Reconsider only if NAV feed semantics or a direct organisation-number index materially changes.

## 15. Phase 9 — BRREG bulk optimization

Later, screen whether official bulk entities/roles/subunits can safely replace selected live calls under Builderr cache/freshness/evidence rules. Any saved request budget must be deliberately reallocated to higher-yield verified-site activity/jobs/contact work. Never sacrifice required freshness.

## 16. Phase 10 — adaptive request scheduler

Prioritize requests by:

```text
expected net-new scored company-family gain
-------------------------------------------
identity risk + request cost + latency risk
```

Examples:

- no verified site -> stop site enrichment
- verified site + no homepage activity + idle slot -> sitemap/RSS discovery may outrank duplicate contact work
- verified site + concrete sitemap/feed article candidate -> dated detail may outrank low-yield about pages
- already-covered families should not consume scarce requests

ML may rank candidates later but never authorize publication.

## 17. Phase 11 — fresh validation and release candidate

Maintain development, validation and final untouched cohorts. Before another Builderr revision require:

- fresh evaluator-shaped 100-company run
- 100/100 terminal envelopes
- zero contract/evidence/canonical/synthesis integrity errors
- zero known wrong-company publications
- manual audit of every newly introduced external family/case
- request/runtime/cost report
- exact commit SHA freeze
- CI green on exact head
- reproducible artifacts
- synthesis/UX preserved or improved

## 18. Measurement harness

Every material experiment reports company-level coverage:

- input/terminal companies
- verified website companies
- contact email/phone companies
- social companies and multi-platform companies
- careers-page companies
- concrete job-posting companies
- dated-update companies
- people/leadership companies
- location/workplace companies
- financial/workforce/change-history companies
- total published claims
- evidence/contract/canonical/synthesis failures
- wrong-company and ambiguous/rejected candidates
- logical requests and conservative charge
- runtime/latency and bytes where relevant
- third-party cost

Always compare:

```text
BASELINE -> NEW -> NET-NEW COMPANIES
```

## 19. Promotion criteria

A source/strategy is promoted only if relevant gates pass:

1. meaningful net-new company coverage
2. very high exact-entity precision
3. complete source/page evidence
4. deterministic behavior
5. acceptable rights
6. refresh-compatible semantics
7. request/time budget fit
8. no meaningful regression elsewhere

Decision labels: **PROMOTE**, **RETUNE**, **SHELVE**, **DROP**.

Rejected experiments belong in `docs/IMPLEMENTATION_LOG.md` so they are not repeated.

## 20. Adversarial entity validation

Maintain tests/fixtures for similar legal names, parent/subsidiary/group sites, subunits/shared domains, chain/franchise, company-vs-brand collisions, same municipality/postcode, pages with multiple organisation numbers, former names/rebrands and parked/hosting/service-provider pages.

## 21. Failure resilience and monitoring

Handle timeouts, connection resets, 403/404/410/429/5xx, redirect loops, robots blocks, invalid HTML, oversized pages and SSL failures without losing the terminal company envelope.

Refresh must distinguish conclusive change from source failure for websites, contacts, social profiles, jobs, news, roles and financial periods.

## 22. Later-only work

Secondary official sources such as Patentstyret, Støtteregisteret or Doffin require rights/reach/exact-ID screening first. Optional ML ranking and evidence-bounded AI extraction come only after deterministic gains. AI may extract from already-fetched verified text only when every fact has a deterministic supporting span; it may never establish legal identity or invent official numbers.

## 23. Synthesis and UX targets

Preserve/improve evidence-bounded synthesis covering what the company does, finances, people, locations, workforce, hiring, activity, changes, unknowns and source/effective dates.

Keep the evaluator-facing product directly linked to generated data with search/select, evidence drill-down, freshness/change context and explicit unavailable states. Do not prioritize cosmetic redesign while recall remains the main score gap.

## 24. Submission strategy

Do not submit after each feature. The next Builderr revision should bundle coordinated safe recall gains while preserving synthesis/UX and zero known wrong-company publications.

## 25. Continuity protocol

Every implementation chat must begin with:

1. `docs/CONTINUATION_STATE.md`
2. this file
3. current GitHub `main` and open PR metadata

If GitHub is ahead, reconcile docs first.

At the end of every substantial implementation session:

1. update `docs/CONTINUATION_STATE.md`
2. append material experiments/milestones to `docs/IMPLEMENTATION_LOG.md`
3. update this roadmap when phase status, acceptance criteria or strategy changes
4. record exact branch/head/PR/run IDs/artifacts/coverage/precision/budget/blockers/next actions
5. distinguish IMPLEMENTED, TESTED, QUALIFIED, MERGED and POST-MERGE GREEN

The repository, not chat history, is the source of truth.
