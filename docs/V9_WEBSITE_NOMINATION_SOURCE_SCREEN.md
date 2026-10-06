# V9 Website-Nomination Source Screen

Updated: 2026-10-06

Status: **source landscape screened before live provider experimentation**

This document records V9 source-selection evidence only. It does not change the V8 production source register and does not authorize any new publication source.

## Selection constraints

Any V9 nomination source must satisfy all of the following before a live experiment:

1. improve unresolved exact-company website nomination;
2. preserve organisation-number-first identity;
3. be evaluator-reproducible;
4. have a documented rights/use basis;
5. fit the current project policy of $0 third-party API spend unless explicitly changed;
6. remain nomination-only until an independently fetched page passes the existing exact-company verifier;
7. avoid consuming a fresh cohort for tuning.

## Norid organisation-number lookup — RIGHTS BLOCKED / SHELVE

Norid's public lookup service technically supports organisation-number lookups that return the domains held by an organisation. That makes it an attractive exact-identity discovery source in principle.

However, Norid's current lookup terms are not compatible with using the service as a systematic Signalpost discovery feed:

- the service terms limit use to the stated directory-service purposes;
- commercial use of lookup-service data is forbidden;
- copying/storing/downloading/transferring all or significant parts of the lookup data is forbidden;
- repeated lookups are rate-limited and can be blocked;
- Norid explicitly says requests for compilations or broader disclosure require a separate assessment.

Official references reviewed:

- https://www.norid.no/en/domeneoppslag/
- https://www.norid.no/en/domeneoppslag/vilkar/
- https://www.norid.no/en/domeneoppslag/personvern/domeneoppslag/
- https://www.norid.no/en/domeneoppslag/requirements-for-disclosing-customer-information/

Decision: **SHELVE / RIGHTS BLOCKED**. Do not automate Norid reverse lookups for V9 and do not treat the public lookup service as an evaluator discovery dependency.

## Paid/search-provider path — NOT ENABLED

The repository already contains historical SerpApi/H1b tooling, but the current V8 production declaration has:

- search APIs: none;
- third-party API spend: $0;
- no evaluator-provisioned SerpApi key/cost contract.

V9 now has a generic provider gate (src/norway_company_agent/v9_provider_gate.py) so a future provider cannot be enabled without explicit reproducibility, rights, credential and cost declarations. No concrete provider is currently approved.

Decision: **do not run live search yet**.

## Selected next micro-screen — BRREG annual-report domain signals

The qualified H2g path already fetches and OCRs official BRREG annual-account PDFs for companies lacking registry workforce values. For those already-paid-for-in-request-theorem reports, V9 can test whether explicit first-party URLs or non-generic email domains provide useful website nominations.

Why this source was selected for the next consumed Gate-A screen:

- official BRREG source already used by production;
- exact target organisation number is recovered from the report before extraction;
- no new third-party source or API key;
- $0 third-party API cost;
- candidate extraction can reuse the same PDF bytes/OCR text in a future implementation;
- extracted domains remain untrusted nominations;
- final website publication still requires an independent first-party fetch and the unchanged exact-company verifier.

The first implementation is on isolated branch:

experiment/v9-annual-domain-discovery

The experiment must be evaluated only on the frozen consumed Gate-A 20 until a promotion decision is made.


## Annual-report screen result — SHELVE

The selected BRREG annual-report micro-screen completed on the frozen consumed Gate-A 20:

- workflow: `37424227898` — PASS
- head: `91ed58af60f2bd1a7fec06b29a9224a8168bee15`
- annual reports selected: 15
- candidate domains: 1
- new verified websites: 0
- conservative request charge: 34
- third-party API cost: $0
- runtime: 70.760 s

The only candidate, `tellnorge.no` for STORELVA IDRETTSPARK AS, was independently fetched and rejected because the page explicitly identified another legal entity.

Decision: **SHELVE annual-report domain extraction as a primary V9 website-nomination source.**

## External search reconnaissance — useful but not provider-qualified

External reconnaissance found plausible candidates that the unchanged verifier accepted for three frozen Gate-A organisations:

- AURSNES KIOSK AS → `aursneskiosk.no`
- FALEX FORVALTNING AS → `falex.no`
- PREG BARNEHAGER ÅLESUND AS → `pregalesund.barnehage.no`

The final consumed verifier calibration run `37426159410` passed and kept wrong/weak controls quarantined.

This demonstrates that broader search-like nomination has real value, but it does **not** authorize a concrete provider because the reconnaissance path itself is not the evaluator-reproducible provider contract required by V9.

Gate-A remains **RETUNE** at 3/20 machine-verifiable uplift versus the required 5/20 continuation gate. See `docs/V9_GATE_A_RETUNE.md`.
