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

Patentstyret's official Open Data documentation exposes a company-portfolio endpoint (`/register/v1/IprCasesByCompany`) and states that many Norwegian rights can be linked to businesses by national organisation number. It also states that the dataset is free to use subject to source/copyright guidance and NLOD 2.0.

The same official developer material requires a valid API subscription key. Account creation and product subscription are self-service. We therefore now treat access semantics as verified, but the exact authenticated operation/query shape must be copied from the official portal rather than guessed from the endpoint name.

Status: **promising; screen tooling ready; blocked only on API subscription key + exact operation URL**.

### Doffin — potentially useful, access verified but role-sensitive

Doffin's official help describes its distribution chain as including an API and Doffindata. The official DFØ API developer portal exposes a `Public API` for searching for and downloading published notices and requires sign-up/subscription access.

That resolves the earlier access uncertainty. It does **not** resolve supplier attribution: an organisation number in a notice can identify the buyer, supplier, participant or another organisation. The first keyed screen therefore measures exact-org response reach only; any useful matches must then be schema-audited for supplier/award roles before productionization.

Status: **candidate; screen tooling ready; blocked on API subscription key + exact authenticated operation URL**.

### Credential-gated comparison tooling

The branch now includes:

- `scripts/screen_keyed_exact_org_source.py` — generic exact-org API reach screen;
- `tests/test_v4_keyed_exact_org_source.py` — compact/grouped identifier, numeric-boundary, HTTPS and secret-header regressions;
- `.github/workflows/v4-keyed-source-screen.yml` — manual Patentstyret/Doffin screen using the same fixed 20-company comparison cohort;
- `docs/V4_KEYED_SOURCE_ACCESS.md` — verified access facts and dispatch checklist.

The API key is passed only through the configured request header, never embedded in the URL or persisted in reports. The workflow uses `PATENTSTYRET_API_KEY` or `DOFFIN_API_KEY` GitHub Actions secrets.

### NAV Job Vacancy Feed — deprioritized

NAV's official feed is free to use with a signed JWT and includes employer organisation numbers, but its documentation says filtering by employer/company must be performed client-side. The project already ran the expensive feed-wide architecture previously: 30,000 feed entries for 20 target companies produced zero exact active jobs. Repeating that architecture would violate the screen-first rule.

Status: **deprioritized unless a materially more bounded lookup becomes available**.

## Milestone 2 decision after current screens

1. **Støtteregisteret:** DROP for broad random-company enrichment (0/20 exact-org reach).
2. **Patentstyret:** READY TO SCREEN once `PATENTSTYRET_API_KEY` and the exact official operation URL are configured.
3. **Doffin:** READY TO SCREEN once `DOFFIN_API_KEY` and the exact official public-search operation URL are configured; schema role validation remains mandatory after any match.
4. **NAV jobs:** DEPRIORITIZED under the current feed-wide architecture.

Because the remaining high-value official sources are now externally credential-gated rather than engineering-blocked, we should not stall the project or weaken evidence rules. The next active engineering milestone can proceed in parallel on **ML request ranking**, while keyed source screens remain ready to dispatch as soon as official subscriptions are available.

The core rule remains: failed screens are useful results. We document and drop them instead of adding connectors for feature count.
