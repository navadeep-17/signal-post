# H1c secondary identity hardening

## Why this change exists

The first zero-overlap 300-company validation (`34926276014`) audited 25 published websites and found one wrong-company publication: `OSLO MIKROSEMENT AS` (`933200353`) was mapped to `oslomikrosement.no`. The exact legal entity instead publishes `oslomikrosement.com` with its Hagan address and organisation number.

The failure was generic: for a multi-token legal name, a guessed `.no` domain could pass on full-name-in-page plus matching title/domain even when neither the exact organisation number nor a BRREG location was present.

## Hardening

The final evaluator now treats that weaker H1c path as provisional.

A deterministic H1c candidate is still immediately publishable when the independently fetched homepage contains:

- the exact target organisation number, or
- registry-location corroboration.

Otherwise a title/domain-only match must earn stronger proof from one bounded same-domain identity page. Candidate links are limited to contact/legal/privacy/about-style paths discovered on the homepage. The secondary page must contain either the exact organisation number or BRREG location evidence. If no suitable link exists, the page does not corroborate the entity, or two logical site requests are no longer available, publication abstains.

The site request ceiling remains `4` logical requests per company. The final 100-company structural ceiling therefore remains `900` logical / `1800` conservative redirect-charged requests.

## Regression tests

`tests/test_h1c_secondary_identity.py` covers:

1. a legal-name/domain homepage with a secondary page that does not match BRREG identity -> quarantine;
2. the same weak homepage with a secondary page matching the registered location -> publish;
3. a weak H1c candidate when an earlier probe has consumed the secondary-page budget -> abstain rather than exceed the request ceiling.

Baseline CI at qualification head `b962b6893e7f9d5e413e5536e5f81217e0c69a32` passed `183 tests + 5 subtests`, including deterministic refresh replay.

## Known-300 regression replay

Workflow: `H1c Secondary Identity Qualification`

Run: `34928483107`

The previously audited 300-company corpus was replayed only as a regression set. The workflow explicitly asserts that org `933200353` no longer publishes `oslomikrosement.no`.

Result:

- known false positive quarantined: **PASS**;
- one-command evaluator: **PASS**;
- canonical verified sites: `16` (down from `25` in the pre-hardening live run);
- H1c sites: `4` (down from `13` in the pre-hardening run);
- registry-email sites: `3`;
- registry-linked sites: `9`.

This is a substantial recall reduction. Some of the difference is live-network variability, but the hardening intentionally drops weak title/domain-only evidence that cannot obtain stronger identity proof.

## Fresh disjoint confirmation corpus

The confirmation sample is not the known 300. It excludes both:

- the original 1,000-company manifest, and
- all 300 companies used to find the Oslo Mikrosement failure.

Selection:

- seed: `20260916`;
- excluded previous companies: `1300`;
- fresh companies: `300`;
- overlap: `0`;
- fresh corpus SHA-256: `7c0d1ae4355edf1e2b282ebc386b7874eb6c3cbc36e5b01f0685069cbcd38d83`.

Fresh run result:

- 300/300 unique completed outputs;
- evaluator run: **PASS**;
- 1,739 logical requests;
- 3,478 conservative challenge-counted requests (`1,159.333` per 100);
- wall runtime: `207.718` seconds;
- third-party API cost: `$0`;
- search API requests: `0`;
- contract errors: `0`;
- budget errors: `0`;
- verified websites: `15`;
- source mix: `9` H1c + `6` registry-linked;
- H1c sites using secondary proof: `2`.

Qualification artifact digest: `sha256:7e3c79c2676937d41ac1a6bd160a9fc4981b0de264aae0d09ee2fa36218ef9ee`.

## Fresh manual precision audit

Every published site in the fresh 300 was manually checked against the legal entity anchored by organisation number and BRREG address/municipality. Exact organisation-number pages, official registry website mappings, company-owned legal/contact pages and independent Norwegian public/business records were preferred.

| Org | Company | Published site | Source | Result | Audit basis |
|---|---|---|---|---|---|
| 998052343 | EGGEN ANLEGGSDRIFT AS | `eggenanleggsdrift.no` | H1c | correct | Published site identifies Eggen Anleggsdrift in Hernes/Elverum; independent business records match exact org `998052343`, Sagene Ring 43, Hernes and the same company identity. |
| 981391209 | MEDIEBEDRIFTENES LANDSFORENING | `mediebedriftene.no` | registry | correct | Company contact page and independent NHO records map exact org `981391209` and Oslo address to the domain. |
| 992414537 | INTRO MUSIC AS | `intromusic.no` | registry | correct | Independent company listing maps exact file/org `992414537`, Intro Music AS and Trondheim contact identity to `intromusic.no`. |
| 915267351 | ARRIVA CHARTERING AS | `arrivashipping.no` | registry | correct | Multiple independent Norwegian company records map exact org `915267351` / Arriva Chartering AS to `www.arrivashipping.no`; the company is part of the Arriva Shipping group. |
| 971500719 | NYBU BARNEHAGE STI | `nybu.barnehage.no` | registry | correct | Public structured records map org `971500719` to the official website and the Lillehammer kindergarten identity. |
| 934973305 | HELHJERTET JOBB AS | `helhjertetjobb.no` | H1c | correct | Company site publishes exact legal name and Vangensteinvegen 6 B, Rælingen; independent company records map org `934973305` to the same domain/location. |
| 918321136 | TRYSIL HELSE OG TRENING AS | `trysilhelseogtrening.no` | H1c | correct | Company site publishes Storvegen 6, Trysil; Trysil municipality independently links the same site/contact identity for Trysil Helse & Trening, while registry records confirm org `918321136` at that address. |
| 933550656 | NORDIC SUN AS | `nordicsun.no` | registry | correct | BRREG directly lists `www.nordicsun.no` for exact org `933550656`, Heggelia 35, Fetsund. |
| 913348648 | SYDENG CONSULTING AS | `sydengconsulting.no` | H1c | correct | Company site itself publishes exact org `913 348 648` and Toresvei 17, Gamle Fredrikstad. |
| 920280242 | CUBE8 GALLERY AS | `cube8gallery.no` | H1c + secondary | correct | Same-domain gallery page publishes exact org `920280242` and Toldbodbrygga 1, Fredrikstad; independent BRREG-derived records match. |
| 922858519 | SELBÆK MASKIN AS | `selbaekmaskin.no` | H1c | correct | Company homepage publishes exact org `922858519` and Lefstadvegen 96, Fannrem; public procurement records independently confirm the exact entity/address/contact. |
| 967852546 | LILLE LONDON AS | `lillelondon.no` | H1c | correct | Independent business records map exact org `967852546`, Carl Johans gate 10, Trondheim and the domain. |
| 924600497 | BLUE ANALYTICS AS | `blueanalytics.no` | H1c + secondary | correct | Company privacy/contact material publishes exact org `924 600 497` and Kong Christian Frederiks plass 3, Bergen; Norwegian Accreditation and Mattilsynet independently map the same company/address/domain. |
| 979747276 | VEST AUTO AS | `vestauto.no` | H1c | correct | Site publishes Rådhusvegen 43, Nordfjordeid; Finanstilsynet confirms exact org `979747276` at that address and Kia independently lists the same dealer/address. |
| 933321177 | TECHSTONE NORDIC AS | `techstone.no` | registry | correct | BRREG-derived/independent company records map exact org `933321177`, Hoffsveien 13, Oslo to `techstone.no`. |

Fresh audit result:

- audited promotions: `15`;
- correct: `15`;
- wrong-company publications: `0`;
- observed point precision: `100%`;
- approximate two-sided 95% Wilson interval: `79.6%–100%`.

**This does not prove the competition's hidden >=95% external-precision threshold.** The fresh sample contains too few published sites for a statistically comfortable lower bound. It is sufficient as a merge gate for this bounded precision hardening because the known generic failure is regression-covered, the fresh corpus has zero overlap with all 1,300 prior companies, and no new wrong-company failure was found.

## Merge decision

**MERGE the precision hardening if final branch-head CI remains green.**

Do not recover the lost recall by weakening this identity rule in the same PR. Recall recovery should be a separate experiment, for example bounded footer/legal identity extraction or safe preservation of query-based same-domain contact URLs, followed by another new disjoint validation corpus. A Wikidata `P2333` organisation-number -> website candidate experiment is another separate $0 option; any Wikidata URL remains candidate discovery and still requires independent page verification.
