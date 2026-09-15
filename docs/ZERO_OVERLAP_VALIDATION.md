# Zero-overlap external precision validation

## Purpose

Measure wrong-company publication risk on companies that were not present anywhere in the 1,000-company development/release manifest selected with seed `20260823`.

This validation is intentionally separate from:

- frozen development 100 (rows 1-100 of the entry manifest),
- earlier H1 validation/qualification slices inside that manifest,
- the reserved final 200-company holdout inside that manifest.

The validation corpus is sampled from the same frozen Builderr universe only after excluding all 1,000 entry-manifest organisation numbers.

## Frozen selection protocol

1. Recreate the 1,000-company entry manifest with `select_entry_batch.py`, seed `20260823`.
2. Exclude every organisation number in that manifest.
3. Deterministically sample 300 companies from the remainder with seed `20260915` using `scripts/select_disjoint_validation_batch.py`.
4. Record universe, excluded-manifest and selected-corpus SHA-256 values.
5. Require `overlap_count == 0` before any live enrichment runs.

The reserved final 200-company holdout is therefore not consumed by this validation.

## Frozen corpus

- Builderr frozen universe rows: `411160`
- Excluded original entry manifest rows: `1000`
- Eligible after exclusion: `410160`
- Validation rows: `300`
- Overlap with original 1,000: `0`
- Validation seed: `20260915`
- Universe SHA-256: `1c89710e5b01f8617e86d09fbdff4a52f2f8dbbba297e74f7164b5984f5a0384`
- Excluded-manifest SHA-256: `01d262523f3b1fe71dc7e18b8f7675a866d3a79042e072b4961b0322fe1033b8`
- Validation-300 SHA-256: `4248438faa42508f7721bdb83002fe15c81735dbf3f97878eba271078864fda5`

## Evaluator protocol

The merged one-command evaluator was run unchanged except for validation-scale count/budget values:

- expected companies: 300,
- workers: 8,
- site timeout: 6 seconds,
- theoretical conservative request ceiling: 5,400 (= 1,800 per 100 companies),
- third-party API cost ceiling: $0,
- search APIs: disabled,
- experimental connectors: disabled.

Workflow: `Zero-Overlap External Precision Validation`

Run: `34926276014`

Artifact digest: `sha256:d0f982597a0a27881dfb2e4f2353c4c41e9f44bc1acea8284626499ad9b6c716`

Measured run result:

- 300/300 unique final contract objects,
- 300/300 terminal status `completed`,
- 1,775 observed logical requests,
- 3,550 conservative challenge-counted requests,
- 1,183.333 conservative requests normalized per 100 companies,
- 270.457 seconds evaluator wall runtime,
- $0 third-party API cost,
- 0 search API requests,
- experimental connectors disabled,
- 0 contract errors,
- 0 budget errors,
- 25 canonical websites published as exact identities.

## Precision audit protocol

The workflow emits `verified-sites.jsonl` containing every company whose final canonical website evidence is `available` and `identity_assessment.publishable == true`.

Every row was manually audited. The audit considered exact organisation number, legal name, registered address/municipality, official registry website fields, company-owned legal/privacy/contact pages, independent public mappings, and redirect/rebrand history. A promotion is a false positive when the published domain belongs to a different legal entity or operation, even if the same words appear in its branding.

## Manual audit

| Org | Company | Published site | Discovery | Result | Audit basis |
|---|---|---|---|---|---|
| 920701310 | LILLEVANNSVEIEN 72 AS | `lillevannsveien72.no` | H1c | correct | Oslo municipality development agreement names the exact org as developer of Lillevannsveien 72; POB identifies project illustrations as owned by Lillevannsveien 72 AS. |
| 925877301 | LUNAR ENTERPRISES AS | `lunarenterprises.no` | H1c | correct | Company site publishes the exact company name and matching Oslo contact identity; independent company records match org `925877301`. |
| 926278592 | ASTMA OG ALLERGIKLINIKKEN AS | `astmaogallergiklinikken.no` | H1c | correct | Site identifies the clinic in Kråkerøy/Fredrikstad; registered entity has the same exact legal name and Fredrikstad identity. |
| 818656742 | ACER DIXON AS | `acerdixon.com` | registry | correct | Registry-linked site; independent climate/industry directory maps exact org `818656742` and company email to `acerdixon.com`. |
| 936772978 | STEELLOGIC AS | `steellogic.no` | H1c | correct | Site identifies Steellogic production at Hensmoen/Hønefoss; official/independent registry records place exact org `936772978` at Hensmoen. |
| 967239070 | NORDØYAN AS | `nordoyan.no` | registry | correct | Official/independent company listing maps exact org `967239070` to `nordoyan.no`. |
| 931041312 | ENKLERE EIENDOM AS | `enklere-eiendom.no` | registry | correct | BRREG explicitly lists `www.enklere-eiendom.no` for org `931041312`. Current page content is weak, but domain ownership mapping is official-registry evidence. |
| 995642034 | MUSEUM STAVANGER AS | `museumstavanger.no` | registry email | correct | Company-owned documents on the domain publish exact org `995642034`; public Stavanger/government records corroborate the entity. |
| 920319408 | BORGESKOGEN METALLGJENVINNING AS | `borgeskogenmetallgjenvinning.no` | H1c | correct | Independent business listing maps the exact company to the domain and matching Sandefjord address. |
| 976960343 | HEXA AS | `hexa.no` | registry email | correct | Site identifies Hexa AS in Trondheim; independent supplier/business records map the same company and address to `hexa.no`. |
| 965594477 | VOLLEN SLIPP AS | `vollenslipp.no` | H1c | correct | Company site publishes exact org `965594477` and matching Asker address; marine-industry listings corroborate the domain. |
| 915244572 | GRAFISK MAILING DISTRIBUSJON AS | `grafmail.no` | registry | correct | Independent company data maps exact org `915244572` to `grafmail.no`. |
| 977301424 | BAKKENS TREPRODUKTER AS | `bakkenstreprodukter.no` | H1c | correct | Company homepage publishes Maskinvegen 24, Vinstra and exact org `977301424`; these match BRREG. |
| 976889754 | NOR COMPANIET AS | `norcompaniet.no` | H1c | correct | Independent company listing maps exact org `976889754` to `norcompaniet.no` and the Båtsfjord entity. |
| 918948260 | L3 CONSULT AS | `l3consult.no` | H1c | correct | Company site publishes Stavanger contact identity; official records for exact org `918948260` match the company and location. |
| 920220495 | AQUAFORM VANNAEROBIC AS | `aquaformvannaerobic.no` | H1c | correct | Site uses the exact distinctive legal name and describes the exact registered purpose (vannaerobic instruction); official records confirm exact org, owner/operator and Bærum entity. |
| 911724081 | HOPEFUL STI | `hopeful.no` | registry | correct | Public education/company records map exact org `911724081` to `www.hopeful.no`. |
| 916622694 | ALT I 3 AS | `alti3.com` | registry | correct | Public company record maps exact org `916622694`, Longyearbyen/Svalbard and company email to `alti3.com`. |
| 933200353 | OSLO MIKROSEMENT AS | `oslomikrosement.no` | H1c | **WRONG** | Exact legal entity publishes `oslomikrosement.com`, Carl Bergersens vei 47A, Hagan and org `933200353`. The promoted `.no` site instead presents a Basebeton-oriented operation with different Oslo/Gjettum contacts. Matching name/domain/title was insufficient identity proof. |
| 997871243 | LOUD AND CLEAR AS | `loudandclear.no` | H1c | correct | Public vocational/business listings map LOUD AND CLEAR AS to `@loudandclear.no`; official company record confirms org `997871243` and Oslo design activity. |
| 934881613 | LARO CONSULT AS | `laro-consult.no` | H1c | correct | Company site explicitly publishes `Laro Consult AS` and org `934881613`; registry records match. |
| 975874982 | SNØHETTA DATA AS | `snohettadata.no` | registry redirect | correct | Registry site was legacy `ramvik.no`; company privacy/legal page on `snohettadata.no` publishes org `975874982` and documents the Ramvik AS → Snøhetta Data AS name change. |
| 993272590 | FORUS FRISKOLE AS | `forusfriskole.no` | registry | correct | Public official/education records map exact org `993272590` and company email to `forusfriskole.no`. |
| 989909576 | CLOUDS AS | `clouds.no` | registry email | correct | Company-owned contact page publishes org `989909576` and matching Oslo address. |
| 984612923 | ERGOLINE AS | `ergoline.no` | registry | correct | Company site identifies ErgoLine AS at Tornsangerveien 13, Fornebu; its own policy/catalogue documents map the same company/address to `ergoline.no`. Current BRREG also retains a legacy/alternate `ergo-line.com` contact mapping. |

## Precision result

- audited promotions: `25`
- correct: `24`
- wrong-company publications: `1`
- observed point precision: `96.0%`
- approximate 95% Wilson interval: `80.5%–99.3%`

The 96% point estimate is above the challenge's 95% threshold, but **this is not a precision qualification pass**. One wrong-company publication is material, and the sample is too small for a zero-risk/comfortable precision claim.

## Failure mechanism

`OSLO MIKROSEMENT AS` exposed a generic H1c weakness. For multi-token legal names, `deterministic_domain_page_identity_guard_v3` can publish when:

1. a deterministic guessed domain strongly resembles the legal name,
2. the independently fetched homepage contains the full distinctive legal name,
3. the page title and final domain also resemble that name,
4. but the page contains neither the exact organisation number nor registry-location corroboration.

A namesake/brand operation can satisfy all four conditions. This is not specific to `oslomikrosement.no` and must not be fixed with a domain blacklist.

## Decision

**Validation infrastructure: MERGE. Precision qualification: FAIL/HOLD.**

Do not tune the identity rule and then reuse this 300-company corpus as unbiased confirmation. The next precision confirmation must use a new deterministic zero-overlap corpus that excludes:

- all original 1,000 entry-manifest companies, and
- all 300 companies in this validation corpus.

The reserved final 200-company holdout remains untouched.
