# Signalpost — isolated bulk exact-org recall plan

Date: 2026-10-05
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

Status: **PARSER READY / LIVE COVERAGE SCREEN DEFERRED BY OFFICIAL EXPORT RATE LIMIT / RIGHTS STILL UNRESOLVED**.

Implementation:

- `scripts/screen_peppol_exact_org_reach.py`;
- `tests/test_screen_peppol_exact_org_reach.py`;
- `.github/workflows/research-peppol-exact-org-screen.yml` (manual-only).

Verified upstream format from the official Peppol Directory implementation:

- gzip-compressed BusinessCard export;
- ISO-8859-1 text;
- semicolon-separated CSV;
- columns include Participant ID, Names, Websites, Contact email and Registration date;
- Norwegian exact participant scheme: `0192:<9-digit orgnr>`;
- export documentation limits a given export file to two downloads per IP per 24 hours by default.

Observed source snapshot during format qualification:

- compressed bytes: **357,195,380**;
- SHA-256: `619d92a63fdbfa202351c0564ad1687b61d88b686c57effbfddaf26c27886ffb`.

The first live coverage attempt downloaded successfully but failed only because the initial parser assumed comma separation. The official implementation proved the separator is `;`; the parser and fixture tests are now corrected and green. We deliberately did not issue a third same-day download.

Promotion still requires:

1. one clean exact-0192 coverage run after the rate-limit window;
2. meaningful website-candidate reach;
3. explicit directory-data reuse-rights clearance before any production proposal;
4. independent Signalpost website verification for every candidate.

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

## R4 — source-union comparison

Status: **PENDING MORE VIABLE MEMBERS**.

Once R2 and further R3 source screens produce candidates, compare their union on the same consumed material and compute:

- exact companies covered;
- net-new companies over current output;
- recent activity companies;
- website candidates;
- email candidates;
- external requests;
- `net_new_companies / requests`;
- rights status;
- precision exceptions;
- overlap between sources so raw hit counts are not double-counted.

Only after this comparison should any production reallocation be discussed.

## Current direction

1. Do not revisit TED unchanged.
2. Run the corrected Peppol exact-0192 screen only after the export rate-limit window; do not weaken the rights gate.
3. Continue Data.norge/source discovery for additional **bulk + exact-org + rights-clean** registries, with priority on website/contact and recent business-activity sources rather than more narrow historical facts.
4. Screen one new source family at a time on consumed material.
5. Build the union comparator once at least two nontrivial candidate sources survive.
6. Keep this entire track isolated from production until a source/union demonstrates materially better coverage-per-request.
