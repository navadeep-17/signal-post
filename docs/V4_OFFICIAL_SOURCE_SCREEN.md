# Signalpost V4 — Official Public-Activity Source Screen

Date: 2026-10-01

Branch: `feature/v4-official-activity-sources`

Milestone 1 (annual-report company descriptions) is merged to `main`. V4 starts Milestone 2 by screening official public-activity sources before implementing another production connector.

## Screening rule

A source is promoted only when a small fresh cohort shows enough exact-entity reach to justify engineering and request-budget cost.

For every screen:

1. use companies that were not used for prior tuning/qualification;
2. prefer exact organisation-number attribution over name matching;
3. measure reach before building a connector;
4. keep screen-only code separate from production publication;
5. reject sources whose random-company reach is too weak for the expected complexity/cost;
6. preserve the existing external-observation evidence contract if a source is promoted.

## Fresh V4 screen cohort

The first V4 screen uses a deterministic 20-company cohort selected with seed `20261006` after excluding every previously touched company through the final V3 confirmation cohort.

Selection evidence:

- universe rows: **411,160**;
- previously excluded/touched companies: **7,200**;
- eligible remaining companies: **403,960**;
- screen companies: **20**;
- unique organisations: **20**;
- overlap with exclusions: **0**;
- cohort SHA-256: `fdf402093fa87e65103c9e5b9e8d26db15b0027da4a4504deb7f575117afa5bb`.

The selection manifest and screen evidence are archived by GitHub Actions run `36873654739` in artifact `v4-official-source-screen`.

## Screen 1 — BRREG Støtteregisteret

### Why it was screened

Støtteregisteret is an official Brønnøysund source for state-aid/support awards. Its public lookup supports recipient organisation-number search and it exposes downloadable datasets, making exact legal-entity attribution possible in principle.

Screen source:

`https://stotte.brreg.no/nb/oppslag/stoettetildeling/totalbestand/json`

### Method

The screen deliberately does **not** implement a production parser. It downloads the official complete JSON dataset once, then checks only whether each target's exact nine-digit organisation number occurs in the official payload (allowing compact and 3-3-3 formatting, with digit boundaries).

This is a lower-bound feasibility test: a source cannot provide an exact-org award for a target if the target organisation number never occurs in the dataset.

### Measured result

- official payload size: **480,788,033 bytes**;
- payload SHA-256: `869335d6829152f6b6f5e8225c8ed192148a42bf4aeb3487ab7b9299bc9232d1`;
- companies screened: **20**;
- companies whose exact organisation number occurs: **0**;
- exact identifier occurrences: **0**;
- measured random-company reach: **0/20 = 0%**.

The workflow, selector reconstruction, screen tests, source download and evidence upload all completed successfully. Baseline CI on the V4 branch also passed.

### Decision

**Do not implement Støtteregisteret as a production Signalpost connector for the current random-company objective.**

The source can be valuable for companies that receive public support, but this fresh random-company screen provides no evidence that a ~481 MB bulk download will improve broad recall enough to justify its runtime/data-transfer cost. It remains a possible targeted source later if the product adds source-specific/on-demand research.

No production facts are emitted from this screen.

## Remaining source triage

### Patentstyret — high semantic value, access-gated

Patentstyret's official Open Data documentation exposes a company-portfolio endpoint (`/register/v1/IprCasesByCompany`) and states that many Norwegian rights can be linked to businesses by national organisation number. This is exactly the kind of deterministic join Signalpost wants for trademark/patent/design activity.

However, the official developer documentation requires a valid API subscription key. Subscription is self-service, but a key is still required before we can run a reproducible exact-org reach screen. Do not build the production connector before that screen.

Status: **promising but blocked on API subscription key for measurement**.

### Doffin — potentially useful, API access must be verified before implementation

Doffin notices are public and individual notices contain structured organisation sections. Result/award notices can provide dated procurement activity and supplier information when published.

The public-API route is preferable to scraping the search UI. Current external implementations indicate the API is Azure APIM-backed and requires a subscription key; official Doffin help exposes a public-API access FAQ but the dynamic answer is not available to our static crawler. Treat API access as unresolved until verified directly.

Status: **candidate, but do not implement until API access and exact supplier-org query strategy are verified**.

### NAV Job Vacancy Feed — deprioritized

NAV's official feed is free to use with a signed JWT and includes employer organisation numbers, but its documentation says filtering by employer/company must be performed client-side. The project already ran the expensive feed-wide architecture previously: 30,000 feed entries for 20 target companies produced zero exact active jobs. Repeating that architecture would violate the screen-first rule.

Status: **deprioritized unless a materially more bounded lookup becomes available**.

## Milestone 2 decision after Screen 1

Do not promote Støtteregisteret.

Next priority order:

1. **Patentstyret exact-org portfolio screen**, once a subscription key is available;
2. **Doffin exact supplier/award screen**, only after public API access is verified;
3. otherwise move engineering effort to the next highest measured-return milestone rather than forcing a low-reach connector.

The core rule remains: failed screens are useful results. We document and drop them instead of adding connectors for feature count.
