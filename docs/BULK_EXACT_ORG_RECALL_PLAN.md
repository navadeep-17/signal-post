# Signalpost — isolated bulk exact-org recall plan

Date: 2026-10-05
Branch: `research/bulk-exact-org-recall`
Base main SHA: `88be83e226da13ba6f7a2717c72c1d2d94cf5bec`

## Goal

Find a materially stronger recall mechanism without touching the production runner, current qualification work, or any fresh evaluator cohort.

The research track optimizes for:

`net-new exact-company coverage / external requests`

and keeps the existing precision rule:

> ATTEMPT MORE -> VERIFY STRICTLY -> PUBLISH CONSERVATIVELY

## Safety boundary

- research branch only;
- no imports from research scripts into production code;
- no mutation of `run_signalpost_v8.py` or request-accounting code;
- no fresh Phase-11/Q8 cohort;
- use only already-consumed `submission/final-release-1000.jsonl` rows for source selection;
- source-selection scripts publish no production claims;
- exact nine-digit organisation-number attribution is mandatory;
- name-only matches are never counted as exact-company hits;
- website/email outputs are candidates only until independently verified;
- no source is promoted without clear reuse rights and reproducible access.

## Milestone R1 — TED procurement winner screen

### Hypothesis

The TED Search API can retrieve contract-award winners by `winner-identifier` in a small number of shared requests. A useful match may provide multiple high-value fields at once: exact winner identifier, dated award activity, website candidate and email candidate.

### Architecture

1. deterministically select 100 companies from the already-consumed final-release 1000;
2. query TED using batched `winner-identifier IN (...)` expert queries;
3. request only bounded fields needed for source qualification;
4. parse returned identifiers conservatively and match only exact target org numbers;
5. measure companies with any award, recent award, website candidate and email candidate;
6. preserve raw response hashes and query text for audit;
7. do not fetch or publish candidate websites in R1.

### Promotion gate

R1 is worth a second-stage verifier experiment only if at least one of these holds on consumed 100:

- >= 3 companies have exact winner records with recent dated activity; or
- >= 3 companies gain website candidates; or
- the source yields another clearly material multi-family gain at <= 5 shared Search API requests.

Any wrong-company identifier association is an automatic NO-GO until understood.

## Milestone R2 — Peppol Directory bulk screen

### Hypothesis

The daily Peppol Directory export can map exact Norwegian participant IDs (`0192:<9-digit orgnr>`) to website/contact metadata with one shared bulk download.

### Method

- use `/export/businesscards-csv` or JSON export;
- filter only participant scheme `0192`;
- exact-match against the same consumed 100;
- measure website/email candidate reach and overlap with existing verified websites;
- never treat Peppol metadata as publication proof;
- resolve reuse-rights ambiguity before any production proposal.

### Promotion gate

Proceed to independent website verification only if the bulk screen produces materially more exact website candidates than current deterministic discovery at negligible request cost and reuse rights are cleared.

## Milestone R3 — Data.norge source miner

### Hypothesis

A union of many small exact-org public datasets may outperform betting on a single national API.

### Method

Use Data.norge's open SPARQL/search/resource services to discover and rank datasets whose metadata suggests:

- organisation number;
- website / URL;
- email / contact;
- supplier / award / support;
- approval / licence / status;
- dated events.

Rank each candidate by:

1. explicit reuse licence;
2. public/evaluator-reproducible access;
3. exact organisation-number key;
4. bulk/shared retrieval;
5. freshness;
6. likely company-level reach;
7. scored-family value.

No connector is built from this milestone; it is source selection only.

## Milestone R4 — source-union comparison

If R1/R2/R3 produce viable candidates, compare their union on the same consumed 100 and compute:

- exact companies covered;
- net-new companies over current output;
- recent activity companies;
- website candidates;
- email candidates;
- logical external requests;
- `net_new_companies / requests`;
- rights status;
- precision exceptions.

Only after this comparison should any production reallocation be discussed.

## Current action

Start R1 now. TED is first because the Search API is public, does not require authentication for published notices, supports expert queries, and exposes winner identifier / website / email / decision-date fields.
