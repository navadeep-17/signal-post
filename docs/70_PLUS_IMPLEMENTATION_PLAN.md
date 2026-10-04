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

Production already includes exact BRREG anchoring; exact-live/bulk registry; financials; roles/people/locations/group context; canonical claims/evidence/changes; terminal envelopes; deterministic refresh; request/runtime/cost accounting; bounded website discovery; strict exact-site verification; first-party contact/social; registry/annual-report workforce; annual-report description; bounded first-party dated news detail; bounded current job-posting logic; and $0 third-party API spend.

Phase 1 recovered broad exact-live BRREG facts already present in fetched data but previously not evaluator-visible: registration/address/purpose/contact facts, postal address, foundation/articles dates, enterprise/VAT states and dates, institutional sector, capital and forced-dissolution state.

## 5. Phase status map

- **Phase 0 — Repository reality check:** substantially complete; repeat when repo state changes materially.
- **Phase 1 — Lost-claim / collected-vs-emitted recovery:** **CLOSED / QUALIFIED / MERGED / POST-MERGE GREEN**.
- **Phase 2 — Website discovery improvement:** **SHELVED / CANDIDATE-SOURCE CONSTRAINED** under current $0 rights-safe sources.
- **Phase 3 — Sitemap/RSS + targeted crawler:** **SCREENED / DROP on current verified-site cohort**.
- **Phase 4 — Observation/evidence hardening:** **ACTIVE NEXT PHASE**.
- **Phase 5 — Contact/social:** partial production foundation; no generic contact fallback without new evidence.
- **Phase 6 — Actual jobs:** C12 M4 foundation exists; NAV batch experiment did not transfer on consumed 100.
- **Phase 7 — Dated activity:** production foundation exists, but source expansion is paused until Phase 4 date-evidence hardening is complete.
- **Phase 8 — NAV batch experiment:** **SCREENED / DROP on consumed 100**.
- **Phase 9 — BRREG bulk request optimization:** later, cache/freshness/evidence-rule gated.
- **Phase 10 — Adaptive request scheduler:** after more useful verified-domain surfaces exist.
- **Phase 11 — Fresh large validation/release candidate:** final promotion gate.

Immediate path:

> Phase 4 page-local date/evidence integrity -> selectively reopen Phase 3/5/6 only with a new measured hypothesis -> Phase 10 adaptive allocation -> Phase 11 fresh release qualification.

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

Repository code and live GitHub state override assumptions.

## 7. Phase 1 — collected-vs-emitted recovery

Status: **closed**.

Reusable rule:

> Recover high-confidence facts already fetched before spending new network requests.

Phase 1 proved this can materially improve evaluator-visible coverage at zero new source/request cost.

## 8. Phase 2 — website discovery improvement

Status: **shelved under the current source constraints**.

Consumed-cohort website reach remains about 7–8/100. Existing production candidate families remain BRREG-declared website, registry email domain, deterministic legal-name `.no`, exact-org Wikidata, and hyphenated `.no`.

Rejected/do-not-repeat without genuinely new evidence:

- guessed `.com` expansion
- broad legal-name rule/ML ranking with no useful transfer
- annual-report domain hints after zero yield
- Norid organisation-number lookup because public-use terms are incompatible
- exact-parent BRREG subunit homepage hints: 0/3
- exact-parent BRREG subunit email domains: 0/10
- same-domain secondary identity verification for loaded quarantined registry sites: 0/4
- provider/model-search PRs #78/#84 unless Builderr resolves provider/key/budget and the $0 constraint changes

Measured root cause on the frozen 100:

- H1c deterministic `.no`: 96 attempts, 78 DNS non-resolution failures, 12 loaded, 3 verified
- H1g hyphenated `.no`: 73 attempts, 73 DNS non-resolution failures, 0 verified

Conclusion: candidate-source quality, not a too-strict verification gate, is the dominant Phase-2 bottleneck.

## 9. Phase 3 — sitemap/RSS + targeted crawler

Status: **DROP / SHELVED on the current verified-site cohort**.

Two bounded consumed-cohort screens were completed with publication disabled and no fresh cohort.

### Sitemap screen

- run `37215062164`
- artifact `phase3-sitemap-activity-screen`, ID `11308151116`
- 7/7 verified sites screened
- robots sitemap hints on 5 companies
- 4 sitemap indexes required an extra child-sitemap request that does not fit the current two-idle-request theorem
- 1 direct urlset had no bounded activity candidate
- accepted dated-activity companies: 0
- projected combined conservative charge: 1,344/2,000
- $0, zero wrong-company publications

### RSS/Atom screen

Initial apparent Bike2Work activity was rejected during manual precision audit because a generic WordPress `Hello world!` feed item from 2021 was paired with an unrelated dynamic date-labelled page element from 2026.

Precision-hardened rerun:

- exact head `5ed4f3a83eab592c0a2a2c7d96e0865cf874bce0`
- run `37215793652`
- artifact `phase3-rss-activity-screen`, ID `11308790825`
- 7/7 verified sites screened
- 2 sites declared feeds; 2 feeds parsed
- accepted precision-clean dated-activity companies: 0
- projected production incremental site requests: 3
- projected combined conservative charge: 1,338/2,000
- $0, zero wrong-company publications

Feed/sitemap metadata remains nomination/ranking/conflict evidence only; it cannot independently publish a company update.

Decision: do not merge or fresh-qualify Phase 3. Reopen only after Phase 4 evidence hardening and a genuinely new measured discovery hypothesis.

## 10. Phase 4 — page-level observation/evidence hardening

Status: **ACTIVE NEXT PHASE**.

Phase 3 exposed a concrete production-risk defect: when a detail page contains multiple dates, the existing first-party activity extractor can select an unrelated dynamic/comment/date-labelled element instead of the true publication date.

Immediate hardening rules:

1. Add adversarial regressions for competing page dates, including a correct article publication date plus unrelated current/dynamic/comment dates.
2. Prefer semantically explicit publication metadata in deterministic order: trusted `NewsArticle`/`Article` JSON-LD `datePublished`, OpenGraph `article:published_time`, explicit `datePublished` metadata, then unambiguous article-local `<time datetime>` / labelled publication date.
3. A generic date-labelled element must never outrank stronger article publication metadata.
4. If multiple equally plausible page-local publication dates conflict materially, abstain rather than guess.
5. Standard CMS placeholder posts such as default WordPress `Hello world!` must not become company activity.
6. Feed/sitemap/archive timestamps may nominate or veto but are not positive publication evidence by themselves.
7. Every retained activity fact must preserve the exact detail URL, detail content hash, extraction method, supporting span/structured node and effective/publication date.
8. No new network requests are required for this phase.

Promotion bar:

- full CI green
- existing qualified dated-activity claims preserved or made more conservative
- adversarial competing-date fixtures pass
- no new false-positive activity
- no request/runtime budget increase
- consumed-cohort output diff manually reviewed

No fresh cohort yet.

## 11. Phase 5 — contact and social enrichment

Extract from verified company-owned pages only. Prefer structured or explicitly labelled declarations. A social publication means only that the verified company page declared the profile URL; do not scrape social platforms for follower counts/posts.

Do not revive a generic idle contact-page request without a new multi-family or structured-data hypothesis; the prior fallback did not transfer.

## 12. Phase 6 — actual job-posting acquisition

Invariant: careers page != active job posting.

Require a concrete role, specific detail/application URL, exact employer context and current-job evidence. The NAV batch screen is not a production path after zero consumed-cohort transfer.

## 13. Phase 7 — dated first-party activity

Status: **paused for source expansion; Phase 4 hardening active**.

The C12 M3 first-party detail path remains the production foundation. New RSS/sitemap source expansion stays shelved until date evidence is robust against competing/dynamic dates.

## 14. Phase 8 — NAV batch experiment

Status: **DROP on consumed 100 / not merged**.

Measured branch `experiment/nav-exact-org-vacancy-screen`, head `c156fda6a5ac711b285e864270273446262d19ac`, run `37214017085`:

- complete 180-day feed traversal
- 38 feed requests / 181,234,775 bytes
- 368,428 raw events / 90,917 unique vacancies / 9,723 active
- 0 target/subunit shortlist candidates
- 0 detail requests
- 0 exact active-vacancy target companies
- 39 NAV logical requests / 78 conservative
- projected combined baseline charge 1,410/2,000
- $0 and zero wrong-company publications

Do not broaden matching post-hoc or spend a fresh cohort.

## 15. Phase 9 — BRREG bulk optimization

Later, screen whether official bulk entities/roles/subunits can safely replace selected live calls under Builderr cache/freshness/evidence rules. Any saved request budget must be deliberately reallocated to higher-yield work. Never sacrifice required freshness.

## 16. Phase 10 — adaptive request scheduler

Prioritize requests by expected net-new scored company-family gain divided by identity risk + request cost + latency risk. ML may rank candidates later but never authorize publication.

## 17. Phase 11 — fresh validation and release candidate

Before another Builderr revision require a fresh evaluator-shaped 100-company run, 100/100 terminal envelopes, zero integrity errors, zero known wrong-company publications, manual audit of every newly introduced external family/case, request/runtime/cost report, exact SHA freeze, exact-head CI green and reproducible artifacts.

## 18. Measurement harness

Every material experiment reports company-level coverage, evidence/contract/canonical/synthesis failures, wrong-company/ambiguous/rejected candidates, logical requests/conservative charge, runtime/latency/bytes, and third-party cost.

Always compare:

```text
BASELINE -> NEW -> NET-NEW COMPANIES
```

## 19. Promotion criteria

Promote only with meaningful net-new company coverage, very high exact-entity precision, complete source/page evidence, deterministic behavior, acceptable rights, refresh-compatible semantics, request/time budget fit and no meaningful regression elsewhere.

Decision labels: **PROMOTE**, **RETUNE**, **SHELVE**, **DROP**.

## 20. Adversarial entity validation

Maintain tests/fixtures for similar legal names, parent/subsidiary/group sites, subunits/shared domains, chain/franchise, company-vs-brand collisions, same municipality/postcode, multiple organisation numbers, former names/rebrands and parked/hosting/service-provider pages.

## 21. Failure resilience and monitoring

Handle timeouts, resets, 403/404/410/429/5xx, redirect loops, robots blocks, invalid HTML, oversized pages and SSL failures without losing the terminal company envelope. Refresh must distinguish conclusive change from source failure.

## 22. Later-only work

Secondary official sources such as Patentstyret, Støtteregisteret or Doffin require rights/reach/exact-ID screening first. Optional ML ranking and evidence-bounded AI extraction come only after deterministic gains. AI may never establish legal identity or invent official numbers.

## 23. Synthesis and UX targets

Preserve/improve evidence-bounded synthesis and the evaluator-facing data-linked product. Do not prioritize cosmetic redesign while recall remains the main score gap.

## 24. Submission strategy

Do not submit after each feature. The next Builderr revision should bundle coordinated safe recall gains while preserving synthesis/UX and zero known wrong-company publications.

## 25. Continuity protocol

Every implementation chat must begin with `docs/CONTINUATION_STATE.md`, this file, and current GitHub `main`/open PR metadata. If GitHub is ahead, reconcile docs first.

At the end of every substantial implementation session:

1. update `docs/CONTINUATION_STATE.md`
2. append material experiments/milestones to `docs/IMPLEMENTATION_LOG.md`
3. update this roadmap when phase status, acceptance criteria or strategy changes
4. record exact branch/head/PR/run IDs/artifacts/coverage/precision/budget/blockers/next actions
5. distinguish IMPLEMENTED, TESTED, QUALIFIED, MERGED and POST-MERGE GREEN

The repository, not chat history, is the source of truth.
