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
6. Parent/group/subsidiary/subunit/franchise relationship alone never authorizes inheritance of a website, job or public activity fact.
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

External acquisition should create page-local observations before canonical claims.

Observation contract should preserve:

- source URL
- retrieved_at
- content SHA-256
- relevant source span / structured node
- extraction method
- identity proof
- effective/reporting/publication date where applicable
- source family/class

Typed internal families should remain conceptually separate:

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

- exact BRREG legal-entity anchoring;
- exact-live and bulk registry handling;
- financials, roles, people, locations/workplaces and group context;
- canonical claims/evidence/change output;
- terminal-envelope behavior;
- deterministic refresh/change tracking;
- request/runtime/cost accounting;
- registry website, registry-email-domain, deterministic `.no`, exact-org Wikidata and hyphenated-domain website discovery paths;
- strict exact-site verification with namesake/parent/franchise/hosting hardening;
- first-party contact email/social observations;
- registry and annual-report workforce;
- annual-report company-description fallback;
- bounded dated first-party news detail;
- bounded current first-party job posting logic;
- $0 third-party API spend.

Phase 1 additionally recovered broad exact-live BRREG facts already present in fetched data but previously not evaluator-visible: registration/address/purpose/contact facts, postal address, foundation/articles dates, enterprise/VAT states and dates, institutional sector, capital and forced-dissolution state.

## 5. Phase status map

- **Phase 0 — Repository reality check:** substantially complete; repeat whenever the repo changes materially.
- **Phase 1 — Lost-claim / collected-vs-emitted recovery:** **CLOSED / QUALIFIED / MERGED / POST-MERGE GREEN**.
- **Phase 2 — Website discovery improvement:** **ACTIVE**.
- **Phase 3 — Sitemap + targeted crawler:** upcoming after Phase 2 materially improves exact site reach.
- **Phase 4 — Observation/evidence hardening:** strong foundation; must be enforced for every new multi-page extractor.
- **Phase 5 — Contact/social:** partial production foundation; broader verified-page expansion pending.
- **Phase 6 — Actual jobs:** C12 M4 foundation exists; broader sitemap/detail acquisition pending.
- **Phase 7 — Dated activity:** C12 M3 foundation exists; RSS/sitemap/structured expansion pending.
- **Phase 8 — NAV batch experiment:** later, measurement-gated.
- **Phase 9 — BRREG bulk request optimization:** later, cache/freshness/evidence-rule gated.
- **Phase 10 — Adaptive request scheduler:** after enough useful candidate surfaces exist.
- **Phase 11 — Fresh large validation/release candidate:** final promotion gate before another Builderr revision.

Immediate path:

> Phase 2 exact website coverage -> Phase 3 bounded sitemap/target pages -> Phase 4 page-level observation integrity -> Phase 5/6/7 contact/social/jobs/activity -> Phase 10 adaptive allocation -> Phase 11 release qualification.

## 6. Phase 0 — repository reality check

Trace the actual evaluator path before changing it:

```text
organisation number
 -> acquisition
 -> normalization
 -> observations/evidence
 -> canonical projection
 -> output contract
 -> final envelope/product
```

Verify `scripts/run_signalpost_v8.py`, delegated runners, official modules, website discovery/identity, external observations, evidence storage, budgets, refresh/change, synthesis and final serialization. Repository code and live GitHub state override assumptions.

## 7. Phase 1 — collected-vs-emitted recovery

Status: **closed**.

Promotion rule remains useful for future audits:

> Recover high-confidence facts already fetched before spending new network requests.

Phase 1 proved this strategy can materially improve evaluator-visible coverage with zero new source requests.

## 8. Phase 2 — website discovery improvement

Status: **active**.

Goal: materially increase companies with an **exact verified website** without weakening identity precision.

Current consumed Phase-A 100-company baseline:

- exact verified websites: 7
- not available: 87
- ambiguous: 4
- failed: 2
- first-party social-profile claims: 10
- first-party contact-email claims: 6

Therefore site reach is the key upstream multiplier for later external families.

Existing candidate families:

1. BRREG-declared website;
2. registry email domain;
3. deterministic legal-name `.no` domains;
4. Wikidata official website linked through exact organisation number;
5. hyphenated `.no` fallback;
6. stored/official hints only when rights-safe and evidence-safe.

Known rejected/do-not-repeat paths without new evidence:

- guessed `.com` expansion;
- broad legal-name rule/ML candidate ranking that previously produced no useful net-new sites;
- annual-report domain hints after zero-yield screening;
- Norid public organisation-number lookup: rights/purpose terms are incompatible with Signalpost use;
- provider/model-search PRs #78/#84 unless Builderr explicitly resolves provider/key/budget and the project constraint changes.

### Active Phase-2 experiment candidate: BRREG subunit homepage hints

BRREG underunit records are already fetched through the production `locations` module. The public underunit schema includes `hjemmeside` and exact `overordnetEnhet`, but current `normalize_locations()` discards `hjemmeside`.

Experiment rules:

- retain the already-fetched subunit `hjemmeside` field; zero added official lookup requests;
- use the exact parent/subunit relationship only to nominate a candidate;
- never inherit the subunit site directly to the parent;
- independently fetch the candidate page;
- require the existing target-main-entity website identity gate to pass;
- preserve conflicting-org-number rejection;
- keep publication disabled during initial screen;
- integrate only if meaningful net-new exact sites transfer on consumed companies;
- production integration must stay within four logical site requests/profile by ordering/substitution, not by adding a fifth request.

Phase-2 measurement must report:

- unresolved companies screened;
- companies with one or more subunit homepage hints;
- candidate domains attempted;
- exact verified target-company websites;
- ambiguous/quarantined candidates;
- wrong-company candidates;
- baseline -> new -> net-new verified website companies;
- added logical requests and conservative charge;
- runtime/latency impact;
- third-party cost.

Decision must be explicit: PROMOTE, RETUNE, SHELVE or DROP.

Do not consume a fresh cohort until a consumed-cohort screen demonstrates meaningful transfer.

## 9. Phase 3 — sitemap + targeted crawler

After an exact domain is verified, discover a bounded set of high-yield pages through homepage links, robots sitemap declarations, `/sitemap.xml`, sitemap indexes, RSS/Atom hints and common feed endpoints when justified.

Rank page classes by expected new information-family gain:

1. job/careers detail
2. news/press detail
3. contact
4. team/leadership
5. about
6. product/legal/privacy pages only when specifically useful

Never crawl an entire sitemap. Optimize scored family coverage per request.

## 10. Phase 4 — page-level observation/evidence hardening

Every multi-page fact must remain bound to the exact page that supplied it. Prefer structured data when trustworthy:

- JSON-LD `Organization`, `LocalBusiness`, `Person`, `JobPosting`, `NewsArticle`, `Article`
- OpenGraph
- canonical tags
- `<time datetime>`
- semantic HTML
- `mailto:`
- `tel:`
- `sameAs`

No supporting page-local evidence means no publication.

## 11. Phase 5 — contact and social enrichment

Extract from verified company-owned pages only:

- email
- phone
- address
- social URLs

Prefer structured or explicitly labelled declarations. A social publication means only that the verified company page declared that profile URL; do not scrape social platforms for follower counts/posts.

Track net-new companies, not number of links.

## 12. Phase 6 — actual job-posting acquisition

Invariant:

> careers page != active job posting

Require a concrete role, specific detail/application URL, exact employer context and current-job evidence such as `JobPosting` data or equally strong structured detail. Never inherit parent/subsidiary jobs without permitted exact legal semantics.

## 13. Phase 7 — dated first-party activity

Goal: at least one reliable dated company-owned update across many companies.

Use exact news details, RSS/Atom, sitemap article candidates, `NewsArticle`/`Article` JSON-LD and explicit page-local publication dates. Avoid ambiguous date text and third-party news.

## 14. Phase 8 — NAV batch experiment

Only reconsider NAV through a once-per-run vacancy-feed architecture indexed by employer organisation number. Map subunit -> parent only through exact BRREG relationship, then fetch details only for matched companies. Promote only on meaningful net-new company coverage.

## 15. Phase 9 — BRREG bulk optimization

Screen whether official bulk entities/roles/subunits can safely replace selected live calls under Builderr cache/freshness/evidence rules. Any saved request budget should be deliberately reallocated to higher-yield website/jobs/activity work. Never sacrifice required freshness.

## 16. Phase 10 — adaptive request scheduler

Prioritize requests by:

```text
expected net-new scored company-family gain
-------------------------------------------
identity risk + request cost + latency risk
```

Examples:

- no verified site -> stop site enrichment;
- verified site + missing contact -> contact candidate may outrank duplicate social work;
- verified site + sitemap + missing jobs/activity -> specific job/news detail outranks low-yield about pages;
- already-covered families should not consume scarce requests.

ML may later rank candidates but never authorize publication.

## 17. Phase 11 — fresh validation and release candidate

Maintain development, validation and final untouched cohorts. Track every touched organisation number.

Before another Builderr revision require:

- fresh evaluator-shaped 100-company run;
- 100/100 terminal envelopes;
- zero contract/evidence/canonical/synthesis integrity errors;
- zero known wrong-company publications;
- manual audit of every newly introduced external family/case;
- request/runtime/cost report;
- exact commit SHA freeze;
- CI green on exact head;
- reproducible artifacts;
- synthesis/UX preserved or improved.

## 18. Measurement harness

Every material experiment reports company-level coverage:

- input/terminal companies;
- verified website companies;
- contact email/phone companies;
- social companies and multi-platform companies;
- careers-page companies;
- concrete job-posting companies;
- dated-update companies;
- people/leadership companies;
- location/workplace companies;
- financial/workforce/change-history companies;
- total published claims;
- evidence/contract/canonical/synthesis failures;
- wrong-company and ambiguous/rejected candidates;
- logical requests and conservative charge;
- runtime/latency where available;
- third-party cost.

Always compare:

```text
BASELINE -> NEW -> NET-NEW COMPANIES
```

## 19. Promotion criteria

A source/strategy is promoted only if relevant gates pass:

1. meaningful net-new company coverage;
2. very high exact-entity precision;
3. complete source/page evidence;
4. deterministic behavior;
5. acceptable rights;
6. refresh-compatible semantics;
7. request/time budget fit;
8. no meaningful regression elsewhere.

Decision labels:

- **PROMOTE**
- **RETUNE**
- **SHELVE**
- **DROP**

Rejected experiments belong in `docs/IMPLEMENTATION_LOG.md` so they are not repeated.

## 20. Adversarial entity validation

Maintain tests/fixtures for:

- same/similar legal names;
- parent/subsidiary/group sites;
- subunits and shared domains;
- chain/franchise;
- company-vs-brand collision;
- directories/marketplaces;
- same municipality/postcode;
- pages containing multiple organisation numbers;
- former names/rebrands;
- parked/hosting/service-provider pages.

## 21. Failure resilience and monitoring

Handle timeouts, connection resets, 403/404/410/429/5xx, redirect loops, robots blocks, invalid HTML, oversized pages and SSL failures without losing the terminal company envelope.

Refresh must distinguish conclusive change from source failure for websites, contacts, social profiles, jobs, news, roles and financial periods.

## 22. Later-only work

Secondary official sources such as Patentstyret, Støtteregisteret or Doffin require rights/reach/exact-ID screening first. Optional ML ranking and evidence-bounded AI extraction come only after deterministic Phase-2–7 gains. AI may extract from already-fetched verified text only when every fact has a deterministic supporting span; it may never establish legal identity or invent official numbers.

## 23. Synthesis and UX targets

Preserve/improve evidence-bounded synthesis covering what the company does, finances, people, locations, workforce, hiring, activity, changes, unknowns and source/effective dates.

Keep the evaluator-facing product directly linked to generated data with search/select, evidence drill-down, freshness/change context and explicit unavailable states. Do not prioritize cosmetic redesign while recall remains the main score gap.

## 24. Submission strategy

Do not submit after each feature. The next Builderr revision should bundle coordinated safe recall gains: exact site reach, multi-page enrichment, useful contact/social/jobs/activity coverage, complete evidence and adaptive request allocation, while preserving synthesis/UX and zero known wrong-company publications.

## 25. Continuity protocol

Every implementation chat must begin with:

1. `docs/CONTINUATION_STATE.md`;
2. this file;
3. current GitHub `main` and open PR metadata.

If GitHub is ahead, reconcile the docs first.

At the end of every substantial implementation session:

1. update `docs/CONTINUATION_STATE.md`;
2. append material experiments/milestones to `docs/IMPLEMENTATION_LOG.md`;
3. update this roadmap when phase status, acceptance criteria or strategy changes;
4. record exact branch/head/PR/run IDs/artifacts/coverage/precision/budget/blockers/next actions;
5. distinguish IMPLEMENTED, TESTED, QUALIFIED, MERGED and POST-MERGE GREEN.

The repository, not chat history, is the source of truth.
