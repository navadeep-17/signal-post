# Signalpost — Current Continuation State

Last updated: 2026-10-04 (Asia/Kolkata)

Repository state and live GitHub metadata are authoritative over chat history. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; architecture and phase order belong in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Live `main` immediately before this update:

`275e040dd4f171c755aa659555ce31d94ea59ccd`

That tip is documentation-only on top of Phase-A production merge `8a729036350c019e107cd68a08641f1fff6796f6`; production code semantics remain Phase A / V8.

Open PRs #76, #78 and #84 are historical/experimental and are not the active production path.

Active experiment branch:

- branch: `experiment/phase3-dated-activity-discovery`
- PR: none
- exact measured head: `5ed4f3a83eab592c0a2a2c7d96e0865cf874bce0`
- state: **IMPLEMENTED + TESTED + MEASURED / DROP / NOT QUALIFIED / NOT MERGED**

No Phase-2, NAV or Phase-3 experiment is qualified or merged.

## 2. Lifecycle state

### Phase 1 / collected-vs-emitted exact BRREG recovery

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** yes
- **MERGED:** yes
- **POST-MERGE GREEN:** yes

Phase 1 is closed.

### Phase 2 / exact website-discovery improvement

- **IMPLEMENTED:** experiment-only strategies
- **TESTED:** yes
- **QUALIFIED:** no
- **MERGED:** no
- **POST-MERGE GREEN:** not applicable
- **STATE:** **CANDIDATE-SOURCE CONSTRAINED / SHELVED under current $0 rights-safe sources**

The dominant failure is candidate generation, not identity verification. Do not add more legal-name domain guesses without a genuinely new rights-safe candidate source.

### Phase 3 / bounded verified-site dated activity discovery

- **IMPLEMENTED:** yes, experiment-only sitemap and RSS/Atom screens
- **TESTED:** yes, full regressions passed
- **QUALIFIED:** no
- **MERGED:** no
- **POST-MERGE GREEN:** not applicable
- **STATE:** **DROP / SHELVED on current verified-site cohort**

Both bounded sitemap and declared-feed paths produced zero precision-clean dated-activity companies.

### Phase 4 / page-level observation and evidence hardening

- **IMPLEMENTED:** not yet
- **TESTED:** not yet
- **QUALIFIED:** no
- **MERGED:** no
- **STATE:** **ACTIVE NEXT PHASE**

Phase 3 exposed a concrete date-selection precision defect that must be fixed before further source expansion.

## 3. Retained Phase-A baseline

Second untouched qualification run `37203580574`:

- fresh cohort: 100 unique, overlap 0
- cohort SHA: `4078579d4a581da0b8d56e4d03d567c4032d43e93c8bb94ee3c02b140b651e40`
- 100/100 terminal
- evidence/contract/canonical/synthesis errors: 0
- logical requests: 666
- conservative charge: 1,332/2,000
- runtime: 460.916 s
- third-party cost: $0
- search API requests: 0
- artifact: `phasea-final-fresh-disjoint-100-v2`, ID `11304401011`
- digest: `sha256:31e12e11f2746dcf8c0b6454ab6052ab44281176363b6934889d22d57a08800b`

Frozen consumed Phase-2/3 profiles contain 7 exact verified websites.

## 4. Phase-2 conclusions retained

Rejected / do-not-repeat under current constraints:

- guessed `.com` expansion
- broad rule/ML legal-name candidate ranking with zero net-new exact sites
- annual-report domain hints after prior zero-yield screen
- Norid public lookup because rights/purpose restrictions are incompatible
- exact-parent subunit homepage hints: 0/3 exact target sites, run `37208360582`, artifact `11306100222`
- exact-parent subunit email-domain hints: 0/10 exact target sites, run `37209911261`, artifact `11306935410`
- same-domain secondary identity verification: 0/4, run `37211887561`, artifact `11307036767`, digest `sha256:b552fe0a4961148a9a0e3dfac520dc9535cfe3171af624cf3efc90a885c59937`
- NAV exact-org vacancy feed: 0/100 target companies after complete 180-day traversal, run `37214017085`, artifact `11307433276`, digest `sha256:917ad28cc991fdeb70a8f78617cbb8c0c1fbbf49e8c6ce598455630127d7e5db`
- provider-dependent model/search PRs #78/#84 unless Builderr resolves provider/key/budget and the $0 constraint changes

Failure funnel on the frozen 100:

- H1c deterministic `.no`: 96 attempts; 79 blocked; **78 DNS non-resolution**; 12 loaded; 3 exact sites verified
- H1g hyphenated `.no`: 73 attempts; **73/73 DNS non-resolution**; 0 verified

This is sufficient evidence to shelve more speculative domain generation for now.

## 5. Phase-3 sitemap activity screen

Decision: **DROP / NOT QUALIFIED / NOT MERGED**.

- branch: `experiment/phase3-dated-activity-discovery`
- measured head: `5f6540fffe5ce3656f2c8611da8cc390409ecddd`
- run `37215062164`: PASS
- artifact `phase3-sitemap-activity-screen`, ID `11308151116`
- digest `sha256:fcbd1aa10c91b7f468894a81e6fe88d797224fe1d058ac472a4d049f8e800d35`
- publication disabled; full regressions passed
- verified sites screened: 7/7
- robots sitemap hints: 5 companies
- sitemap indexes requiring an extra child-sitemap request: 4
- direct urlsets: 1, with no bounded activity candidate
- accepted dated-activity companies: **0**
- actual experiment requests: 13
- projected production incremental site requests with cached robots policy: 6
- projected combined conservative charge: 1,344/2,000
- runtime: 8.614 s
- cost: $0; search requests: 0; wrong-company publications: 0

Sitemap `<lastmod>` remained ranking-only and could never authorize publication. Four sitemap indexes would require an extra child-sitemap request and therefore do not fit the two-idle-request / four-site-request theorem.

## 6. Phase-3 RSS/Atom activity screen

Final decision: **DROP / NOT QUALIFIED / NOT MERGED**.

Initial screen:

- run `37215447605`: PASS
- artifact `phase3-rss-activity-screen`, ID `11308540417`
- digest `sha256:8d8688618568204f6aea2d9c3b56d2604f15e267c85b96ba21dfb67f83a1548b`
- 2/7 sites declared RSS feeds
- one apparent Bike2Work hit was produced by the existing detail-date extractor

Manual precision audit rejected that apparent hit. The RSS item was the standard WordPress placeholder `Hello world!`, dated 16 Nov 2021, while the detail extractor selected a separate `04/10/2026` date-labelled element from the page. Feed dates were never treated as positive publication evidence.

Precision-hardened rerun:

- exact head: `5ed4f3a83eab592c0a2a2c7d96e0865cf874bce0`
- run `37215793652`: PASS
- artifact `phase3-rss-activity-screen`, ID `11308790825`
- digest `sha256:f2c10fbeb86d0f04bdd8a53e3594bd2aaf2e1ef957ae36eb5bdfd29c41714cde`
- full regressions: PASS
- publication disabled
- verified sites screened: 7/7
- companies with declared feed hint: 2
- RSS feeds parsed: 2
- accepted precision-clean dated-activity companies: **0**
- decisions: 4 no feed hint, 1 feed with no activity item, 1 robots unavailable, 1 generic CMS placeholder reject
- actual experiment network requests: 16
- actual bytes: 1,631,210
- projected production incremental site requests: 3
- projected combined conservative charge: 1,338/2,000
- projected headroom: 662
- runtime: 13.374 s
- third-party cost: $0; search requests: 0; wrong-company publications: 0

The hardened experiment added two generic vetoes: standard CMS placeholder posts cannot become company activity, and a feed/detail year contradiction can veto an apparent detail fact. Feed metadata remains ranking/conflict evidence only, never positive publication proof.

## 7. Precision and budget invariants

- exact organisation number remains the legal-entity anchor
- candidate generation is never publication proof
- wrong-company publication is a hard failure
- exact-page URL + retrieval/hash provenance remains mandatory
- dates must be page-local and semantically tied to the article/update; archive/sitemap/feed dates cannot independently publish a fact
- missing/blocked/ambiguous stays explicit
- third-party API spend remains $0
- no paid/search API path is active
- four logical site requests/profile remains the production site ceiling
- new site enrichment must fit by adaptive ordering/substitution, not a fifth site request
- fresh cohorts remain reserved for promotion after meaningful consumed-cohort transfer

## 8. Known blockers

1. Exact website reach remains only ~7–8/100 under current rights-safe $0 sources.
2. Phase-2 candidate generation is dominated by non-resolving guessed domains.
3. Phase-3 sitemap/RSS activity transfer was zero after precision hardening.
4. The existing first-party date selector can prefer an unrelated/dynamic date-labelled element over the true publication date when a page contains multiple dates. This is now a known precision defect and is the immediate Phase-4 target.

## 9. Exact next 1–3 actions

1. Create a clean Phase-4 branch from current `main`; do not merge the Phase-3 experiment branch.
2. Add adversarial regressions for competing page dates and generic CMS placeholder updates, then harden `first_party_activity` date selection so stronger explicit publication metadata / ordered page-local candidates win and ambiguous dynamic/comment dates abstain.
3. Run full CI plus a consumed-cohort output diff. Promote only if existing qualified claims are preserved or made more conservative, with no new false positive and no request increase. No fresh cohort yet.

## 10. NEXT

**NEXT: Phase 4 page-level dated-activity evidence hardening. Fix competing-date selection and generic-placeholder acceptance before any further source expansion; consumed cohort only, no fresh qualification yet.**
