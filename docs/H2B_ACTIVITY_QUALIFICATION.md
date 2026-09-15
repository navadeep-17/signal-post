# H2b — company-owned dated activity qualification

Date: 2026-09-15

## Decision

**Do not promote H2b into the production runner.**

H2b tested whether an already-qualified exact company website could expose a same-domain news/blog/activity page with explicitly dated items. The extraction path was precise and zero-cost, but fresh-company recall gain was too small to justify production complexity or request-budget use.

The experimental branch remains available for reference:

`experiment/h2b-company-activity`

No H2b production code was merged.

## Claim boundary

The only experimental claim was:

> A verified company-owned activity listing page explicitly listed this titled item with this publication date at the recorded retrieval time/content hash.

H2b did **not** fetch article bodies, infer sentiment, infer business impact, or treat undated content as activity.

Candidate activity pages had to be explicitly linked by the company homepage. H2b did not synthesize guessed `/news`, `/blog`, or `/nyheter` paths. Cross-domain redirects abstained.

## Fresh zero-overlap qualification

Workflow: `H2b Company Activity Qualification`

Successful run: `34966322464`

Qualified branch head:

`cb8ddb072927d07d1dec38156276f372bdbab645`

Artifact:

- ID: `10395726782`
- digest: `sha256:281a67d1468861a50934bc33e3dc2bd3fdb967f444ba596c8c36dca1be0a3bda`

Before selecting the H2b cohort, the workflow reconstructed and hash-checked all prior non-heldout/touched cohorts. It excluded **3,400 unique companies**.

Fresh H2b cohort:

- seed: `20260923`
- count: 300
- excluded rows: 3,400
- overlap: 0
- evaluation split: `h2b_company_activity`
- sample slice: `fresh_dated_company_activity_validation`
- fresh manifest SHA-256: `0bff58af0b8535e71c677dbe44c873a7dfe63805839eb72044896577e1c968dc`

The unchanged production runner completed the fresh 300 before the experimental H2b probe. Production behavior was asserted identical to `main` for the final runner, final site discovery, Wikidata discovery, output contract and external contract.

## Measured result

Fresh production baseline:

- 300/300 companies completed
- 3,540 conservative challenge-charged requests
- structural production ceiling remained 5,406/300 = **1,802/100**
- third-party API cost: $0

H2b eligibility and yield:

- 31 verified company websites
- 31/31 were promotion-compatible with the existing four-logical-request site ceiling
- 31 companies experimentally probed
- 24: no declared activity link
- 5: declared activity page but no qualifying explicitly dated items
- 1: activity page unavailable
- **1: qualifying dated activity**
- **5 dated activity observations total**
- 76 logical requests used by the experimental benchmark probe
- third-party API cost: $0
- observation validation errors: 0

The company-level gain was therefore:

- **1/300 = 0.33%** of the fresh cohort
- **1/31 = 3.23%** of verified-company-site profiles

That is too small to materially improve the challenge's primary risk: weighted external-company recall.

## Manual precision audit

The sole fresh company producing observations was:

- CHIIJE AS
- organisation number: `925360090`
- verified website: `https://chiije.com/`
- activity page: `https://chiije.com/blogs/journal`

The exact legal entity was independently corroborated through Chiije's own legal/privacy information, which names CHIIJE AS and organisation/trade number 925360090. The fetched company-owned journal produced five explicitly dated entries. One sampled live article was independently checked against the first-party site.

The observed H2b output therefore appeared precise under the narrow listing claim, but precision was not the limiting factor. Recall/yield was.

## Request-budget interpretation

The benchmark intentionally refetched the homepage plus one activity page so H2b could be measured without changing production code. That cost up to four experimental logical requests per eligible company.

A theoretical production integration could avoid the homepage refetch by capturing activity navigation during the already-paid homepage fetch and using only two remaining site requests for the activity page. In this fresh cohort all 31 verified sites had exactly that headroom, so H2b could have been integrated without raising the structural 1,802/100 ceiling.

We still do **not** promote it because the measured company-recall gain is only 0.33%.

## Related careers result

The earlier `feature/company-careers-signals` experiment is also not worth reviving as-is. Its frozen-100 audit (`34857612452`) had:

- 6 verified sites entering the careers extractor
- 11 additional careers requests
- **0 publishable observations**
- $0 third-party API cost

This reinforces the current conclusion: deeper crawling of the small verified-site subset is precise but does not solve the broad external-recall gate by itself.

## Follow-up

Do not spend further production complexity on H2b unless new evidence materially changes its population reach.

The next experiment must target a source with substantially broader company coverage than the current verified-site subset. The project should continue respecting the $0 third-party API policy unless that decision is explicitly changed.