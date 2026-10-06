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

## R9 — eInnsyn exact-org recent public-record screen

Status: **DROP FOR BROAD PRODUCTION RECALL / EXACTNESS GOOD, ECONOMICS POOR**.

The official eInnsyn API specification and frontend were inspected first. Although the
OpenAPI service declares API-key authentication globally, the production frontend also has a
public no-credential API client and anonymous `GET /search` works in practice.

Research contract probes established:

- exact quoted 9-digit organisation-number searches can return public `Journalpost` rows;
- returned rows expose `publisertDato`, `journaldato`, `dokumentetsDato` and public titles;
- in the qualified example, the exact organisation number was literally present in
  `offentligTittel`;
- `publisertDatoFrom` correctly restricts to the recent window;
- a naive two-org `OR` query did not batch, so the useful route is effectively per-company;
- production data-reuse rights remain unresolved, so publication stayed disabled.

Implementation:

- `scripts/screen_einnsyn_exact_org_reach.py`;
- `tests/test_screen_einnsyn_exact_org_reach.py`;
- `.github/workflows/research-einnsyn-exact-org-reach.yml` (now manual-only).

Successful consumed-100 run: **37423413569**.

Frozen aggregate artifact:

- artifact ID: **11394310022**;
- ZIP SHA-256: `cf2ea9bdf24083dc3eab5ebf0c0354ae4a0a36f1e1e5936d55929e985f1e7adf`.

Strict identity rule:

> a hit counts only when the request is the exact quoted target org number and the returned
> public `offentligTittel` itself contains that exact 9-digit value with digit boundaries.

Measured deterministic consumed-100 result:

- requests: **100**;
- HTTP/source errors: **0**;
- empty results: **93**;
- query results with a public date: **7**;
- query hits whose public title did not contain the exact org number: **5**;
- **exact recent public-record companies: 2/100 = 2%**;
- exact hits/request: **0.02**.

Decision: **DROP for broad production use**. The identity evidence is unusually strong for the
two accepted companies, but 100 per-company requests for two recent exact hits is far below the
yield needed to displace existing request paths under Signalpost's full request theorem.
Reconsider only for targeted/on-demand official-record research or if eInnsyn exposes a
batch/bulk exact-org retrieval mechanism later.

## R10 — zero-request structured company-site contact recovery

Status: **QUALIFIED ON FROZEN CONSUMED 1000 / PROMOTION CANDIDATE / KEEP ISOLATED**.

After the JSON-LD email recovery qualified, the retained exact-site snapshots were audited for
another explicit structured contact field: schema.org `telephone`.

The recovery boundary is deliberately narrow:

- the website must already be exact-verified and publishable;
- the telephone must come from an individually identified schema.org Organization node;
- that node must identify the exact target either by exact structured organisation number or,
  with no conflicting structured organisation number, by all normalized target legal-name tokens;
- the phone value must be in an explicit structured `telephone` field;
- only conservative Norwegian numbers that normalize to `+47` plus eight digits are accepted;
- no free-text phone mining and no cross-entity inheritance;
- the source page/hash/retrieval time remain the already-retained exact company-site evidence;
- no network request is added.

Implementation on this research branch:

- `src/norway_company_agent/company_site_phone.py`;
- phone observation/claim projection in `src/norway_company_agent/external_contract.py`;
- canonical `contact_phone -> website.contact_phone` projection;
- `scripts/replay_jsonld_phone_recovery.py`;
- focused phone/contract/canonical regression tests.

Full frozen-1000 replay:

- workflow run: **37437599303**;
- artifact ID: **11399737205**;
- artifact ZIP SHA-256: `00dc992cde558f92c9f6742517a1b720c5374362c1d4e35ce31cf3b8db071d6f`;
- focused regressions: **14 passed**;
- before external contact-phone companies: **0**;
- after: **19/1000**;
- **+19 contact-phone companies / +19 claims / +1.9 percentage points**;
- exact structured-org-number identity on 4 recovered nodes;
- remaining accepted nodes passed the no-conflicting-org + legal-name-token node gate;
- network requests added: **0**;
- third-party API cost added: **$0**;
- lost existing organisations: **0**;
- observation errors: **0**;
- output-contract errors: **0**;
- canonical errors: **0**;
- synthesis errors: **0**;
- raw phone numbers are excluded from the research report/audit; only fingerprints are retained there.

Full branch regression:

- workflow run: **37437717684**;
- result: **602 tests passed + 5 subtests passed**.

Email + phone were then replayed as one contact bundle to avoid double-counting company coverage:

- workflow run: **37437925331**;
- artifact ID: **11399841888**;
- artifact ZIP SHA-256: `a68ab8704cb5934daa26c7c1b67968f6eee370a879f539430316b9bc9911acf6`;
- focused tests: **31 passed**;
- baseline companies with any external contact: **53**;
- challenger: **60**;
- **net-new any-contact companies: +7/1000 = +0.7 percentage points**;
- email: +5 companies / +7 claims;
- phone: +19 companies / +19 claims;
- new-email/new-phone overlap: 4 companies;
- non-managed claim mutations: **0**;
- observation/contract/canonical/synthesis errors: **0**;
- logical requests added: **0**;
- third-party API cost added: **$0**;
- promotion gate: **PASS**.

Decision: structured email and phone recovery are legitimate zero-request enrichment candidates.
They are not the primary path to 65+ because Builderr's explicit recall gaps are website/social/
hiring/dated-news coverage, but the phone path is safe enough to preserve for later coordinated
production promotion. Do not merge it from this isolated research track.

## R11 — BRREG public-announcement exact-org activity screen

Status: **EXACT / REQUEST ECONOMICS TOO WEAK / RIGHTS MAPPING UNRESOLVED / SHELVE**.

BRREG's public Foretaksregisteret announcement search was tested because it can expose dated
official legal/company events with exact organisation numbers. These events are kept strictly
typed as registry/legal events and are never relabelled as company-authored news.

Identity boundary:

- exact 9-digit organisation number in the BRREG announcement row only;
- rows carrying multiple organisation numbers are rejected;
- dates are inherited only from the BRREG date header in the same response;
- no company-name identity matching.

Measured source behavior:

- one day (01.10.2026): **1,462** announcement org rows;
- two-day range (30.09–01.10): **3,670** org rows and **9/1000** consumed target companies;
- three days or more in the tested high-volume window returns BRREG's own limit message:
  **"Antall treff overstiger 5000. Vennligst begrens søket."**
- therefore a safe broad shared-query span is at most roughly two days in this window.

The frozen 30-day single-day screen:

- workflow run: **37425714146**;
- artifact ID: **11394727301**;
- 30 days / 30 requests;
- 26,356 parsed announcement rows;
- **33/1000** exact consumed target companies;
- 40 target announcement rows;
- current frozen production registry-change overlap: 0.

A zero-network comparator then simulated the same 30 days as fifteen two-day bins:

- workflow run: **37438482035**;
- artifact ID: **11400366029**;
- artifact ZIP SHA-256: `78d099e8737ea6202a2602c6a715fd1555b74883a2df741b66096be46bd0686e`;
- source requests required: **15**;
- unique target companies: **33**;
- **2.2 unique companies per request**;
- maximum target companies in one two-day request: **9**;
- minimum: **0**;
- requests with zero target hits: **6/15**.

Rights boundary remains unresolved for persistent reuse of the legacy public HTML announcement
surface. BRREG's general open datasets use NLOD, but this research did not establish that the
specific HTML announcement-search output is an NLOD distribution.

Decision: **SHELVE for broad production**. Exactness is useful, but 2.2 unique companies/request
is not strong enough to displace the current score-critical request paths, and the rights mapping
is still incomplete. Revisit only if BRREG exposes a bulk/open distribution of announcements or
a materially more efficient query surface.

## Current direction

1. Optimize explicitly for Builderr's measured external recall gaps: **company website, social profile, hiring signal and dated news**. The latest official 49.99 evaluator feedback reported 0% dated news, 0% hiring and 0% social on the submitted revision.
2. Preserve structured JSON-LD email and phone recovery as qualified **zero-request** promotion candidates, but do not confuse contact enrichment with the main recall path and do not merge from this isolated branch.
3. Peppol website discovery remains a measured **DROP**: 47 net-new candidates produced only 1 independently verified website after 87 logical site requests.
4. BRREG public announcements are now measured **SHELVE**: exact but about 2.2 unique companies/request over a 30-day equivalent window, with an explicit >5000-result cap beyond roughly two days and unresolved HTML reuse mapping.
5. The rights-clean official-activity union remains shelved for the immediate 65+/70+ objective; another set of similarly narrow official activity registries is unlikely to close the recall gap.
6. Prefer the next experiment to be a **zero-network evaluator-family recovery** from already-retained exact-site evidence, especially a defensible hiring/careers or dated-news fact, before adding another live source.
7. Workforce snapshots remain size/workforce evidence, **not active hiring**. BRREG registry changes remain official registry events, **not company-authored news**.
8. Do not reopen Nkom unchanged, OSM exact-org website discovery, the current Finanstilsynet pagination strategy, Patentstyret broad per-company lookup, Peppol website nomination, eInnsyn broad per-company lookup, or BRREG announcements unchanged.
9. Keep SGregister/DSB and any source with unresolved persistent-reuse rights out of production proposals regardless of raw coverage.
10. Keep this entire track isolated from production and fresh evaluator cohorts until a candidate demonstrates materially better consumed-cohort value than the already-measured paths.


## R12 — BRREG historical-name deterministic .no discovery

Status: **MEASURED / DROP**.

Why tested:

- BRREG open-data v2 added `historiskeNavn` to live entity/search responses in June 2026;
- production already performs one exact live BRREG entity request per company, so retaining this field would add **0 incremental BRREG requests**;
- former legal names can plausibly survive in legacy company domains after a rename.

Official source semantics:

- exact organisation number remains the legal-entity anchor;
- historical name is candidate-generation evidence only;
- BRREG open data is NLOD 2.0;
- the existing Signalpost website identity gate and registry-risk guard remain unchanged.

### R12.1 bulk-field probe

Workflow run: **37442303037**  
Artifact: **11402290813**

Current BRREG bulk CSV:

- compressed bytes: **154,858,476**;
- rows scanned: **1,176,746**;
- consumed-1000 target rows present: **998**;
- header count: **90**;
- historical-name columns: **0**;
- internet-like columns: only **`hjemmeside`**;
- target companies with non-empty internet field: **116**.

Conclusion: `historiskeNavn` is available in the live/search API but not in the current bulk CSV, and there is no second hidden bulk internet-address field to recover.

### R12.2 live exact-org candidate reach

Workflow run: **37442619950**  
Artifact: **11401443977**

Deterministic consumed 100:

- baseline verified websites: **13/100**;
- unresolved websites: **87/100**;
- live BRREG entity calls: **100/100 HTTP 200**;
- unresolved companies with historical names: **25/87**;
- unresolved companies with distinct historical-name `.no` candidates: **23/87 = 26.4%**;
- distinct candidate domains: **50**;
- latest historical-name end within 1 year: **1 company**;
- within 3 years: **6 companies**;
- within 5 years: **12 companies**;
- within 10 years: **16 companies**;
- incremental production BRREG requests if the field were retained from the already-paid live entity response: **0**.

This candidate availability was high enough to justify one bounded transfer test.

### R12.3 transfer / DNS gate

Most-recent compact candidate transfer run: **37443128589**, artifact **11401818668**.

- candidate companies: **23**;
- live entity responses: **23/23 HTTP 200**;
- site logical requests: **0**;
- all **23/23** most-recent compact candidates failed the safe public-host/DNS preflight and were marked blocked before HTTP;
- identity publications: **0**.

All-candidate DNS/public-host preflight: **37443309574**, artifact **11402590304**.

- candidate domains: **50**;
- safe public-host domains: **1**;
- safe public-host companies: **1**;
- unresolved/blocked domains: **49**;
- HTTP requests: **0**.

Final sole-survivor verification: **37443436371**, artifact **11402800206**.

- survivor candidates: **1**;
- BRREG entity HTTP: **200**;
- site logical requests: **2**;
- site status: **blocked**;
- current-entity identity publishable: **false**;
- registry-guard publishable: **false**;
- verified websites: **0**.

Decision: **DROP historical-name deterministic `.no` website discovery**. The official name-history signal is exact and free, but almost every derived legacy domain fails even DNS/public-host viability, and the sole survivor failed page verification. Do not add this path to production or spend additional candidate slots on it unchanged.

All R12 live workflows are frozen to manual-only after the result.

## Next direction after R12

Website discovery remains the root external-recall bottleneck, but another guessed-domain family is not justified. The next screens should prioritize **collected-but-not-emitted fields from source responses already paid for in production**. Highest priority: inspect the current Støtteregisteret recipient/support payload for website/domain/contact fields that are currently discarded. If such fields exist, measure exact-org candidate reach and net-new website overlap before any page fetch. This preserves the zero-additional-source-request strategy.
