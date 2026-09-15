# H2c — verified company-site contact emails

## Decision

**Promote, subject to PR/post-merge regression.** H2c converts contact email addresses already present in the bounded text retained from an exact verified company website into formal `external.contact_email` output-contract claims.

H2c performs **no additional network request** and introduces **no third-party API cost**.

## Claim boundary

The only H2c claim is:

> The exact verified company webpage published this contact email at the recorded retrieval time/content hash, and the email registered domain matches the verified website registered domain.

H2c does **not** claim that:

- the mailbox is deliverable now;
- a specific named individual owns or controls the mailbox;
- the address remains current after the recorded retrieval time;
- a cross-domain group/brand email belongs to the legal entity.

Publication requires all of the following:

- the website evidence state is `available`;
- the website exact-entity assessment is publishable;
- the profile has a valid 9-digit Norwegian organisation number;
- the verified website has a valid source URL, retrieval timestamp and 64-character content hash;
- the email appears in the bounded identity/footer/contact/legal text retained from that website snapshot;
- the email and verified website share the same registered domain;
- placeholder/no-reply local parts are rejected;
- at most three distinct contact emails are emitted per company;
- the resulting external observation passes the existing publication/evidence validator before contract projection.

## Fresh zero-overlap qualification

Workflow: `H2c Company Contact Email Qualification`

Successful exact-head run: `34992345539` (run #6), head:

`ae91b95e72fd7cd852a61826d5719df73774f9b1`

Qualification artifact:

- artifact ID: `10405904993`
- ZIP digest: `sha256:b5703cf7ed83032d0dbaeb000e3aba2d27372a4fe7b7bc318eb62d98101b5367`

All prior validation cohorts were recreated and hash-checked before fresh selection. H2c excluded **3,700 unique previously touched companies**.

Fresh selector:

- seed: `20260924`
- count: 300
- excluded rows: 3,700
- overlap: 0
- evaluation split: `h2c_company_contact_email`
- sample slice: `fresh_same_domain_contact_email_validation`
- fresh manifest SHA-256: `eee5765bcdfed57aa81489c2f3ef613bf612fcde92f73e5dc641df97905812bf`

The integrated production runner completed:

- 300/300 final objects
- 300/300 present in the current BRREG bulk snapshot
- production report `passed=true`
- 1,789 observed logical requests
- 3,578 conservative challenge-charged requests
- theoretical ceiling 5,406 for 300 (= **1,802/100**, unchanged)
- wall runtime 203.119 seconds
- third-party API cost: $0
- search API requests: 0
- 37 verified company websites
- 19 existing H2a profile-handle observations across 13 companies
- contract errors: 0
- change errors: 0
- budget errors: 0

H2c produced:

- **24** `external.contact_email` observations/claims
- **19** companies with at least one contact email
- reach over all fresh profiles: **19/300 = 6.33%**
- reach over verified company websites: **19/37 = 51.35%**
- observation validation errors: 0
- integrated contact-email claims: 24
- added network requests: **0**
- added third-party cost: **$0**

## Fresh manual audit

Every emitted observation was manually reviewed against the retained exact-company website snapshot. The audit asks only whether the verified company page actually published the address under H2c's narrow claim boundary. It does not test SMTP deliverability.

| Organisation | Company | Contact email | Verified page | Result | Manual note |
|---|---|---|---|---|---|
| 886212062 | AUST-AGDER UTVIKLINGS- OG KOMPETANSEFOND STI | `pon@aaukf.no` | `https://www.aaukf.no/` | Correct | Exact company homepage snapshot explicitly publishes the address; same registered domain. |
| 887898332 | EIGERØY BARNEHAGE SA | `post@eigeroy-barnehage.no` | `https://www.eigeroy-barnehage.no/` | Correct | Snapshot publishes company address and email together; same registered domain. |
| 914479916 | COVE AS | `post@cove.no` | `https://cove.no/` | Correct | Exact Cove AS page/footer explicitly publishes the address. |
| 916548370 | LARSENS BAKERI AS | `bestilling.farsund@larsensbakeri.no` | `https://larsensbakeri.no/` | Correct | Exact bakery page publishes the Farsund ordering address. |
| 916548370 | LARSENS BAKERI AS | `bestilling.vanse@larsensbakeri.no` | `https://larsensbakeri.no/` | Correct | Exact bakery page publishes the Vanse ordering address. |
| 923239596 | ALTERNATIV ASSISTANSE AS | `post@alternativassistanse.no` | `https://alternativassistanse.no/` | Correct | Exact company snapshot names Alternativ Assistanse AS and publishes the address. |
| 925328472 | ONGA AS | `info@onga.no` | `https://onga.no/` | Correct | Snapshot includes exact org number `925328472`, company address and email. |
| 929361164 | LAGERFØRING AS | `info@lagerforing.no` | `https://lagerforing.no/en/` | Correct | Exact site snapshot publishes Lagerføring AS and email; identity gate also has exact-org evidence. |
| 931755323 | XIIT AS | `malfrid@xiit.no` | `https://www.xiit.no/` | Correct | Exact site contact section publishes the named employee address and registered Mandal location. |
| 931755323 | XIIT AS | `rolf@xiit.no` | `https://www.xiit.no/` | Correct | Exact site contact section publishes the named employee address and registered Mandal location. |
| 931755323 | XIIT AS | `terje@xiit.no` | `https://www.xiit.no/` | Correct | Exact site contact section publishes the named employee address and registered Mandal location. |
| 931868780 | ARTISTFELLESSKAPET AS | `post@artistfellesskapet.no` | `https://www.artistfellesskapet.no/` | Correct | Exact site snapshot publishes the email alongside the company's Stavanger address. |
| 933334481 | REN TJENESTE AS | `post@rentjeneste.no` | `https://rentjeneste.no/` | Correct | Exact site snapshot includes exact org/company/location evidence and the email. |
| 934903331 | LYNGBY CONSULTING AS | `post@lyngbyconsulting.no` | `https://lyngbyconsulting.no/` | Correct | Exact site contact block publishes registered Oslo address and the email. |
| 938984263 | KMS ARKITEKTER AS | `post@kms-arkitekter.no` | `https://kms-arkitekter.no/` | Correct | Exact company site publishes the address; company contact page also exposes the exact org number. |
| 941188133 | SØR-VARANGER AVIS A/S | `abonnement@sva.no` | `https://www.sva.no/` | Correct | Exact newspaper snapshot explicitly publishes subscription contact address. |
| 941188133 | SØR-VARANGER AVIS A/S | `annonser@sva.no` | `https://www.sva.no/` | Correct | Exact newspaper snapshot explicitly publishes advertising contact address. |
| 941188133 | SØR-VARANGER AVIS A/S | `redaksjon@sva.no` | `https://www.sva.no/` | Correct | Exact newspaper snapshot explicitly publishes editorial contact address. |
| 943945039 | VESTNES LAND AS | `atle@vestnesland.no` | `https://www.vestnesland.no/` | Correct | Snapshot includes exact org number `943945039`, company address and email. |
| 982537401 | TUNDRA SOL AS | `ordre@tundra.no` | `https://www.tundra.no/` | Correct | Exact Tundra site publishes the ordering email; current contact page ties the domain to Tundra Sol AS. |
| 987214597 | EIENDOMSFINANS DRIFT AS | `firmapost@eiendomsfinans.no` | `https://eiendomsfinans.no/` | Correct | Exact company site publishes the address; first-party company/legal pages also expose exact org `987214597`. |
| 990903859 | FESTPARTNER KJERSTI HELENE GLESTAD | `post@festpartner.no` | `https://festpartner.no/` | Correct | Exact site publishes the contact email; exact-org identity evidence already passed. |
| 993567264 | GAUSDAL OPTIKK AS | `post@gausdaloptikk.no` | `https://www.gausdaloptikk.no/` | Correct | Exact site contact content publishes the email and matching Gausdal business identity/location. |
| 995898705 | JOY4ALL AS | `post@joy4all.no` | `https://joy4all.no/` | Correct | Snapshot includes exact org number `995898705`, registered address and email. |

Observed fresh manual precision for the narrow first-party contact-email claim: **24/24 correct (100% point estimate)**.

This sample does **not** by itself prove the hidden challenge's >=95% external precision threshold, and H2c does not establish the hidden >=60% weighted external-company-recall requirement.

## Safety properties and regressions

H2c is intentionally narrower than a generic email scraper:

- exact website identity is mandatory;
- cross-domain emails abstain even if they might be legitimate group/brand contacts;
- common placeholder/no-reply local parts abstain;
- invalid organisation numbers, missing hashes/timestamps and non-publishable websites abstain;
- contract projection re-runs idempotently without duplicating `external.contact_email` claims;
- projection preserves claim-specific source URL, retrieval time, content hash and evidence span;
- tests explicitly document that H2c does not assert email deliverability or a specific human owner.

The exact-head qualification passed the full repository suite before the fresh run and then passed the integrated fresh-300 production assertions.

## Cost and request-budget impact

H2c only transforms evidence already captured by the bounded company-site fetch. It performs **zero additional network operations**. Therefore the structural request ceiling remains **1,802 conservative challenge-charged requests per 100 companies**, and third-party API cost remains **$0**.

## What H2c changes strategically

H2c is materially stronger than H2b/company activity on observed reach: it produces a supported first-party external field for **51.35% of verified websites** in the fresh cohort at no request cost. It therefore deserves production integration under the current zero-cost strategy.

It still does not solve the primary hidden scoring risk by itself. Coverage/weighted external recall remains open because many companies do not yet have a verified website, and H2c adds no jobs, reviews, independent activity, engagement metrics or sentiment.
