# JSON-LD contact recovery — current-main transfer qualification

Date: 2026-10-06  
Branch: `research/jsonld-contact-transfer-main-20261006`  
Base: current `main` at branch creation (`72f1bf2892ec1c1e35674aa383433c9a37afdaca`)

## Scope

This branch is an isolated transfer qualification only. It is not merged into `main`.

The candidate extends H2c contact-email extraction with a zero-network path over already-retained
`schema.org Organization` nodes. Existing footer/contact-text H2c behavior remains unchanged and
keeps precedence when the same email is present in both paths.

Publication boundary for the new path:

1. the website must already be exact/publishable under the existing website identity gate;
2. the individual structured Organization node must identify the target legal entity:
   - exact target organisation number in a structured identity field; or
   - full normalized legal-name token containment when no conflicting structured organisation number exists;
3. any explicit different structured nine-digit organisation number vetoes name-based acceptance;
4. an email is extracted only from an explicit structured field named `email`, including nested `ContactPoint.email`;
5. the email registered domain must equal the verified website registered domain;
6. free-text JSON-LD scanning and cross-domain contact inheritance are forbidden;
7. zero network requests are added.

Strategy identifier:

`verified_company_jsonld_same_domain_email_v1`

## Code under test

Production-module delta:

- `src/norway_company_agent/company_site_contact.py`

Adversarial transfer tests:

- `tests/test_jsonld_contact_recovery_transfer.py`

Research-only workflows:

- `.github/workflows/research-jsonld-contact-transfer-main.yml`
- `.github/workflows/research-jsonld-contact-structural-audit.yml`
- `.github/workflows/research-jsonld-contact-baseline-ci.yml`

No production runner change is required: current `run_signalpost_final.py` already calls
`attach_company_site_contact_email_observations()` after exact website verification.

## Current-main frozen-1000 transfer result

Successful transfer gate:

- workflow run: **37420576289**
- artifact: **11393086101**
- artifact SHA-256: `7c6aec8c6b59beb973789918087ffbaa2953bb57f35cad12d4fae75cfb5ec7c4`

Measured coverage:

- baseline contact-email companies: **53/1000**
- challenger contact-email companies: **58/1000**
- true net-new contact-covered companies: **5/1000 = 0.5%**
- baseline contact-email claims: **57**
- challenger contact-email claims: **64**
- net-new contact claims: **7**
- companies receiving at least one new contact claim: **7**

The distinction above is important: two of the seven companies gaining a new claim already had another
contact email, so coverage rises by five companies, not seven.

Correctness gates:

- lost existing contact companies: **0**
- non-contact claim mutations: **0**
- observation validation errors: **0**
- output-contract errors: **0**
- canonical-projection errors: **0**
- synthesis errors: **0**
- logical requests added: **0**
- conservative request charge added: **0**
- third-party API cost added: **$0**
- transfer promotion gate: **PASS**

All seven new claims used `structured_legal_name_token_match`; none depended on an exact org number
inside the retained JSON-LD node.

## Structural precision audit

Successful structural audit:

- workflow run: **37420890000**
- artifact: **11392992478**
- artifact SHA-256: `7ad05701269f3cffe9d172b915d9ceffe71bd3061203ae06c7f78ca40dda46b4`

Results:

- candidate claims: **7**
- candidate companies: **7**
- candidates with a competing same-domain email on a non-target Organization node: **0**
- candidates with any explicit different-org node: **0**
- structurally ambiguous candidates: **0**
- one candidate (PROZO NORGE AS) contains duplicate target-matching Organization nodes; this is
  duplicate target schema, not cross-entity ambiguity.

The seven privacy-minimized candidate identities/domains were:

| Company | Org nr | Verified site | Contact domain | Structured identity |
|---|---|---|---|---|
| ENTALPY AS | 927097532 | entalpy.no | entalpy.no | full legal-name tokens |
| TØLLEFSENHJØRNET AS | 928832562 | tollefsenhjornet.no | tollefsenhjornet.no | full legal-name tokens |
| LEAN TECH AS | 915338275 | leantech.no | leantech.no | full legal-name tokens |
| PROZO NORGE AS | 987934239 | prozo.no | prozo.no | full legal-name tokens |
| KINGS BAY AS | 930155500 | kingsbay.no | kingsbay.no | full legal-name tokens |
| TRUCKTECH AS | 980152634 | trucktech.no | trucktech.no | full legal-name tokens |
| SLITASJETEKNIKK AS | 976160975 | slitasjeteknikk.no | slitasjeteknikk.no | full legal-name tokens |

Raw email values are intentionally absent from the research report/artifacts.

## Full repository regression

Successful current-main-equivalent offline baseline:

- workflow run: **37420949134**
- full tests: **539 passed + 5 subtests passed**
- certified-1000 canonical facts: **19,951**
- canonical failures: **0**
- submission-bundle verification: **PASS**
- refresh false positives: **0**
- refresh false negatives: **0**
- refresh evidence complete: **true**
- refresh idempotent rerun: **true**
- refresh qualification: **PASS**

## Decision

**QUALIFIED AS A NARROW PROMOTION CANDIDATE, NOT MERGED.**

The measured score lift is modest (+0.5 percentage points of company contact coverage on the frozen
1000), but it is unusually cheap: zero requests, zero API spend, no request-theorem impact, and no
observed regression to existing claims.

This should be considered only as a precision-preserving incremental improvement. It is not a
solution to the large Builderr recall gap by itself.

Before production promotion, the active implementation workstream should decide whether to take this
single-module change into its current PR/qualification sequence. Do not merge this research branch
directly if `main` has advanced; rebase/cherry-pick the narrow module+tests onto the then-current main
and rerun Baseline CI plus the frozen-1000 transfer gate.
