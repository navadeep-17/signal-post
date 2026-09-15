# Final Release Audit

Date: 2026-09-15

## Release candidate

The audited production code is exactly:

`24145ffb98e36c31a16145d6408a7556a38b5289`

No production logic or identity threshold was changed between the 800-company non-heldout scale validation and the final 200-company held-out audit.

The final held-out split was the predeclared lines 801-1000 from the deterministic 1,000-company manifest generated with seed `20260823`.

Held-out manifest SHA256:

`fb81f7695ee91606d1af7eee00e8323a326ebc33b79b3cb1a4f046573ae3368f`

The held-out 200 had zero overlap with the first 800 companies. The held-out set was not used for tuning before this release audit and must not be used as a tuning set after this audit.

## Pre-holdout 800-company release-scale gate

Actions run: `34946808243`

Result: **PASS**

- 800/800 final objects
- 800/800 terminal outputs completed
- 12,696 claims / 12,696 evidence records
- 4,688 observed logical requests
- 9,376 observed conservative challenge-counted requests
- 518.772 s wall runtime
- $0 third-party API spend
- 0 search API requests
- 0 contract errors
- 0 change errors
- 0 budget errors
- 55 verified company websites
- 799 present in the current BRREG bulk snapshot
- 1 snapshot-drift entity preserved (`928987728`)
- 0 overlap with the final held-out 200

Validation artifact ID: `10387843322`

Artifact SHA256:

`153fd7bf25a424650fe427bde8d0da559aec0835184892ba2fa231900d08655e`

## Final untouched 200-company held-out audit

Validation-only workflow commit:

`096bbdb751cfba468b19cd43667d97da4611f4fb`

This commit adds only the audit workflow. Application code remains the production release candidate `24145ffb98e36c31a16145d6408a7556a38b5289`.

Actions run: `34948307697`

Result: **PASS**

### Mechanical / contract results

- 205 tests passed + 5 subtests passed before opening the held-out set
- 200/200 final objects
- 200/200 unique organisation numbers
- 200/200 terminal outputs completed
- 200/200 current BRREG bulk rows present
- 3,191 claims / 3,191 evidence records
- 1,208 observed logical requests
- 2,416 observed conservative challenge-counted requests
- 1,208 conservative requests normalized per 100 companies
- 1,802 theoretical logical-request ceiling for 200 companies
- 3,604 theoretical conservative-request ceiling for 200 companies
- 122.656 s wall runtime
- p50 request latency: 490 ms
- p95 request latency: 573 ms
- $0 third-party API spend
- 0 search API requests
- experimental connectors disabled
- 0 contract errors
- 0 change errors
- 0 budget errors
- 20 verified company websites

Website source mix:

- registry-linked website: 11
- registry email-domain candidate: 2
- deterministic legal-name-domain H1c: 7
- no verified website: 180
- Wikidata candidates selected as final canonical site: 0

Wikidata candidate discovery remained bounded at 2 shared requests for 200 organisation numbers, returned 3 candidates, 0 ambiguous candidates, and 197 missing.

Validation artifact ID: `10388281985`

Artifact SHA256:

`d2e87c64324df31643ef969b9fd432d33fe971c8689c36833b9a56edf5176efd`

## Manual held-out website precision audit

Every one of the 20 published held-out websites was manually checked after the frozen run completed. No publication was used to change the release candidate.

| Org. no. | Company | Published website | Discovery path | Audit result | Corroboration |
|---|---|---|---|---|---|
| 915713769 | ZIVID AS | `zivid.com` | registry-linked | Correct | Company contact/about page states Zivid AS and VAT `NO 915713769` |
| 932194198 | UM EIENDOMSDRIFT AS | `umeiendomsdrift.no` | H1c + secondary | Correct | Site identifies UM Eiendomsdrift AS at Stålfjæra 17, matching the registered entity/address |
| 928978680 | VINJE KIROPRAKTOR AS | `vinjekiropraktor.no` | H1c | Correct | Site identifies Vinje Kiropraktor AS at Averøyveien 34, matching the registered entity/address |
| 917397341 | NORDIC AMERICAN AS | `nordic-american.com` | registry-linked | Correct | Public registry-derived listings tie org `917397341` directly to this website/domain |
| 927358298 | NORDTECH SERVICES AS | `nordtech-services.no` | registry-linked | Correct | Registry-derived listing ties org `927358298`, email and website to the domain |
| 919881151 | ISOBYGG INNLANDET AS | `isobygg.no` | registry-linked | Correct | Isobygg's own Innlandet page states org `919881151` |
| 982701570 | EGAS SPORT AS | `egas.no` | registry email-domain | Correct | Egas purchase terms state Egas Sport AS and org `982701570` |
| 922750688 | VASK OG BAD AS | `vaskogbad.no` | registry-linked | Correct | Site terms identify VASK OG BAD AS; public company listing confirms org `922750688` |
| 982349362 | INFOSERVE AS | `infoserve.no` | registry email-domain | Correct | Independent company/regulatory listings tie org `982349362` to `khs@infoserve.no` |
| 917554579 | 5ARNS DATA AS | `5arndata.no` | registry-linked | Correct | Registry-derived listings directly tie org `917554579` to `5arndata.no` |
| 986455213 | BRADY ENERGY NORWAY AS | `bradytechnologies.com` | registry-linked | Correct | Registry-derived listings directly tie org `986455213` to `www.bradytechnologies.com` |
| 995899728 | RENATE EVENSEN NUF | `renateevensen.no` | H1c exact org | Correct | Business directory ties Renate Evensen NUF/address to `renateevensen.no`; frozen page proof contained exact org number |
| 922297738 | NOBISCURA AS | `nobiscura.no` | H1c + secondary | Correct | Site identifies NobisCura AS at Lienga 6, matching the registered entity/address |
| 916774915 | KILEN MOTOR AS | `kilenmotor.no` | H1c + secondary | Correct | Site identifies Kilen Motor AS and its air-cooled VW/Porsche motor activity, matching the registered company purpose |
| 943088136 | BESTSELLER AS | `bestseller.com` | registry-linked | Correct | Registry-derived listings directly tie org `943088136` to `www.bestseller.com` |
| 953264560 | FJORDFISK AS | `fjordfisk.no` | H1c | Correct | Company directory lists Fjordfisk AS, org `953264560`, and `fjordfisk.no` together |
| 941561071 | RUDOLF STEINERSTIFTELSEN | `rudolfsteinerstiftelsen.no` | registry-linked | Correct | Registry-derived sources tie org `941561071` to the official website |
| 934052315 | NORBIOEN AS | `norbioen.no` | H1c + secondary | Correct | Site identifies NorBioen AS at Dragonveien 54, matching the registered entity/address |
| 976073169 | FORSKNINGSSTIFTELSEN NIFU | `nifu.no` | registry-linked | Correct | Registry-derived listing ties org `976073169` directly to `www.nifu.no` |
| 989544314 | ENERGIGÅRDEN AS | `energigarden.no` | registry-linked | Correct | Company material and registry-derived listings tie org `989544314` directly to `energigarden.no` |

Observed held-out website precision: **20 correct / 20 published = 100% point precision**.

There were **0 observed wrong-company website publications** in the final held-out 200.

### Statistical limitation

A 20/20 result is a strong observed result but is not, by itself, statistical proof that the underlying website precision is at least 95%. A two-sided 95% Wilson interval for 20/20 has an approximate lower bound of 83.9%.

Therefore this audit records:

- observed held-out point precision: **100%**
- observed wrong-company publications: **0**
- claim that true precision is proven >=95% from this sample alone: **not made**

## Release decision

### Identity, terminal-output, budget and runtime gates: PASS

The release candidate passed the frozen 100-company gate, the 800-company non-heldout scale gate, and the final untouched 200-company audit without silent drops, contract failures, budget violations, paid API use or observed wrong-company website publication.

The production release candidate remains:

`24145ffb98e36c31a16145d6408a7556a38b5289`

No production-code change should be made from observations in this held-out set without treating the current release audit as consumed/invalidated and obtaining a new independent validation set.

## Important challenge-scoring caveat

The held-out run published a verified website for 20/200 companies (10%). This number is **website discovery coverage**, not the challenge's weighted external-company recall metric.

The challenge qualification requirement for weighted external-company recall must therefore be evaluated separately across the actual external-signal categories and scoring weights. It would be incorrect to claim either that 10% website coverage equals 10% weighted external recall or that the hidden >=60% weighted external-recall gate has been proven by this release audit.

Accordingly:

- release engineering / exact-identity audit: **PASS**
- observed held-out website precision: **PASS, 20/20**
- $0 final-source policy: **PASS**
- challenge hidden weighted external-company recall threshold: **NOT YET ESTABLISHED BY THIS AUDIT**

The next work item should be a scoring/coverage readiness audit and submission/demo hardening, not threshold tuning against the consumed held-out set.
