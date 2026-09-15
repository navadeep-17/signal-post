# H2a — verified company-declared social profile handles

## Decision

**Promote, subject to final one-command integration regression.** H2a converts a social-profile URL already declared by an exact, publishable company website snapshot into a formal `profile_handle` observation and output-contract claim. It performs no social-platform request and makes no claim about posts, follower counts, engagement, activity, or sentiment.

## Claim boundary

The only H2a claim is:

> The exact verified company webpage declared this social-profile URL at the recorded retrieval time/content hash.

The declaring company page remains the evidence URL. A Facebook, Instagram, YouTube, LinkedIn, X, or TikTok URL is the **claim value**, not the fetched evidence source. H2a does not fetch the social platform.

Publication requires all of the following:

- the company website record is `available` and its entity assessment is publishable;
- organisation number is a valid 9-digit Norwegian organisation number;
- the declaring page has a valid URL, retrieval timestamp, and 64-character content hash;
- the website snapshot contains exactly one captured page, because the current snapshot model does not retain per-social-link page provenance across multi-page snapshots;
- that page URL/hash exactly matches the website evidence URL/hash;
- the existing deterministic social-handle identity assessment is publishable;
- the social URL has a canonical platform/profile shape;
- malformed nested-host artifacts such as `instagram.com/name/www.instagram.com/vendor` are rejected.

## Fresh zero-overlap qualification

Workflow: `H2a Company Social Qualification`

Successful exact-head run: `34953130330` (run #5), head `3476e2089ab95e8e43487f0a9deefa8a52bfc209`.

Independent successful application-equivalent run: `34953103421` (run #4). Qualification artifact ID `10389968812`; ZIP digest `sha256:00e12af41402b3f0952a9966f3e199db021960dfcbbfb270d8090afd8a63c55e`.

All previously used validation cohorts were frozen and checked before fresh selection. H2a excluded **3,100 unique previously touched companies**. The archived successful H1e 300-company exclusion was hash-checked as `5b4c4ae41a01c8b29aefa703bfd754da3e7448b33cbbbcb831d705032ef030b7`.

Fresh selector:

- seed: `20260922`
- count: 300
- excluded rows: 3,100
- overlap: 0
- evaluation split: `h2a_company_social`
- sample slice: `fresh_profile_handle_validation`
- fresh manifest SHA-256: `1d1da002538c0a493303934de53925984c36f641bef2e7623df48897b2e4a88f`

The unchanged production runner completed the fresh 300 before H2a post-processing:

- 300/300 final objects
- 300/300 present in the BRREG bulk snapshot
- production report `passed=true`
- 1,774 observed logical requests
- 3,548 conservative challenge-charged requests
- theoretical ceiling 5,406 for 300 (= **1,802/100**, unchanged)
- wall runtime 193.925 seconds
- third-party API cost: $0
- search API requests: 0
- 17 verified company websites
- contract errors: 0
- budget errors: 0

H2a then produced:

- **10** `profile_handle` observations
- **5** companies with at least one handle
- Facebook: 5
- Instagram: 4
- YouTube: 1
- observation validation errors: 0
- output-contract errors: 0
- added network requests: **0**
- added third-party cost: **$0**
- post-H2a logical requests: unchanged at 1,774
- post-H2a conservative charge: unchanged at 3,548

## Fresh manual audit

Every emitted fresh observation was reviewed. The audit judges the narrow H2a claim — whether the exact company-owned page declares the URL for the target legal entity — not whether the social platform was separately fetched or whether the account is currently active.

| Organisation | Company | Platform | Declared profile | Result | Notes |
|---|---|---|---|---|---|
| 926787527 | YTTERBAKKE AS | Instagram | `instagram.com/Ytterbakke` | Correct | Current exact company site exposes the handle; company identity/address independently corroborated. |
| 926787527 | YTTERBAKKE AS | Facebook | `facebook.com/Ytterbakke` | Correct | Current exact company site exposes the handle. |
| 992407042 | METRO SANDEFJORD AS | Instagram | `instagram.com/metrosandefjord` | Correct | Current exact company site exposes the handle; same legal entity/address independently corroborated. |
| 992407042 | METRO SANDEFJORD AS | Facebook | `facebook.com/metrosandefjord` | Correct | Current exact company site exposes the handle. |
| 922038899 | ZOO COMICS AS | Instagram | `instagram.com/zoocomicsas` | Correct | Current company declaration; independent municipal activity listing corroborates the same Instagram profile and company address. |
| 922038899 | ZOO COMICS AS | Facebook | `facebook.com/zoocomics` | Correct for H2a claim | Current live company-page declaration. An older municipal listing used `facebook.com/zoo.comics`; treat this as an older alias/username, not proof of current platform state. |
| 922038899 | ZOO COMICS AS | YouTube | `youtube.com/@ZoocomicsAndCards` | Correct for H2a claim | Exact live company page declares it; YouTube itself was not fetched. |
| 938433054 | STIFTELSEN FRANSISKUSHJELPEN | Instagram | `instagram.com/fransiskushjelpen` | Correct | Exact first-party page snapshot declares it and the site exposes the exact organisation number. |
| 938433054 | STIFTELSEN FRANSISKUSHJELPEN | Facebook | `facebook.com/fransiskushjelpen` | Correct | Exact first-party page snapshot declares it and the site exposes the exact organisation number. |
| 925400645 | AS TANNLEGE KLOUMAN | Facebook | `facebook.com/TannlegeKloumanAS` | Correct | Current exact company site exposes the handle; legal entity/address independently corroborated. |

Observed fresh manual precision for the narrow declared-handle claim: **10/10 correct (100% point estimate)**. This small sample does **not** prove the hidden challenge's >=95% external precision threshold by itself and is not presented as such.

## Additional precision regression

Applying the extractor offline to the previously audited release artifacts exposed a malformed site-builder social URL for `NUMMER TI AS`:

`https://instagram.com/nummerti/www.instagram.com/webnode_ag`

H2a now generically rejects nested/embedded social hostnames in profile path components. A dedicated regression test prevents this artifact from being published. This is a structural rule, not a company-specific blacklist.

## Cost and request-budget impact

H2a only transforms evidence already captured by the bounded company-site fetch. It performs **zero additional network operations**. Therefore the final structural request ceiling remains **1,802 conservative challenge-charged requests per 100 companies**, and third-party API cost remains **$0**.

## What H2a does not establish

H2a improves formal external-profile coverage, but it does not establish the hidden Builderr qualification gates of weighted external company recall >=60% or coverage >=21/35. It also does not provide social activity, engagement, follower counts, posts, reviews, jobs, or sentiment. Those require separately qualified sources and must not be inferred from a declared profile URL.
