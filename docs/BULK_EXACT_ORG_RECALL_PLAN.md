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

Status: **DROP FOR PRODUCTION WEBSITE DISCOVERY — CANDIDATE REACH DID NOT SURVIVE EXACT VERIFICATION**.

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

### R2.4 — exact website-verification transfer

The apparent 47-company net-new candidate upper bound was tested with the existing
Signalpost exact-company website verifier before any production consideration.

Successful verification-yield run: **37412285620**.

Frozen privacy-minimized artifact:

- artifact ID: **11389623173**;
- ZIP SHA-256: `100c8bca27ead0b2e75caf899c29a6b1fcd0f80af35572ead9a6e0bb7469529d`.

Measured result:

- net-new Peppol website candidates attempted: **47**;
- logical site requests spent on independent verification: **87**;
- exact publishable websites recovered: **1/47 = 2.13%**;
- current website coverage: **107/1000**;
- post-verification website coverage: **108/1000**;
- net-new verified-site reach: **1/1000 = 0.1%**;
- candidates with explicit wrong-organisation-number evidence: **10**;
- transient fetch outcomes included blocked/source-error candidates;
- raw candidate URLs and page content were not persisted by the frozen result.

Decision: **DROP Peppol for the production website-discovery path**. The exact-org
participant join is broad, but Directory website values do not transfer reliably to the
target legal entity under Signalpost's precision boundary. This is a measured verification
failure, not merely a rights deferral. Do not spend more source or site requests on this
candidate family unchanged.

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

## R6 — zero-request retained website recovery

Status: **JSON-LD CONTACT RECOVERY QUALIFIED ON CONSUMED 1000 / RESEARCH-BRANCH PROMOTION CANDIDATE**.

The first aggregate audit over the frozen 1000 output showed:

- verified websites: **107/1000**;
- current external contact-email companies: **53/1000**;
- verified websites without an external contact-email claim: **54**;
- structured Organization.description recovery: **0** safe candidates.

Archived final-release run **35246833190** still retained the ten chunk-level
`profiles.jsonl` files, allowing a zero-provider-request replay over the original exact-site
snapshots.

A loose retained-evidence audit found 8 additional same-domain email candidates. We then
tightened the rule so that a schema.org Organization node is accepted only when that
individual node:

1. explicitly carries the exact target organisation number; or
2. has no conflicting structured organisation number and its own legal/name field contains
   every normalized target legal-name token.

The email must be in an explicit schema field named `email` (including nested
ContactPoint.email), must match the verified website registered domain, and still requires
the already-passed exact website identity gate. Free-text JSON-LD and cross-domain contacts
are ignored.

Implementation:

- `src/norway_company_agent/company_site_contact.py` — research-branch extension only;
- expanded `tests/test_company_site_contact.py`;
- `scripts/replay_jsonld_contact_recovery.py`;
- `.github/workflows/research-jsonld-contact-recovery-replay.yml`.

Replay run: **37418125650**.

Frozen replay artifact:

- artifact ID: **11391073124**;
- ZIP SHA-256: `4baee50f604547217da8a6f4a997b34fe3ce90833dbae02ca4a4b93ba94920e1`.

Measured replay result:

- before contact companies: **53/1000**;
- after contact companies: **58/1000**;
- before contact claims: **57**;
- after contact claims: **64**;
- **7 net-new contact-email companies / 7 net-new claims**;
- zero network requests;
- zero third-party cost;
- zero lost existing contacts;
- zero observation-validation errors;
- zero output-contract errors;
- zero canonical-projection errors;
- zero synthesis errors;
- all seven recovered structured nodes used the target legal-name match gate;
- raw email addresses were not retained in the research audit.

The seven privacy-minimized audit rows were exact-site records for LEAN TECH AS, ENTALPY AS,
TØLLEFSENHJØRNET AS, KINGS BAY AS, SLITASJETEKNIKK AS, TRUCKTECH AS and PROZO NORGE AS.
Every recovered email domain matched the already-verified website registered domain.

Full branch regression run **37418275911** passed after the contact change.

Decision: this is a **small but legitimate zero-request promotion candidate** because it adds
0.5 percentage points of company-level contact coverage without weakening website identity
or consuming request budget. Keep it isolated until production-line ownership is explicitly
coordinated; do not merge from this research chat into work happening elsewhere.

Description recovery was separately checked and remains **DROP**: the existing website
extractor already retains meta/OG description, and the archived profiles contained **0**
additional safe schema.org Organization.description candidates among the missing cases.
Do not synthesize company descriptions from arbitrary homepage prose.

## R7 — combined zero-network exact-site enrichment gate

Status: **PROMOTION GATE PASS / STRONGEST ZERO-REQUEST RESEARCH CANDIDATE / KEEP ISOLATED**.

The independently qualified JSON-LD contact recovery and homepage social recovery were
replayed together against the same archived final-release 1000 to verify that they compose
without silently replacing unrelated facts.

Implementation:

- `scripts/gate_zero_network_enrichment_bundle.py`;
- `tests/test_zero_network_enrichment_bundle.py`;
- `.github/workflows/research-zero-network-enrichment-bundle.yml`.

Successful workflow: **37421708928**.

Frozen aggregate artifact:

- artifact ID: **11393242341**;
- ZIP SHA-256: `287a3a8d31133f12f5afd1293f3ad397edb96e4e340f41a0b3be4e3fd22524f1`.

Focused regression gate: **41 tests passed**.

Measured frozen-1000 result:

- baseline contact companies: **53**; challenger: **58**;
- baseline contact claims: **57**; challenger: **64**;
- **+5 newly covered contact companies / +7 contact claims**;
- baseline social companies: **48**; challenger: **58**;
- baseline social-handle claims: **82**; challenger: **99**;
- **+10 newly covered social companies / +17 social-handle claims**;
- baseline companies with contact or social: **75**;
- challenger companies with contact or social: **80**;
- union lift: **+5 companies / +0.5 percentage points**;
- canonical `hiring_and_public_activity` data-area lift: **+10 companies**;
- logical requests added: **0**;
- conservative request charge added: **0**;
- third-party API cost added: **$0**;
- search API requests added: **0**;
- lost existing contact companies: **0**;
- lost existing social companies: **0**;
- non-managed claim mutations: **0**;
- observation-validation errors: **0**;
- output-contract errors: **0**;
- canonical-projection errors: **0**;
- synthesis errors: **0**.

Production-overlap correction: the zero-network **social** recovery is already present on
current `main`. Therefore the combined run is a valuable compatibility/composition proof, but
the only genuinely new production candidate in this bundle is the stricter JSON-LD contact
recovery: **+5 newly covered contact companies / +7 contact claims at zero requests**.

Decision: preserve the JSON-LD contact extension as the current genuinely new low-risk
promotion candidate. Do not double-count the +10 social-company lift as new production value,
and do not merge anything to `main` from this isolated chat without explicit coordination.

## R8 — supplier-payment ledger metadata investigation

Status: **METADATA SCREENED / CURRENT BROAD PUBLIC SOURCE NOT YET FOUND**.

A supplier-payment route was investigated because municipal accounts-payable exports can,
in principle, combine exact supplier organisation numbers with dated/value-bearing commercial
activity.

Implementation:

- `scripts/resolve_data_norge_supplier_sources.py`;
- `tests/test_resolve_data_norge_supplier_sources.py`;
- `.github/workflows/research-data-norge-supplier-resolver.yml`.

Latest frozen metadata run: **37419104906**.

- metadata artifact: **11392570608**;
- artifact ZIP SHA-256: `bea1a565aab4428470f8eb937c7755adcb0c6f50d15f6790eac91c7d9e5d4dad`;
- 24 frozen broad-catalogue candidates were resolved;
- the apparent 24/24 exact-org/open-license supplier score is a metadata-classification
  overcount: most rows are agricultural subsidy/payment datasets, not general supplier ledgers;
- the only genuine broad supplier-ledger candidate resolved was **Leverandørregnskap Stavanger
  kommune**, NLOD/CSV, describing payments to companies with organisation numbers;
- that dataset is explicitly marked ended/on hold by the live Stavanger open-data portal and
  is not a current 2025/2026 activity source;
- live targeted Data.norge searches for `leverandørregnskap`, `leverandørreskontro`,
  supplier payments and invoices returned **0** discoverable current candidates.

External current-source checking found no comparable openly downloadable 2025/2026 ledgers
from the major municipalities tested. A separate commercial/research supplier database is
known to aggregate municipal accounts-payable data at much broader scale, but that is not a
$0 open-data production source and is outside this track.

Decision: **do not download or productionize the stale Stavanger ledger**. Revisit supplier
payments only if a current openly licensed bulk source or a reproducible multi-municipality
export becomes available.

## Current direction

1. Preserve the JSON-LD contact recovery as the current zero-request promotion candidate; do not merge it into production from this isolated research track.
2. Peppol website discovery is now a measured **DROP**: 47 net-new candidates produced only 1 independently verified website after 87 logical site requests.
3. Treat the rights-clean official-activity union as measured and shelved for the immediate 65+/70+ objective; another collection of similarly narrow activity registries is unlikely to close the recall gap.
4. Continue only with either (a) a genuinely broad rights-safe exact-org source, or (b) zero-extra-request facts already retained by production that can be surfaced without semantic relabeling.
5. Workforce snapshots remain size/workforce evidence, **not active hiring**. BRREG registry changes remain official registry events, **not company-authored news**.
6. Do not reopen Nkom unchanged, OSM exact-org website discovery, the current Finanstilsynet pagination strategy, Patentstyret broad per-company lookup, or Peppol website nomination without a materially different retrieval signal.
7. Keep SGregister/DSB and any source with unresolved persistent-reuse rights out of production proposals regardless of raw coverage.
8. Keep this entire track isolated from production and fresh evaluator cohorts until a candidate demonstrates materially better consumed-cohort value than the already-measured paths.
