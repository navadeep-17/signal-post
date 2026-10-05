# Signalpost 70+ Implementation Master Plan

Last updated: 2026-10-04

This document is the canonical engineering roadmap toward a Builderr 70+ result. `docs/CONTINUATION_STATE.md` owns exact live branch/PR/run state; `docs/IMPLEMENTATION_LOG.md` owns historical experiments and decisions. GitHub and live Builderr rules outrank stale documentation.

## 0. Objective

Goal:

> Build the strongest possible Signalpost revision capable of scoring 70+ while preserving exact-company precision, evidence quality and evaluator reproducibility.

Working target:

- Recall / coverage: 22–24+/50
- Precision / evidence: 28–29+/30
- Synthesis: 12/12
- UX: 8/8
- Total: 70–73+

Primary optimization target: **net-new companies covered per scored information family**, not raw claim count.

Core strategy:

> ATTEMPT MORE -> VERIFY STRICTLY -> PUBLISH CONSERVATIVELY

## 1. Non-negotiable invariants

1. Exact organisation number is the legal-entity anchor.
2. Candidate generation is never publication proof.
3. Parent/group/subsidiary/subunit/franchise relation alone never authorizes inheritance of a website, job or public-activity fact.
4. Legal-name similarity, search rank, URL similarity or municipality alone never authorize a site.
5. Ambiguous identity means abstain.
6. Every external fact keeps exact page URL, retrieval time, page/content SHA-256 and page-local supporting evidence.
7. One page's hash may never support a fact observed only on another page.
8. Missing/blocked/ambiguous is never converted to false absence or zero.
9. Official and financial facts remain deterministic source-backed facts.
10. Source failure must not drop the terminal company envelope.
11. Refresh/change processing remains deterministic and idempotent.
12. Third-party API spend remains $0 unless explicitly changed.
13. Four logical site requests/profile remains the site ceiling until separately requalified.
14. Fresh cohorts are scarce and are consumed permanently once used.
15. No experimental source enters production without meaningful transfer, precision audit, rights review and budget fit.

## 2. Architecture

```text
organisation number
 -> exact BRREG legal entity
 -> official exact-ID sources
 -> bounded external candidates
 -> exact identity verification
 -> page-local typed observations
 -> evidence-backed canonical claims
 -> changes/history
 -> synthesis/product
```

Typed families remain conceptually separate: identity, registry, financials, people, locations, website, contact, social, hiring, activity and changes.

## 3. Current production foundation

Production now includes:

- exact BRREG entity anchoring and exact-live registry evidence
- financials, roles, people, locations/workplaces and group context
- broad Phase-1 exact-live BRREG breadth recovery
- canonical claims/evidence/change output
- terminal-envelope behavior
- deterministic refresh/change tracking
- request/runtime/cost accounting
- registry website, registry-email-domain, deterministic `.no`, exact-org Wikidata and hyphenated `.no` discovery
- strict exact-site verification with namesake/parent/franchise/shared-domain hardening
- first-party email/social observations
- registry + annual-report workforce
- annual-report company-description fallback
- bounded dated first-party news detail foundation
- bounded current first-party job-posting foundation
- Phase-4 page-local dated-activity precision hardening
- $0 third-party API spend

Phase-1 production merge: `8a729036350c019e107cd68a08641f1fff6796f6`.
Phase-4 production merge: `07f01734ba9bb5ed850a5a494c6c38f7cdaf66a3`.

## 4. Phase status map

- **Phase 0 — Repository reality check:** substantially complete; repeat whenever repo/live state changes materially.
- **Phase 1 — Collected-vs-emitted recovery:** **CLOSED / QUALIFIED / MERGED / POST-MERGE GREEN**.
- **Phase 2 — Exact website discovery improvement:** **SHELVED / CANDIDATE-SOURCE CONSTRAINED** under current $0 rights-safe sources.
- **Phase 3 — Bounded sitemap/RSS dated activity:** **SCREENED / DROP on current consumed cohort**.
- **Phase 4 — Page-level observation/evidence hardening:** **CLOSED / IMPLEMENTED / TESTED / MERGED / POST-MERGE GREEN**.
- **Phase 5 — Contact/social enrichment:** partial production foundation; revisit only with a new structured/multi-family hypothesis.
- **Phase 6 — Actual jobs:** C12 M4 foundation exists; NAV exact-org batch screen did not transfer.
- **Phase 7 — Dated activity:** production C12 M3 foundation remains; Phase-3 RSS/sitemap expansion did not transfer.
- **Phase 8 — NAV exact-org vacancy screen:** **DROP**.
- **Phase 9 — BRREG bulk/request optimization:** later and freshness-gated.
- **Phase 10 — Adaptive request scheduler:** after a new high-yield surface exists.
- **Phase 11 — Fresh validation/release candidate:** final promotion gate.

Immediate path:

> consumed-only rights/reach/exact-ID source-selection audit -> choose one deterministic high-yield family/source if justified -> Phase 10 allocation if needed -> Phase 11 fresh release qualification.

## 5. Phase 1 — collected-vs-emitted recovery

Status: **closed**.

Reusable rule:

> Recover high-confidence facts already fetched before spending new requests.

This phase materially improved evaluator-visible coverage at zero new source/request cost and remains the best model for future low-risk gains.

## 6. Phase 2 — website discovery improvement

Status: **shelved**.

Consumed-cohort website reach remains about 7–8/100. The dominant failure is candidate-source quality, not verification strictness.

Rejected/do-not-repeat without genuinely new evidence:

- guessed `.com` expansion
- broad legal-name rule/ML candidate ranking
- annual-report domain hints
- Norid public lookup because rights/purpose restrictions are incompatible
- exact-parent subunit homepage hints: 0/3
- exact-parent subunit email domains: 0/10
- same-domain secondary identity verification: 0/4
- provider/model-search PRs #78/#84 unless Builderr resolves provider/key/budget and the $0 constraint changes

Measured funnel on frozen 100:

- H1c deterministic `.no`: 96 attempts, 78 DNS non-resolution failures, 12 loaded, 3 verified
- H1g hyphenated `.no`: 73 attempts, 73 DNS non-resolution failures, 0 verified

Conclusion:

> Reopen Phase 2 only for a genuinely new rights-safe candidate source. Do not weaken identity rules or keep generating speculative domains.

## 7. Phase 3 / 7 — bounded dated first-party activity

Status: **screened / DROP for current sitemap + RSS expansion**.

### Sitemap screen

Run `37215062164`, artifact ID `11308151116`:

- 7 verified domains screened
- 5 robots sitemap hints
- 4 sitemap indexes required an extra discovery request
- 1 direct urlset had no bounded activity candidate
- 0 accepted dated-activity companies
- projected combined conservative charge 1,344/2,000

Sitemap `<lastmod>` remained ranking-only and never publication evidence.

### RSS/Atom screen

Initial run `37215447605` exposed a precision false positive on a standard WordPress `Hello world!` post. The feed item was dated 2021 while an unrelated/dynamic page element looked like a 2026 date.

Hardened rerun `37215793652`, artifact ID `11308790825`:

- 7 verified domains screened
- 2 declared RSS feeds
- 0 precision-clean dated-activity companies
- 4 no feed hint
- 1 no feed activity item
- 1 robots unavailable
- 1 generic CMS placeholder rejected
- projected combined conservative charge 1,338/2,000
- $0, zero wrong-company publications

Conclusion:

> Do not productionize the current sitemap/RSS experiment. The useful result was the precision defect it exposed; that production evidence path is now hardened by Phase 4.

## 8. Phase 4 — page-level observation and evidence hardening

Status: **CLOSED / IMPLEMENTED + TESTED + MERGED + POST-MERGE GREEN**.

Purpose: harden first-party dated-activity evidence without adding requests or new sources.

Implemented:

1. Adversarial regressions for strong publication metadata plus conflicting generic DOM date, same-rank conflicts, multiple weak text dates, preserved unique text dates and generic CMS placeholders.
2. Replaced order-insensitive concatenated date extraction with typed page-local candidate evaluation.
3. Deterministic semantic priority from publication metadata through `<time datetime>` to weaker labelled/time text.
4. Same-rank conflicting publication dates abstain.
5. Unstructured page text is accepted only if it contains exactly one unique date.
6. Generic WordPress/CMS placeholder updates are rejected.
7. Retained update evidence records selected extraction method and raw page-local date evidence.
8. No new network request/source was added.

Validation and release:

- measured semantics head `a220089fccefd63f88555d675194ebefcdd44723`
- consumed diff run `37217368930`: PASS
- artifact `phase4-activity-evidence-consumed-diff`, ID `11308328355`
- digest `ddcf4e328edab217a016122801f1ad16f4f60c0a80d3e106b09ba5f67ed59da0`
- frozen 100: jobs 0 -> 0, updates 0 -> 0, no added/dropped URLs, no date changes
- network/search requests added 0; cost added $0; `precision_monotonic=true`
- docs-inclusive PR head Baseline CI `37219207340`: PASS
- PR #95 merged as `07f01734ba9bb5ed850a5a494c6c38f7cdaf66a3`
- post-merge Baseline CI `37219278337`: PASS
- fresh cohort intentionally not consumed because this was a precision-only, zero-request hardening phase

## 9. Phase 5 — contact/social enrichment

Extract only from verified company-owned pages. Structured or explicitly labelled declarations are preferred. Social publication means only that the verified company page declared the profile URL; do not scrape social platforms for follower/post metrics.

Do not revive the prior generic contact fallback unless a new structured or multi-family hypothesis demonstrates net-new company coverage.

## 10. Phase 6 / 8 — actual jobs and NAV

Invariant:

> careers page != active job posting

Require concrete role, specific detail/application URL, exact employer context and current-job evidence.

NAV exact-org batch screen is **DROP on consumed 100**:

- run `37214017085`
- 38 feed requests over complete 180-day window
- 90,917 unique vacancies / 9,723 active
- 0 target/subunit shortlist candidates
- 0 exact active-vacancy target companies
- projected combined charge 1,410/2,000

Reconsider NAV only if feed semantics or a direct organisation-number index materially changes.

## 11. Phase 9 — official-source/request optimization

Later, test whether BRREG bulk entities/roles/subunits can safely replace selected live calls under freshness/evidence requirements. Saved requests must be deliberately reallocated to proven high-yield work; never sacrifice required freshness.

## 12. Phase 10 — adaptive request scheduler

Prioritize by:

```text
expected net-new scored company-family gain
-------------------------------------------
identity risk + request cost + latency risk
```

Already-covered families should not consume scarce requests. ML may rank candidates later but may never authorize publication.

## 13. Phase 11 — fresh validation and release candidate

Before another Builderr revision require:

- fresh evaluator-shaped 100-company run
- 100/100 terminal envelopes
- zero contract/evidence/canonical/synthesis integrity errors
- zero known wrong-company publications
- manual audit of every newly introduced external family/case
- request/runtime/cost report
- exact SHA freeze
- exact-head CI green
- reproducible artifacts
- synthesis/UX preserved or improved

## 14. Next-source selection gate

This is the active roadmap step after Phase 4.

Do not immediately implement another connector. First build a consumed-only source/family selection matrix for plausible deterministic sources such as Doffin, Støtteregisteret or Patentstyret.

For each candidate require evidence for:

1. rights/licensing compatible with production use;
2. exact organisation-number or equally deterministic legal-entity join;
3. expected company-level reach on evaluator-shaped Norwegian companies;
4. scored information family value and likely net-new coverage;
5. request/runtime cost under the 2,000/100 theorem;
6. freshness/refresh semantics;
7. no need to loosen identity or evidence rules.

Only one bounded candidate should proceed to implementation at a time. No fresh cohort is used for source selection.

## 15. Measurement harness

Every material experiment reports company-level coverage:

- input/terminal companies
- verified website companies
- contact/social companies
- careers and concrete job companies
- dated-update companies
- people/leadership/location companies
- financial/workforce/change-history companies
- total published claims
- evidence/contract/canonical/synthesis failures
- wrong-company and ambiguous/rejected candidates
- logical requests and conservative charge
- runtime/latency/bytes where relevant
- third-party cost

Always compare:

```text
BASELINE -> NEW -> NET-NEW COMPANIES
```

## 16. Promotion criteria

Promote only when relevant gates pass:

1. meaningful net-new company coverage or a clear precision/integrity improvement
2. very high exact-entity precision
3. complete source/page evidence
4. deterministic behavior
5. acceptable rights
6. refresh-compatible semantics
7. request/time budget fit
8. no meaningful regression elsewhere

Decision labels: **PROMOTE**, **RETUNE**, **SHELVE**, **DROP**.

Rejected experiments belong in `docs/IMPLEMENTATION_LOG.md` so they are not repeated.

## 17. Adversarial validation

Maintain fixtures for similar names, parent/subsidiary/shared domains, chains/franchises, company-vs-brand collisions, same municipality/postcode, multiple organisation numbers, former names/rebrands, parked/provider pages, multiple conflicting dates and generic CMS placeholders.

## 18. Failure resilience

Handle timeouts, resets, 403/404/410/429/5xx, redirects, robots blocks, invalid/oversized content and SSL failures without losing terminal envelopes. Refresh must distinguish conclusive change from source failure.

## 19. Later-only work

Secondary official sources such as Patentstyret, Støtteregisteret or Doffin require rights/reach/exact-ID screening first. Optional ML ranking and evidence-bounded AI extraction come only after deterministic gains. AI may extract only from already-fetched verified text with deterministic supporting evidence; it may never establish legal identity or invent official numbers.

## 20. Synthesis and UX

Preserve evidence-bounded synthesis covering business activity, finances, people, locations, workforce, hiring, activity, changes, unknowns and source/effective dates. Keep search/select, evidence drill-down, freshness/change context and explicit unavailable states. Do not prioritize cosmetic redesign while recall remains the main score gap.

## 21. Submission strategy

Do not submit after each feature. Submit only after a meaningful qualified bundle with exact SHA, reproducible artifacts, manual precision audit, CI green, request/runtime/cost proof and updated continuation state.

## 22. Continuity protocol

At the end of every substantial session update:

1. `docs/CONTINUATION_STATE.md`
2. `docs/IMPLEMENTATION_LOG.md`
3. this roadmap whenever phase status, acceptance criteria or strategy changes

Always distinguish **IMPLEMENTED**, **TESTED**, **QUALIFIED**, **MERGED**, and **POST-MERGE GREEN**.

## 23. NEXT

**Run a consumed-only deterministic source/family selection audit. Screen rights, exact-ID join quality, likely evaluator-shaped reach and request/runtime budget for Doffin, Støtteregisteret, Patentstyret or another official source before implementing a connector. No fresh cohort yet.**

---

## 2026-10-05 roadmap advancement — deterministic source selection -> Phase 7 Støtteregisteret -> Phase 11

Status: **SOURCE SELECTION COMPLETE / PHASE 7 PROMOTION QUALIFIED ON CONSUMED V8 / PHASE 11 NEXT AFTER MERGE**

The post-Phase-4 deterministic source/family screen selected Brønnøysundregistrene Støtteregisteret because it combines NLOD rights, exact organisation-number recipient identity, recent dated events, one shared batch request and meaningful company-level reach. The final production semantics accept only the **primary recipient organisation number**, never `Spesifisert mottaker` or the granting authority, and publish typed `official.support_award` claims rather than company-authored news.

The hardened actual-V8 consumed qualification (`37254237936`, artifact `11321344340`) passed on 100 already-consumed certified companies: 100 terminal, 11 support companies, 46 support claims/facts, zero contract/canonical/synthesis/external/integrity failures, $0 third-party cost, 1 support request, 1 BRREG change-feed request, H2g ceiling 97, 1,366 observed conservative requests and exactly 2,000 theoretical conservative requests. External wall runtime was 784 s.

The parallel exact-org Common Crawl Stage-4 path remains **SHELVED**: 3,000 generic domains yielded 453 indexed org numbers, only 4/5,900 consumed-company overlap and 2 net-new verified sites. This is far below the 20+/100 website-breakthrough threshold.

Roadmap consequence: do not spend the next main-track cycle on another speculative connector. Complete clean merge/post-merge qualification of Støtteregisteret, then advance to **Phase 11 fresh validation / release candidate**. A Builderr revision remains gated on fresh evaluator-shaped evidence, manual audit and an exact SHA/artifact freeze.
