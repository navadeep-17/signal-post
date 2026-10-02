# V6d — Verified-Site Depth Decision

## Decision

**NO-GO for the bounded multi-page crawl as a production feature.**

V6d proved that exact verified sites can unlock real first-party facts, but the unseen transfer result is too small for the additional network/runtime/implementation cost. The exact-company identity gate remains unchanged and production `main` is not modified by this experiment.

A narrower zero-network follow-up is justified: two of the three unseen-transfer gains were social profiles already present in the retained V5 homepage evidence and can be recovered without any additional HTTP requests. That follow-up must be implemented and qualified separately on a new untouched cohort.

## Development cohort

Consumed/tuning cohort:

- 100 companies
- historical exclusions before selection: 7,520
- overlap: 0
- cohort SHA-256: `9256a2c823bb8a02ca1a0a3bf4cc5f168077ac5728e60a46efd9fe79ec25c73c`
- exact V5 verified sites: 10

After hardening stale/default RSS posts and page prioritization:

- added logical requests: 49
- added conservative request charge: 98
- added wall time: 37.213 s
- net-new candidate facts: 7
- companies with new contacts: 2
- companies with new socials: 1
- companies with new jobs: 1
- companies with new updates: 1
- third-party API cost: $0
- identity conflicts published: 0

This cohort was used for hardening and is not validation evidence.

## Unseen transfer qualification

Workflow run: `36978734059`

Artifact: `v6d-first-party-depth-transfer`

Artifact digest: `sha256:37c6d48ac571a42e6b37db604c85dfbb17de5e3614efeb51722d16c0f13c9a2c`

Cohort:

- 100 companies
- historical exclusions: 7,620
- overlap: 0
- seed: `20261012`
- cohort SHA-256: `536b55977b2d6b7b996d397ceb7ad8c3773f7a7c5a7c33bfd633731ff3646ea7`

V5 incumbent on the exact same cohort:

- exact verified websites: 5 / 100
- descriptions: 100 / 100
- workforce: 100 / 100
- revenue: 83 / 100
- current roles: 100 / 100
- registered locations: 75 / 100
- contact-email companies: 3 / 100
- social-profile companies: 1 / 100
- strict jobs: 0 / 100
- strict company-authored updates: 0 / 100
- registry-change companies: 100 / 100
- observed conservative challenge charge: 1,376 / 2,000
- runtime: 444.09 s
- contract validation: PASS
- third-party API cost: $0

Hardened V6d challenger:

- exact verified sites eligible: 5
- sites crawled: 5
- added logical requests: 31
- added conservative request charge: 62
- combined conservative charge: 1,438 / 2,000
- added wall time: 21.428 s
- bytes added: 4,548,634
- net-new candidate facts: 3
- social-profile companies added: 2
- company-update companies added: 1
- contact companies added: 0
- job companies added: 0
- leadership companies added: 0
- location companies added: 0
- outside-domain publications: 0
- identity conflicts published: 0
- third-party API cost: $0

The three transfer candidates were:

1. MENTI VERDI AS (`931395726`) — Instagram `https://instagram.com/mentiverdi`, declared in exact-site Organization JSON-LD `sameAs`.
2. A-MEMBRAN AS (`998823951`) — Facebook `https://facebook.com/amembran`, explicitly linked by the exact verified homepage. The exact homepage also displays A-Membran AS and its registered Oslo address.
3. KIRKENS NØDHJELP / NORWEGIAN CHURCH AID (`951434353`) — dated first-party update `Kirkens Nødhjelp i media: Uke 39`, dated 2026-09-28 on the exact verified company-owned news path.

No candidate depended on search-result evidence, a guessed third-party identity, or a social-platform fetch.

## Why the full crawl is rejected

The primary optimization target is scoring-relevant accepted facts per charged request, not raw extraction volume.

Transfer efficiency was only:

`3 / 62 = 0.0484 net-new candidate facts per conservative request`

More importantly, **two of the three transfer gains do not require the deep crawl at all**:

- V5 already retained the Menti Verdi Organization JSON-LD containing Instagram `sameAs` on the exact homepage.
- V5 already retained the A-Membran homepage social-link assessment as publishable, but the legacy H2a projector abstained because a secondary identity page caused the retained page count to exceed one.

The current final website collector does not merge social candidates from the secondary identity page; those social candidates originate from the already-fetched homepage. Therefore a source-specific, per-homepage provenance recovery can capture these social facts with **zero additional network requests**.

Once those two zero-network facts are removed from the V6d transfer gain, the multi-page crawl itself contributed only one new company-authored update on the unseen 100 while adding 31 logical HTTP requests and 21.428 seconds.

That is below the project's production complexity/yield threshold and does not address the central verified-website bottleneck.

## Next experiment

Build a separate zero-network social recovery challenger from current V5 retained evidence:

1. exact V5 website identity must already be publishable;
2. only current final-site source types are eligible;
3. recover already-assessed homepage anchor social links even when a separately retained identity page makes `pages > 1`;
4. recover social `sameAs` links from retained homepage Organization JSON-LD;
5. run the existing deterministic social-handle identity gate;
6. persist exact homepage URL/hash provenance for every recovered handle;
7. add **zero** network requests and **zero** third-party cost;
8. qualify on a new unseen cohort excluding both V6d development and V6d transfer companies.

If that zero-network path transfers, promote only it. Do not merge the V6d multi-page crawler.
