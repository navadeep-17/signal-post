# Final External Source Landscape Audit

Date: 2026-09-17

Base production SHA: `b14ef3c277d8f1512064f865d4028e23dcd8bacf`

## Decision

**STOP broad connector hunting under the current $0, exact-entity, publication-rights policy unless new evidence changes the source landscape.**

The remaining project work should move to release finalization: reconcile production documentation, freeze a new disjoint final corpus, run the current production stack at release scale, improve evidence-bounded synthesis and the existing prototype, and package the final submission.

This is not a claim that Builderr's hidden coverage or weighted external-recall thresholds have been passed. Those remain evaluator-owned and cannot be computed locally. It is an engineering prioritization decision: the remaining zero-cost sources reviewed below do not currently justify another full connector cycle relative to the value of finalization.

## Why this audit exists

H2g materially changed the project. Production now has near-universal explicit workforce evidence from BRREG live data plus exact-entity annual-account OCR, while the remaining external-footprint gaps are concentrated in ratings/reviews, public posts/mentions/engagement, sentiment, second-platform breadth, and freshness.

The local development proxy is only a diagnostic, but its current external coverage semantics are useful for preventing accidental score-hacking:

- workforce/jobs: `job_posting` or `workforce_snapshot`;
- ratings/reviews: `review`, `review_summary`, or `place_summary`;
- buzz/engagement: `public_post`, `public_mention`, or `profile_metrics`;
- sentiment: accepted evidence with a qualified sentiment label;
- breadth: at least two distinct external platforms for the company.

A government grant, patent, procurement notice, or other interesting company event must therefore not be relabelled as a review, public post, engagement metric, or sentiment signal merely to increase a local proxy score.

## Measured experiments immediately preceding this audit

### H2h — Fagfolkguiden review coverage

Decision: **DROP**.

Fresh 100-company screen:

- prior unique companies excluded before selection: 5,800;
- seed: `20261001`;
- manifest SHA-256: `08ff94cd39a07b4cb24f8ed0479e2a94c758cd47ca550f0af63cc94382ed98ef`;
- workflow run: `35136522325`;
- artifact: `h2h-fagfolkguiden-review-coverage`;
- artifact ID: `10463363228`;
- artifact digest: `sha256:700e26ae0bf81e4ac369838f6fa6463f215cb0d45471f798cbf28736a5de49d2`;
- companies with a usable aggregate rating: **0/100**;
- publication remained disabled.

The source also exposed Google-derived review content without an identified sublicensing basis suitable for production. Zero measured yield plus unresolved rights makes further work unjustified.

### H2i — NAV jobs feasibility

Decision: **SHELVE**.

NAV is technically attractive: the vacancy feed is an official Norwegian source, employer organisation numbers are available in vacancy details, and BRREG subunit relationships allow exact subunit-to-main-entity verification without fuzzy identity publication.

A bounded exploratory screen reused 20 untouched-by-NAV companies from the H2h cohort rather than consuming a new independent validation cohort.

Corrected workflow run: `35233357136` at commit `f29fc16ae7b4168478d6e00e8bdca42c72a1b050`.

Results:

- targets: 20;
- lookback: 90 days;
- feed pages: 30;
- feed items traversed: 30,000;
- active headers: 19,972;
- candidate employer headers: 7;
- vacancy-detail requests: 3;
- exact main/subunit organisation-number matches: **0**;
- companies with exact active job: **0/20**;
- logical requests: 54;
- third-party API cost: $0;
- BRREG subunit lookup errors: 0.

Even if later cohorts produced jobs, production already covers the local `workforce_jobs` category through `workforce_snapshot` on roughly 99% of fresh companies. NAV therefore has weak incremental scoring leverage and weak measured random-company reach.

## Final source landscape

| Candidate | Rights / access | Exact-entity path | Expected random-company reach | Fit to an unsolved proxy field | Decision |
|---|---|---|---|---|---|
| Patentstyret open data | Strong: NLOD 2.0; official API; free data; API subscription/key required | Strong where Norwegian rights are linked by organisation number; dedicated `IprCasesByCompany` endpoint | Potentially meaningful for IP-owning firms but not demonstrated as broad across random companies | Weak: IP filings are legitimate company activity but are not reviews, posts, mentions, or engagement metrics in the current model | **DEFER product intelligence** |
| BRREG Støtteregisteret | Strong: BRREG open data under NLOD; full dataset downloads and org-number search | Strong: recipient organisation number is explicit | Potentially broad, but support-reporting rules mean not all companies/awards appear | Weak: useful funding intelligence, but same BRREG platform and not an honest ratings/buzz/sentiment signal | **DEFER product intelligence** |
| Doffin procurement announcements | Strong: public CSV with CC BY 4.0 distribution; no registered API | Potentially strong where supplier/customer organisation numbers are present | Likely sector-biased and uncertain for a random company population | Weak: procurement activity is not a review or social/public engagement metric under current semantics | **DEFER** |
| OpenStreetMap place data | Strong open-data basis (ODbL), attribution/share-alike obligations | Strong only when `ref:NO:orgnr` or equivalent exact reference exists | **Very low for strict exact-org matching**; Norwegian community only recently normalized a small number of org-number tags | Strong semantic fit to `place_summary`, but exact coverage is too sparse; public Nominatim also discourages systematic bulk production lookup | **REJECT as production foundation** |
| Official YouTube Data API | Official API; quota/key operational dependency | Strong only after exact channel identity is independently established | Historical company-declared YouTube reach in the audited 1,000 was only 1 company | Strong fit to profile metrics/buzz if a channel exists | **DEFER / too sparse** |
| Company-owned dated activity pages | Clean company-owned evidence once a site is exact | Strong through existing exact-site gate | Previous H2b experiment: only 1/300 companies | Strong fit to fresh activity, but measured reach is too low | **REJECT unchanged design** |
| Company-owned careers/jobs | Clean company-owned evidence once a site is exact | Strong through exact-site gate | Previous H2f structured-job screen produced no useful net-new coverage | Jobs duplicate already-saturated workforce/jobs bucket | **REJECT unchanged design** |
| Google Places / commercial review APIs | Official but metered/commercial | Potentially strong | Potentially broad | Strong ratings/reviews fit | **BLOCKED by $0 production policy** |
| Public-platform scraping (Google reviews, LinkedIn, Glassdoor, etc.) | Rights/reproducibility unresolved or adverse | Variable | Potentially broad | Strong theoretical fit | **BLOCKED / rejected foundation** |
| Sentiment model | Model itself is possible | Depends entirely on independent source evidence | Not meaningful without broad qualified source text | Direct sentiment fit, but qualification requires real independent evidence and labelled evaluation | **DEFER until evidence exists** |

## Source facts checked on 2026-09-17

### Patentstyret

Patentstyret's developer portal describes open patent/trademark/design data under NLOD 2.0. It notes that many Norwegian business-linked rights can be uniquely identified by national organisation number and recommends `/register/v1/IprCasesByCompany` for an actor's portfolio.

References:

- <https://developer.patentstyret.no/>
- <https://developer.patentstyret.no/docs-open-data>

### BRREG Støtteregisteret

BRREG's open-data catalogue states that its open datasets are free of charge and follow NLOD. Støtteregisteret supports searches using a recipient organisation number and offers full CSV/JSON dataset downloads with dated allocations.

References:

- <https://www.brreg.no/en/use-of-data-from-the-bronnoysund-register-centre/open-data/>
- <https://www.brreg.no/en/use-of-data-from-the-bronnoysund-register-centre/datasets-and-api/>
- <https://stotte.brreg.no/>

### Doffin

Data.norge lists the Doffin procurement-announcement dataset as public open data with a CSV distribution under CC BY 4.0 and no registered API.

Reference:

- <https://data.norge.no/en/datasets/a77b0408-85f9-3e12-8a66-8d500b492e9d/kunngjoringer-av-offentlig-anskaffelser>

### OpenStreetMap

`ref:NO:orgnr` is the Norwegian organisation-number reference key. The Norwegian OSM community discussion in April 2026 shows that this exact reference was only beginning to be normalized across a small set of existing objects. Public Nominatim permits at most one request per second, discourages periodic/bulk geocoding, and requires caching/attribution; regular systematic lookup is therefore a poor evaluator dependency even apart from sparse exact-org coverage.

References:

- <https://wiki.openstreetmap.org/wiki/Key:ref:NO:orgnr>
- <https://community.openstreetmap.org/t/hvilken-referanse-tag-bor-brukes-for-organisasjonsnummer/140458>
- <https://operations.osmfoundation.org/policies/nominatim/>

## Stop rule

Do not start another full connector cycle merely because an accessible dataset exists.

Reopen source exploration only if a candidate can plausibly satisfy **all** of the following before production coding:

1. It improves a genuinely unsolved Builderr-relevant information family, rather than duplicating workforce or adding an interesting but locally unscored registry fact.
2. Rights permit the intended production acquisition and publication path.
3. Exact legal entity attribution can be proved without lowering current identity standards.
4. Third-party API spend remains $0 under the current project policy.
5. A cheap pre-screen suggests at least roughly 5–10% random-company reach, or there is equally strong evidence of material hidden-evaluator value.
6. Request/runtime cost fits the 100-company evaluator budget with headroom.
7. The source can support deterministic refresh/evidence semantics.

If these conditions are not met, the default decision is **do not build it**.

## Finalization plan

### Phase F1 — reconcile the production record

Update the stale permanent docs so they describe current `main` rather than the pre-H2g release candidate:

- mark H2g as promoted and its final integrated qualification passed;
- mark H2h dropped and H2i shelved;
- update `CONNECTOR_STATUS.md`, `REQUIREMENTS_MATRIX.md`, `SCORING_READINESS_AUDIT.md`, and H2g decision language;
- preserve the explicit statement that Builderr's hidden coverage/recall gates are not locally proven.

### Phase F2 — freeze a new final release corpus

The previous 1,000-company audit predates H2g and its heldout 200 is consumed. Create a new deterministic corpus outside all previously touched companies.

At this point the historical exclusion chain reaches 5,800 prior companies before H2h. H2h then touched 100 new companies; H2i reused 20 of those and adds no new companies. Therefore a wholly untouched new release corpus should exclude **5,900 unique previously touched companies**.

Freeze:

- a new deterministic 1,000-company manifest;
- its SHA-256;
- a predeclared split if a separate heldout portion is retained;
- the exact production git SHA.

Do not use the new final heldout subset for tuning.

### Phase F3 — run the current production stack at release scale

Because the official resource limits are normalized around 100-company evaluation runs, execute the 1,000 final corpus in reproducible 100-company chunks rather than treating a single monolithic OCR run as the evaluator shape.

For every chunk record:

- exactly 100 terminal objects;
- output-contract validation;
- request count / conservative challenge charge;
- third-party API cost;
- runtime;
- H2e/H2g workforce coverage;
- website/social/contact reach;
- source/OCR abstentions/errors;
- evidence/claim consistency.

Then aggregate the ten chunks without altering company results.

### Phase F4 — synthesis and UX hardening

Do not invent missing external signals. Improve the existing research layer and prototype around the data that is actually qualified:

- concise company overview;
- financial period/context;
- workforce evidence and reporting-period wording;
- verified website/social/contact where available;
- explicit evidence links and freshness;
- visible unknown/unavailable states;
- change history;
- clear provenance for every decision-useful statement.

Improve the current prototype rather than starting a frontend rewrite.

### Phase F5 — submission package

Package and verify:

- final repository SHA;
- frozen 1,000-company manifest and digest;
- evaluator command/setup instructions;
- Tesseract/Poppler prerequisites and graceful-abstention behavior;
- source/licence/acquisition register;
- model/API declaration;
- measured requests/runtime/$0 third-party spend;
- final machine-readable run reports;
- final release audit and known limitations.

## Final claim boundary

This audit says that **continuing broad zero-cost source hunting is no longer the best engineering use of time under the current evidence**. It does not assert that the hidden Builderr coverage threshold is passed, that no better source exists anywhere, or that the local proxy equals the official scoring system.

If the official challenge rules, cost policy, a source's licence, or new measured source coverage changes, this decision can be revisited with new evidence.