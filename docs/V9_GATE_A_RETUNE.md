# V9 Gate-A Website Discovery Retune Record

Updated: 2026-10-06

Status: **RETUNE — Gate A has not passed.**

This record is V9 consumed/dev engineering evidence only. It does not change V8 production, the qualified V8 ref, the current submission ref, or Builderr score claims.

## Frozen Gate-A cohort

Gate A is the deterministic 20-company unresolved-site cohort created by the successful V9 consumed baseline:

- baseline workflow: `37421325313` — PASS
- baseline artifact: `v9-consumed-baseline`
- baseline artifact ID: `11393772677`
- Gate-A manifest SHA-256: `f2177abd0bd0d6202f9fe47fd00b8def06b21c01fdf4c864c1f3b68f80b160d5`
- baseline verified websites: **0 / 20**
- fresh qualification credit: **none**

The cohort is not changed after observing results.

The V9 plan requires at least **5 / 20 new verified websites** to continue from Gate A, with zero wrong-company publications, zero evidence defects, bounded cost, and no identity-rule weakening.

## Source screen 1 — BRREG annual-report domain extraction

Isolated branch:

`experiment/v9-annual-domain-discovery`

Successful consumed screen:

- workflow: `37424227898` — PASS
- head: `91ed58af60f2bd1a7fec06b29a9224a8168bee15`
- artifact ID: `11394635506`
- artifact digest: `sha256:89ae7c471a58299bef1170257ce5268e3623cd6d99381eefcb5dc1ca68579273`

Observed:

- companies: 20
- annual-report eligible: 15
- annual-report selected: 15
- annual-report requests: 15
- domain candidates: 1
- independent candidate fetches: 1
- new verified websites: **0**
- conservative request charge: **34**
- third-party API cost: **$0**
- runtime: **70.760 s**
- publication enabled: **false**

The only nominated domain was `tellnorge.no` for STORELVA IDRETTSPARK AS. Independent fetch plus the unchanged exact-company identity gate rejected it because the fetched page explicitly identified a different legal entity.

Decision: **SHELVE as a primary website-discovery source.** It is too sparse for Gate A.

## Source screen 2 — external reconnaissance + unchanged verifier

A separate consumed-only calibration screen tested candidate URLs found during external reconnaissance. These candidates are **not** evaluator-reproducible provider evidence and therefore cannot qualify a production provider path.

Isolated branch:

`experiment/v9-recon-verifier-screen`

Final green calibration:

- workflow: `37426159410` — PASS
- head: `98c8c9b9dc454819ec3f1b4b5528039c1f001c85`
- artifact ID: `11395103216`
- artifact digest: `sha256:f767e401dc2133b1962bb60b51eb5ff9e9a024f666a7eb54f5d0dbceeee9605c`
- tested candidate URLs: **8**
- machine-verified organisations: **3 / 20**
- logical site requests: **16**
- conservative request charge: **32**
- third-party API cost recorded by the verifier screen: **$0**
- production publications: **0**
- fresh qualification credit: **none**

The unchanged verifier accepted:

| Organisation | Company | Verified candidate |
|---|---|---|
| 921093934 | AURSNES KIOSK AS | `https://www.aursneskiosk.no/` |
| 917615624 | FALEX FORVALTNING AS | `https://falex.no/` |
| 930465143 | PREG BARNEHAGER ÅLESUND AS | `https://pregalesund.barnehage.no/` |

Important rejected controls:

- BRAVO MATSENTER AS → `bravoseafood.no`: rejected because the page explicitly identified another organisation number.
- BRAVO MATSENTER AS → SPAR Førde hosted store page: rejected because the page lacked strong exact legal-entity evidence.
- DRONNINGENS GATE 13 AS → `dg13.no`: remained review/ambiguous; no exact organisation-number or sufficient legal-name corroboration.
- SVERRESPLASS BORETTSLAG → Vibbo path: fetch did not produce qualifying first-party evidence in the bounded verifier path.

This is useful precision evidence: broader nomination found plausible domains, but the existing exact-company verifier continued to reject wrong-company, brand-only, ambiguous, and unavailable cases.

## Nomination recall retune

PR `#134` was merged into the **V9 integration branch only**, not `main`.

Integration merge SHA:

`7699b7c44b1ff407893cfb8dba5571866050065e`

The retune widens only the untrusted nomination stage:

- legacy strong search candidates remain eligible;
- exact organisation-number search evidence may nominate;
- full legal-name title evidence may nominate brand/alias domains for independent fetch;
- bounded transient score threshold is `0.45`;
- maximum remains three registered-domain-deduplicated candidates;
- obvious non-first-party hosts remain blocked;
- provider text is not returned as publication evidence;
- `publication_authorized = false` remains invariant.

Focused regression workflow `37425242213` passed **40 tests**, including the existing search verifier, organisation-number conflict, and zero-cost discovery regressions.

No publication identity rule was weakened.


## Source screen 3 — bounded secondary identity fetch

A follow-up experiment tested whether an ambiguous nominated homepage could be rescued by one bounded same-domain legal/contact/privacy page while preserving the same exact-company rules.

Isolated branch:

`experiment/v9-search-secondary-identity`

Final consumed Gate-A screen:

- workflow: `37427405477` — PASS
- head: `a86c3c0af5475b4a047733f4c18a10e74f7bb43c`
- artifact ID: `11395436286`
- artifact digest: `sha256:5b9842f36396df8a77286ef61fa982a97d8fd8a439f200080a9a514e3b3a324e`
- candidates tested: **8**
- machine-verified organisations: **3 / 20**
- secondary identity attempts: **3**
- secondary pages merged: **3**
- incremental secondary accepts: **0**
- logical site requests: **22**
- conservative request charge: **44**
- third-party API cost: **$0**
- runtime: **18.142 s**
- production publications: **0**
- fresh qualification credit: **none**

The accepted organisations remained exactly AURSNES KIOSK AS, FALEX FORVALTNING AS, and PREG BARNEHAGER ÅLESUND AS; all three were already accepted by the primary independent-page verifier.

The secondary path correctly remained conservative:

- BRAVO SEAFOOD stayed a hard negative for BRAVO MATSENTER AS because a competing organisation number was present;
- the SPAR Førde candidate still lacked exact BRAVO MATSENTER legal-entity proof, and the fetched SPAR legal page identified another organisation;
- `dg13.no` remained review/ambiguous because neither exact target organisation-number evidence nor sufficient legal-name-plus-BRREG-location corroboration was recovered.

Decision: **SHELVE / NO-GO for integration.** The mechanism preserved precision but added **0** verified Gate-A companies while increasing request use. Keep the experiment and artifact as engineering evidence; do not merge its runtime code into the V9 integration branch.



## Source screen 4 — expanded manual reconnaissance ceiling

The same consumed-only verifier calibration was extended with additional externally discovered candidate URLs. This is a **ceiling / verifier-capability screen**, not provider qualification evidence.

Final green expanded screen:

- branch: `experiment/v9-recon-verifier-screen`
- workflow: `37439876507` — PASS
- head: `f716890697b6ab6004cbdcd5f5420d02c859d6e9`
- artifact ID: `11400163382`
- artifact digest: `sha256:9ef071c95140d38bb0cfbb14c6ad9ce56ec1013f774171f71e0aef215e541e32`
- candidate URLs tested: **12**
- machine-verified organisations: **4 / 20**
- logical site requests: **23**
- conservative request charge: **46**
- third-party API cost recorded by the verifier screen: **$0**
- production publications: **0**
- fresh qualification credit: **none**
- provider qualification credit: **none**

The fourth exact organisation is:

| Organisation | Company | Verified candidate | Exact-page result |
|---|---|---|---|
| 923368876 | TRE FOR EN AS | `https://hauglidhelse.no/` | accepted, score 1.0 |

The fetched Hauglid Helse page explicitly labelled the exact target organisation number, so the unchanged search-discovered page identity guard accepted it without any verifier weakening.

Additional useful negative/availability evidence:

- `https://vibbo.no/sverresplass/om` is externally known to expose the exact SVERRESPLASS BORETTSLAG organisation number, but the bounded evaluator-style HTTP fetch returned `source_error`; it is therefore **not counted**.
- `https://uba.no/`, linked to STIFTELSEN UTLEIEBOLIGER I ALTA through public company/email-domain discovery, was blocked by the bounded fetch path and is **not counted**.
- `https://yd-maskin.no/`, surfaced as a candidate for YD MASKIN AS, returned `source_error` in the bounded fetch path and is **not counted**.

This raises the observed manual/external reconnaissance ceiling from **3 / 20 to 4 / 20**, while preserving the conservative rule that inaccessible or non-independently-verifiable pages do not receive credit.



## Source screen 5 — fetch-relaxation calibration

After the manual ceiling reached 4 / 20, three narrowly isolated experiments tested whether the missing fifth site was primarily an evaluator-fetch limitation rather than a nomination limitation. These experiments did **not** weaken company identity rules and did **not** change production defaults.

### 5a — explicit two-hop redirect option

Branch:

`experiment/v9-safe-two-hop-redirect`

Consumed calibration:

- workflow: `37442426876` — PASS
- artifact ID: `11401279201`
- artifact digest: `sha256:9525bca9888241e393ac18646d9c0fa03a3a482842a9be62ea73817f0665a3cf`
- candidates tested: **4**
- incremental verified organisations: **0**
- logical site requests: **8**
- conservative request charge: **16**
- third-party API cost: **$0**
- production/default redirect ceiling changed: **false**

The ordinary fetch default remained one redirect. The experiment explicitly allowed two SSRF-checked redirects.

Observed:

- SVERRESPLASS BORETTSLAG → `https://vibbo.no/sverresplass/om`: still ended as `source_error` / HTTP 302 after the bounded redirect allowance.
- YD MASKIN AS → `https://yd-maskin.no/`: the redirect chain progressed farther, but the destination exceeded the ordinary 750 kB page ceiling.
- TRE FOR EN AS positive control remained exact.
- BRAVO SEAFOOD wrong-company control remained rejected.

Decision: **SHELVE.** Two redirects added no Gate-A company.

### 5b — explicit three-hop redirect calibration

Branch:

`experiment/v9-safe-three-hop-redirect`

Workflow:

- workflow: `37442796321` — **FAILED safety-control step**
- artifact ID: `11401926652`
- artifact digest: `sha256:a4bfdf2a66545703b95393bca037d668a421c19c4466072797e76abbeff0bab7`
- candidates tested: **4**
- machine-verified organisations in that run: **0**
- third-party API cost: **$0**

The failure must not be rewritten as a success. The exact TRE FOR EN positive control hit a transient network-unreachable error during that run, causing the workflow assertion to fail.

The useful diagnostic result is nevertheless negative for the hypothesis:

- the SVERRESPLASS Vibbo page still ended at HTTP 302 even with three SSRF-checked redirects;
- YD MASKIN still exceeded the ordinary page-byte ceiling;
- BRAVO SEAFOOD remained rejected.

Decision: **DROP further redirect-ceiling escalation.** Repeatedly increasing redirect depth would add attack/runtime surface without measured recall gain. Vibbo remains evaluator-inaccessible in the bounded path and receives no credit.

### 5c — bounded 1.5 MB page calibration

Branch:

`experiment/v9-bounded-large-page`

Consumed calibration:

- workflow: `37443154952` — PASS
- head: `b0ffe467ea788a2b9c176f2d1658cf7e245541aa`
- artifact ID: `11402041800`
- artifact digest: `sha256:4a39fe77491d1c4fe6b0e1f06ec34654662efef40f72c8a0938822f4fc1363ee`
- candidates tested: **2**
- incremental verified organisations: **0**
- logical site requests: **4**
- conservative request charge: **8**
- third-party API cost: **$0**
- production/default 750 kB byte ceiling changed: **false**
- production/default one-redirect ceiling changed: **false**

The larger bounded fetch showed that `https://yd-maskin.no/` resolves to:

`https://www.facebook.com/yngvedalemaskin`

The destination is therefore a social-network surface, not a first-party company domain. The unchanged verifier correctly kept it non-publishable. The BRAVO SEAFOOD wrong-company control also remained rejected.

Decision: **SHELVE / NO-GO.** Increasing the page-byte ceiling does not recover YD MASKIN as a first-party site.

### Fetch-relaxation conclusion

These screens close the current fetch-relaxation hypothesis:

```text
two redirects:       +0 Gate-A companies
three redirects:     +0; run also had transient positive-control failure
1.5 MB page ceiling: +0; YD resolves to Facebook
```

Do not merge these runtime relaxations into the V9 integration branch. Continue looking for a genuinely new first-party candidate/source for the fifth Gate-A organisation instead.


## Source screen 6 — registry-seeded sitemap nomination

A consumed-only source screen tested whether official BRREG website/email-domain seeds could expose a deeper exact-company page through same-domain robots/sitemap metadata. Sitemap content remained nomination-only and never became company evidence.

Isolated branch:

`experiment/v9-registry-seed-sitemap`

Final hardened screen:

- workflow: `37446354632` — **PASS**
- head: `393b39bfc0a567552b5e6d12222ea025e166dd91`
- frozen Gate-A manifest unchanged
- candidate URLs nominated: **1**
- machine-verified organisations: **0 / 20**
- nomination requests: **24**
- independent verification requests: **2**
- logical requests: **26**
- conservative request charge: **52**
- total bytes: **873,807**
- runtime: **18.129 s**
- third-party API cost: **$0**
- production publications: **0**
- fresh qualification credit: **none**

During hardening, noisy manager/contact-person/location-only sitemap paths were explicitly removed from the ranking logic. The final source remained safe but did not recover a fifth Gate-A website.

Decision: **SHELVE as a primary Gate-A source.** Keep the code and artifact on the isolated experiment branch; do not merge the runtime path into V9 integration.

## Source screen 7 — BRREG subunit homepage nomination

A second consumed-only source screen tested the official BRREG subunit endpoint. Exact parent→subunit relationships were allowed to nominate a subunit homepage only; the relationship itself was forbidden from contributing any parent-company identity evidence.

Isolated branch:

`experiment/v9-brreg-subunit-discovery`

Final screen:

- workflow: `37447133224` — **PASS**
- workflow head: `389c6269c66579e13997deecad8f46c0066dca1d`
- parents with official BRREG subunits: **17 / 20**
- observed subunits: **17**
- parents with subunit homepage candidates: **0**
- candidate URLs nominated: **0**
- machine-verified parent organisations: **0 / 20**
- registry requests: **20**
- site verification requests: **0**
- logical requests: **20**
- conservative request charge: **40**
- total bytes: **23,529**
- runtime: **14.278 s**
- third-party API cost: **$0**
- production publications: **0**
- fresh qualification credit: **none**

This source was structurally clean but sparse: BRREG exposed subunits for most Gate-A parents, yet none of those subunit records supplied a usable homepage.

Decision: **SHELVE as a website-discovery source for this Gate-A cohort.** Do not infer parent website ownership from subunit relation alone.


## Source screen 8 — exact-org OpenStreetMap/Overpass nomination

A consumed-only source screen tested whether public OpenStreetMap objects carrying exact Norwegian organisation-number tags could nominate a first-party website. The experiment batched the 20 frozen parent organisation numbers plus their exact BRREG subunit organisation numbers into one Overpass query. OSM metadata remained nomination-only and was never used as target-company publication evidence.

Isolated branch:

`experiment/v9-osm-orgnr-discovery`

Final diagnostic screen:

- workflow: `37449173244` — **PASS**
- head: `bd65ed37b7a0ad4af946c76f5cac9eed1956a349`
- artifact ID: `11405280045`
- artifact digest: `sha256:09844f2b15c7dd8149467e34616fa93bdf38fefdf23e401fdd55297a492fc4f3`
- parent organisation references: **20**
- exact BRREG subunit references: **17**
- total exact references queried: **37**
- Overpass elements returned: **1**
- candidate URLs nominated: **0**
- machine-verified organisations: **0 / 20**
- BRREG requests: **20**
- Overpass requests: **1**
- site verification requests: **0**
- logical requests: **21**
- conservative request charge: **42**
- bytes: **24,260**
- runtime: approximately **12.6 s**
- third-party API cost: **$0**
- production publications: **0**
- fresh qualification credit: **none**

The only exact-reference OSM object was a BRREG subunit already associated with the PREG BARNEHAGER ÅLESUND path. It exposed an email address but no website field, so it could not nominate a fifth Gate-A website.

Decision: **SHELVE as a primary Gate-A website source.** The source was precise but too sparse. Do not turn OSM organisation tags or BRREG parent→subunit relations into identity proof, and do not depend on the public Overpass endpoint for production without a separate reliability/rights review.


## Source screen 9 — BRREG subunit alias diagnostic

Before spending page-verification requests on subunit-derived trade-name guesses, a consumed-only diagnostic inspected the exact BRREG subunit names for the same frozen Gate-A parents.

Isolated branch:

`experiment/v9-subunit-alias-domains`

Diagnostic:

- workflow: `37450061895` — **PASS**
- head: `65553450df888a1d6026d4df03d7a80af224a2cf`
- artifact ID: `11406306039`
- artifact digest: `sha256:b6cdc6129edacaec0c3d6c4945d8b99776939142b5c63cdf48d267700931e8cd`
- exact BRREG subunits observed: **17**
- parents with distinct alias-domain candidates: **0**
- candidate URLs nominated: **0**
- registry requests: **20**
- logical requests: **20**
- conservative request charge: **40**
- bytes: **23,529**
- runtime: **12.912 s**
- third-party API cost: **$0**
- site verification requests: **0**
- production publications: **0**
- fresh qualification credit: **none**

All observed subunit names collapsed to the parent legal name after removing legal-form/branch/location tokens. There was therefore no genuinely new trade-name label worth independently fetching.

Decision: **DROP the full subunit-alias website screen.** The diagnostic prevented wasting up to forty guessed-domain fetches without weakening identity or consuming fresh data.


## Source screen 10 — NAV Arbeidsplassen job-feed employer homepage

A consumed-only screen tested NAV's official Arbeidsplassen vacancy feed as a structured, exact-employer discovery source. NAV documents the feed as free to use, provides a rotating public experiment token, and exposes employer organisation number and optional homepage in detailed vacancy records. Signalpost retained neither vacancy descriptions nor personal contact data, and NAV metadata remained nomination-only.

Isolated branch:

`experiment/v9-nav-job-feed-discovery`

Final screen:

- workflow: `37452513974` — **PASS**
- head: `b71c3af0c53dd76e9bada9508780793ae38c90e7`
- artifact ID: `11407745223`
- artifact digest: `sha256:6d46fc1561e1f6c0c9fc9fe17b728fd0999f1ea5b36569a369eba40b29705bed`
- feed pages fetched: **38**
- feed items scanned: **368,773**
- feed scan truncated: **false**
- exact normalized legal-name header matches: **4**
- detailed entries fetched: **4**
- parents with homepage candidates: **0**
- candidate URLs nominated: **0**
- machine-verified organisations: **0 / 20**
- logical requests: **43**
- conservative request charge: **86**
- bytes: **181,424,771**
- runtime: **73.446 s**
- third-party API cost: **$0**
- production publications: **0**
- fresh qualification credit: **none**

All four exact-name header matches belonged to the already-known PREG BARNEHAGER ÅLESUND path; the detailed entries exposed no usable employer homepage for a new Gate-A company.

Decision: **SHELVE as a primary Gate-A website source.** The feed is reproducible and rights-compatible but too sparse for this frozen cohort.

## Source screen 11 — EU TED exact-org procurement metadata

A consumed-only screen tested the official EU TED Search API. Each frozen Gate-A organisation number was searched directly, and winner/buyer/business website fields were eligible for nomination only when the same notice lane contained the exact target organisation number. TED metadata was never used as company publication evidence.

Isolated branch:

`experiment/v9-ted-orgnr-discovery`

Final screen:

- workflow: `37453267479` — **PASS**
- head: `8afdd43ac4395a4abf4fe4c4023558b5c2836944`
- artifact ID: `11408181057`
- artifact digest: `sha256:4de1faf958827b3fcf3228800514e52a88c5e14f37b31724408ea48578ba1253`
- TED search requests: **20**
- exact-identifier notices: **0**
- parents with candidates: **0**
- candidate URLs nominated: **0**
- machine-verified organisations: **0 / 20**
- logical requests: **20**
- conservative request charge: **40**
- bytes: **1,620**
- runtime: **30.433 s**
- third-party API cost: **$0**
- authentication: **none**
- production publications: **0**
- fresh qualification credit: **none**

Decision: **SHELVE for this Gate-A cohort.** The source is evaluator-reproducible and precise but produced no exact-identifier procurement records for the frozen companies.


## Provider state

The generic V9 provider gate is implemented on the V9 integration branch. It requires an explicit evaluator-reproducible provider/key path, permitted rights/use, bounded searches, and declared cost before any live provider experiment is enabled.

Current public provider pricing/free allowances do not by themselves satisfy that gate. A free tier is not the same thing as evaluator reproducibility or source-rights approval.

Norid reverse organisation-number/domain lookup remains **rights blocked / shelved** for systematic V9 use.

## Gate-A decision

Current measured machine-verifiable uplift is:

```text
baseline exact websites:       0 / 20
recon-verifiable candidates:  +4 / 20
Gate-A continuation minimum:  +5 / 20
```

Therefore:

**Gate A = NOT PASSED.**

Decision: **RETUNE**, not PROMOTE.

Do not:

- proceed to Gate B 100 as though Gate A passed;
- enable a live search provider without the provider gate;
- lower the exact-company verifier;
- count hosted/brand pages that do not prove the legal entity;
- consume a fresh cohort;
- merge V9 experiments to `main`.

## Exact next action

Continue Website Discovery 3.0 source/provider retuning against this same frozen Gate-A 20. The next source must be able to nominate at least one additional candidate that independently passes the unchanged exact-company verifier, while remaining evaluator-reproducible and rights/cost compliant.

Only after the frozen Gate-A result reaches at least **5 / 20** with **0 wrong-company publications** and **0 evidence defects** should V9 proceed to the consumed/dev 100-company transfer gate.
