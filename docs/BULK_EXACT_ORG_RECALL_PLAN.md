# Signalpost — isolated bulk exact-org recall plan

Date: 2026-10-06
Branch: `research/bulk-exact-org-recall`
Base main SHA: `88be83e226da13ba6f7a2717c72c1d2d94cf5bec`

## Goal

Find a materially stronger recall mechanism without touching the production runner, current qualification work, or any fresh evaluator cohort.

Optimization target:

`net-new exact-company coverage / external requests`

Precision rule:

> ATTEMPT MORE -> VERIFY STRICTLY -> PUBLISH CONSERVATIVELY

## Safety boundary

- research branch only;
- no imports from research scripts into production code;
- no mutation of `run_signalpost_v8.py` or production request-accounting code;
- no fresh Phase-11/Q8 cohort;
- use only already-consumed `submission/final-release-1000.jsonl` rows for source selection;
- source-selection scripts publish no production claims;
- exact nine-digit organisation-number attribution is mandatory;
- name-only matches are never counted as exact-company hits;
- website/email outputs are candidates only until independently verified;
- no source is promoted without clear reuse rights and reproducible access;
- live research workflows are changed to manual-only after a useful result is frozen.

## Shared consumed cohort

R1/R2/R3 source screens use the same deterministic consumed 100 selected from the frozen final-release 1000 by sorting on:

`sha256("bulk-exact-org-r1-v1|" + organisation_number)`

The complete consumed 1000 is also used when a one-download bulk source makes the larger comparison essentially free.

## R1 — TED procurement winner screen

Status: **DROP FOR BROAD RANDOM-COMPANY RECALL**.

Implementation:

- `scripts/screen_ted_exact_winner_reach.py`;
- `tests/test_screen_ted_exact_winner_reach.py`;
- `.github/workflows/research-ted-exact-winner-screen.yml` (now manual-only).

Precision semantics:

- only TED `winner-identifier` establishes a company hit;
- exact 9-digit target matching only;
- multi-winner notices may count as activity but do not attribute website/email to one target;
- publication disabled.

Measured consumed-100 result:

- companies: **100**;
- shared Search API requests: **4**;
- returned notices: **0**;
- companies with exact award: **0/100**;
- companies with recent award: **0/100**;
- website candidates: **0/100**;
- email candidates: **0/100**;
- API/search execution itself succeeded and was not truncated.

Decision: do not build a TED production path for the current random-company objective. Reconsider only for targeted procurement research or if a materially different retrieval scope is justified.

## R2 — Peppol Directory bulk screen

Status: **MATERIAL WEBSITE-CANDIDATE LIFT / PRODUCTION BLOCKED ON DIRECTORY-DATA RIGHTS**.

Implementation:

- privacy-minimized parser: `scripts/screen_peppol_exact_org_reach.py`;
- aggregate coverage test: `tests/test_screen_peppol_exact_org_reach.py`;
- aggregate coverage workflow: `.github/workflows/research-peppol-aggregate-coverage.yml` (manual-only after result freeze);
- overlap comparator: `scripts/screen_peppol_website_overlap.py`;
- overlap test: `tests/test_screen_peppol_website_overlap.py`;
- overlap workflow: `.github/workflows/research-peppol-website-overlap.yml` (manual-only after result freeze).

Verified upstream format:

- gzip-compressed BusinessCard export;
- ISO-8859-1 text;
- semicolon-separated CSV;
- Norwegian exact participant scheme: `0192:<9-digit orgnr>`;
- website is an optional Business Entity field;
- current export documentation says responses should be cached for 24 hours;
- the 2026-05-18 Directory changelog states per-IP/per-file export rate limiting defaults to **3 requests per 24 hours**.

### R2.1 — aggregate exact-org coverage

Successful run: **37409836333**.

Frozen aggregate-only artifact:

- artifact ID: **11388863383**;
- ZIP SHA-256: `6dc8619ca94cf1597b8ea06c86fa64aad539da511d93d6d37fbf65a875972dcb`.

Source snapshot:

- HTTP: **200**;
- compressed bytes: **358,316,202**;
- SHA-256: `3eb4cbf888f7117e87d638c1adcebb8b6efa72442f4eccfb64a770fe1852b06a`;
- source rows: **9,016,262**;
- Norwegian `0192` rows: **388,726**;
- malformed `0192` rows: **13**.

Reach:

- deterministic consumed 100: **64/100** exact Peppol participants; **7/100** with a website candidate;
- consumed 1000: **595/1000 = 59.5%** exact Peppol participants;
- consumed 1000 website candidates: **78/1000 = 7.8%**.

Privacy/data-minimisation boundary for this screen:

- contact fields are not retained;
- raw names are not retained;
- raw websites are not retained;
- matched organisation-number lists are not retained;
- only aggregate counts are frozen.

### R2.2 — website overlap versus current production

Successful run: **37410381982**.

Frozen aggregate-only artifact:

- artifact ID: **11389135786**;
- ZIP SHA-256: `9f9fa7d7c1b644739f2bd2c30e6fdcc552286d15edcf33ec8f80bc67f1654bfd`.

Measured against the frozen current 1000-company production output:

- current verified website companies: **107/1000 = 10.7%**;
- Peppol exact participant companies: **595/1000 = 59.5%**;
- current verified websites among Peppol participants: **94**;
- Peppol website-candidate companies: **78/1000 = 7.8%**;
- Peppol website candidates already covered by current verified websites: **31**;
- **net-new Peppol website candidates: 47/1000 = 4.7%**;
- upper-bound post-candidate website companies before independent verification: **154/1000 = 15.4%**.

This is the first source in the bulk-recall track with a potentially material website-discovery lift. The 47 candidates are still only discovery candidates; none count as Signalpost websites until the existing exact-company verification boundary independently succeeds.

### R2.3 — rights decision

Technical usefulness is **proven**; production reuse is **not yet cleared**.

Official material establishes that:

- Peppol Directory is publicly searchable;
- an automated public REST API is intentionally provided;
- full XML/JSON/CSV exports are intentionally provided;
- Business Cards are published voluntarily by SMP providers;
- the Peppol Directory specification explicitly discusses reuse of the described components in scenarios unrelated to Peppol.

However, the reviewed official material does **not** state an explicit open-data licence for the live Directory dataset itself. The Apache 2.0 statement on the Directory site applies to the **software**, not automatically to directory data. The specification's CC BY-NC-ND notice applies to the specification document, not automatically to the live dataset. The current Directory privacy policy further says that any personal data in the Directory may only be used as necessary for correct/effective/secure Peppol Network operation and limits permitted recipients.

Therefore:

- do not retain or publish Peppol contact data;
- do not treat public availability or software licensing as a dataset reuse licence;
- do not promote Peppol website candidates to production until the non-personal directory-data reuse position is explicitly documented/cleared;
- if clearance is obtained, use Peppol only as candidate nomination and keep Signalpost's independent exact-company website verification unchanged.

## R3 — Data.norge source miner / registry union

Status: **MINER IMPLEMENTED; FIRST SOURCE FAMILY SCREENED; CONTINUE SOURCE DISCOVERY**.

Implementation:

- `scripts/mine_data_norge_exact_org_sources.py`;
- `tests/test_mine_data_norge_exact_org_sources.py`;
- `.github/workflows/research-data-norge-source-miner.yml` (now manual-only);
- network-free research unit gate covers TED, Peppol and Data.norge parsers.

The first broad SPARQL attempt was intentionally abandoned after the public endpoint returned HTTP 502 on a join-heavy query. The miner now uses seven bounded Data.norge Search API queries and separates PUBLIC access rights from actual reuse-license metadata.

The first successful targeted metadata screen surfaced Landbruksdirektoratet's production/agricultural subsidy datasets. The 2025 dataset has:

- public access;
- direct CSV distribution from the publisher's GitHub open-data repository;
- NLOD reuse license;
- exact organisation-number column;
- application/payment and calculated-subsidy fields.

### R3.1 — 2025 agricultural-support exact-org screen

Implementation:

- `scripts/screen_landbruksdirektoratet_support_reach.py`;
- `tests/test_screen_landbruksdirektoratet_support_reach.py`;
- `.github/workflows/research-landbruk-support-reach.yml` (now manual-only).

Measured source:

- bytes: **11,775,424**;
- SHA-256: `a09bd9180f7ed4fd2ca40818a4d17c58d9d29b216f50e321d5026ef0dd449a43`;
- rows: **36,752**;
- encoding: UTF-8-SIG;
- delimiter: `;`;
- exact identity column: `orgnr`;
- malformed organisation-number rows: **0**.

Reach:

- consumed 100: **1/100** exact company hit; **1/100** with positive subsidy cells;
- consumed 1000: **2/1000 = 0.2%** exact company hits; both have positive subsidy cells;
- external source requests: **1 shared download**.

Decision: **do not build as a standalone production source**. Keep as a possible member of a larger exact-org registry union because it is precise, current, rights-clean and nearly free in request terms, but individual reach is too niche.

## R4 — rights-clean official-activity union

Status: **MEASURED / SHELVE FOR 65+/70+ CRITICAL PATH**.

Implementation:

- `scripts/compare_official_activity_union.py`;
- `tests/test_compare_official_activity_union.py`;
- `.github/workflows/research-rights-clean-official-activity-union.yml`;
- successful workflow run: **37409025540**;
- frozen artifact: **11389007073**;
- artifact ZIP SHA-256: `52e2898b68c88d9c0702330c476343744ff7b0ff04f61062ecd3ee1e22bf9097`.

The comparison deliberately used only exact-org source families whose reuse position is sufficiently clean for this gate:

- current production Støtteregisteret as baseline;
- Doffin exact winners;
- Forskningsrådet funded projects;
- Arbeidstilsynet open registries;
- Landbruksdirektoratet 2025 support data.

The current Støtteregisteret snapshot was fetched once and matched **88/1000** consumed companies with <=365-day official support evidence.

Measured candidate union:

- candidate sources: **4**;
- candidate union exact companies: **19/1000 = 1.9%**;
- candidate union recent-activity companies: **6/1000 = 0.6%**;
- overlap with current support: **10** all / **2** recent;
- **net-new exact companies over current support: 9/1000 = 0.9%**;
- **net-new recent-activity companies over current support: 4/1000 = 0.4%**;
- post-union official-activity coverage: **97/1000** all, **92/1000** recent.

Per-source contribution versus current support:

| Source | Exact companies | Net-new all | Recent companies | Net-new recent |
|---|---:|---:|---:|---:|
| Doffin | 12 | 5 | 5 | 3 |
| Forskningsrådet | 3 funded-project companies | 2 | 1 | 1 |
| Arbeidstilsynet | 3 | 1 | 0 | 0 |
| Landbruk 2025 | 2 | 1 | 0 | 0 |

Net-new recent companies were:

- JOHANSEN MONUMENTHUGGERI AS (`835761762`);
- WAI ENVIRONMENTAL SOLUTIONS AS (`919383712`);
- TRUCKTECH AS (`980152634`);
- UNIFON AS (`987100648`).

Decision: **do not spend production request budget on this union for the 65+/70+ critical path**. The union is exact and useful, but a 0.4% net-new recent-company lift is too small relative to the current recall deficit and the already-full theoretical request ceiling. Preserve the research artifacts for later enrichment.

## R5 — Doffin exact-winner Power BI screen

Status: **TECHNICALLY PROVEN / PRECISION-CLEAN / LOW TRANSFER / RIGHTS DECLARATION STILL NEEDS FINAL MAPPING**.

The public Doffin supplier-statistics surface exposes an anonymous Power BI embed token. Research reproduced the public report contract without persisting credentials, resolved the report model/schema and queried the exact winner organisation-number field:

- report ID: `1e4ba2c1-d15e-41c3-8cba-6166c3812f1a`;
- exact identity: `winner_eu_registration_number`;
- winner legal name: `winner_eeig_official_name_nor`;
- dated evidence includes contract-conclusion, winner-decision and notice dispatch/publication dates.

Consumed-1000 result:

- **12/1000** exact winner companies;
- **5/1000** with an official date inside 365 days;
- **5/1000** net-new all versus current support;
- **3/1000** net-new recent versus current support;
- all 12 winner identities passed BRREG legal-name/historical-name audit;
- zero unresolved identity matches.

Rights note:

- the official Data.norge Doffin notice dataset is public/open and its registered CSV distribution is CC BY 4.0;
- Doffin publicly exposes the notice flow to API/Doffindata;
- the research Power BI presentation itself has not yet been explicitly documented as the same licensed distribution, so production promotion still requires a source-declaration/reuse mapping. Do not assume the Power BI transport inherits the CSV distribution licence without documenting that mapping.

Decision: retain Doffin as a possible later exact activity connector, but **do not promote it alone** for the score-critical path.

## Current direction

1. Treat the rights-clean official-activity union as measured and shelved for the immediate 65+/70+ objective; do not spend more time adding similarly narrow registries one by one.
2. Peppol is now measured: 59.5% exact participant presence but only 7.8% website-value presence. Treat it as **not a breakthrough** unless rights are explicitly cleared and net-new verified-site transfer can be shown.
3. Prioritize a genuinely new rights-safe source or a zero-extra-request reuse of data already being fetched. Prefer changes that improve website/contact/social/jobs/activity family coverage across materially more companies.
4. Do not reopen Nkom unchanged (tested export URLs returned 404), OSM exact-org website discovery (1/1000 exact hit, 0 website candidates), or the current Finanstilsynet strategy (2/1000 exact hits in the five-page sample and no recent registrations).
5. Keep SGregister/DSB and any other source with unresolved reuse rights out of the rights-clean production proposal even if raw coverage is attractive.
6. Before another external download, audit existing production requests for **zero-extra-request field recovery** (for example structured identifiers/properties already returned by sources) because the theoretical 2,000/100 request ceiling is already full.
7. Keep this entire track isolated from production and from fresh evaluator cohorts until a candidate demonstrates a material consumed-cohort lift that justifies explicit request-budget reallocation.
