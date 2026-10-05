# Q4 — Dated first-party activity via RSS/Atom

Last updated: 2026-10-05

Status: **CONSUMED INTEGRATION PASS / PRODUCTION CANDIDATE / FRESH COHORT NOT CONSUMED**

> Sprint terminology note: the qualification plan originally labels social/contact as Q4 and dated first-party activity as Q6. This branch retained its working name `Q4 first-party feed activity`; semantically, the promoted mechanism is the new bounded dated-activity path for the Q6 gap.

## Why this milestone exists

The consumed Phase-11 evaluator-shaped output before this change had:

- 100 companies;
- 6 exact verified company websites;
- social coverage on 4 of those 6 sites;
- 0 `external.job_posting` claims;
- 0 `external.company_update` claims.

Social parsing was therefore not the immediate bottleneck. Dated first-party public activity remained structurally zero even though Builderr scores public activity inside recall/coverage.

This milestone tests and integrates a strict RSS/Atom path for already verified company-owned domains. A qualifying feed can provide a title, article URL and publication/update date in one bounded same-site snapshot.

## Safety boundary

The feed path does not discover company identity.

A feed-backed update is eligible only when:

1. the company already has a website that passed the current exact-company identity gate;
2. the feed URL remains on that verified site;
3. each retained entry URL remains on that verified site;
4. the entry has a specific title;
5. the entry has an explicit RSS/Atom date;
6. the feed fetch obeys current public-URL, redirect and robots safety rules;
7. retained feed provenance is revalidated before final contract projection.

Cross-domain entries, undated items, generic section titles, invalid hashes, mismatched retained website URLs and malformed dates are discarded.

The RSS/Atom snapshot itself is the cited evidence source. An article URL observed inside the feed is never represented as independently fetched unless another collector actually fetched it.

## Consumed screen result

The screen reused the already-consumed Phase-11 owner-veto replay (`37314396820`). It did not touch a new company cohort.

For each of the six exact verified websites, the screen tried at most two deterministic feed candidates (`/feed/` and `/rss.xml`). The first valid feed with dated same-site entries stopped further attempts for that company.

Measured result:

- verified sites screened: **6**;
- sites with valid dated feed activity: **1/6**;
- dated same-site entries retained: **5**;
- screen logical requests: **22 / 24 hard ceiling**;
- wrong-company/cross-domain publications: **0**;
- positive company: `PUBSPILL AS` (`936252494`);
- accepted feed: `https://www.pubspill.no/feed`;
- accepted feed snapshot SHA-256: `89f2f1cd5cc9f7bad33ea6a5808861b67309eb00368375db436c53272edce22a`.

Screen workflow:

- run: `37332237813`;
- artifact: `11354278409`;
- artifact digest: `sha256:0084c12819ed9120d6d65d5ea27e750563af6ec37497a17dafc0392cc87e4914`.

## Production integration

Production uses the already-proven spare site-request allocation rather than adding a new unconditional request family.

Rules:

- unresolved companies keep H1g website recovery priority;
- a company whose website is already exact-verified may attempt the feed only when two of the existing four site-request slots remain;
- production tries only `/feed/`, the consumed-screen winner, so robots + feed GET fits the two-request spare slot;
- a website newly recovered by H1g does not receive an additional feed attempt in the same run;
- maximum site logical requests per profile remains **4**;
- the zero-network V8 postprojection publishes strict feed-backed `external.company_update` claims, then rebuilds canonical projection, synthesis and product output and revalidates each layer.

No production request ceiling, identity threshold, third-party source or publication semantics outside the new typed company-update path are weakened.

## Consumed V8 integration result

The full V8 evaluator was replayed over the same already-consumed 100-company Phase-11 cohort.

Result:

- companies: **100/100 terminal**;
- final report: **PASS**;
- feed-backed `external.company_update` claims: **5**;
- companies with feed-backed dated activity: **1**;
- positive company: **PUBSPILL AS**;
- observed logical requests: **694**;
- observed conservative challenge charge: **1,388 / 2,000**;
- theoretical conservative challenge ceiling: **2,000 / 2,000**;
- maximum site logical requests/profile: **unchanged at 4**;
- third-party cost: **$0.00**;
- contract validation: **PASS**;
- canonical validation: **PASS**;
- synthesis validation: **PASS**;
- product/workspace rebuild: **PASS**.

Integration verification:

- exact measured code head: `5fcad2fbc9f3850e0896c1eea514ade71c08d681`;
- Baseline CI: `37334838722` — **PASS**;
- consumed V8 integration workflow: `37334830712` — **PASS**;
- artifact: `11356971290`;
- artifact digest: `sha256:9163614a5661ea14a139c79144a179e0fa8c089e982c96599cc5059504f1daa4`;
- fresh qualification cohort consumed: **no**.

## Decision

**GO for production promotion.**

The path creates a real dated-public-activity signal where the consumed baseline had none, preserves exact-company publication rules, keeps the structural 2,000-request theorem unchanged, costs $0 in third-party APIs and survives full consumed evaluator integration.

This is not sufficient evidence to spend Q8 by itself. The next sprint action remains Q7: compare the complete current bundle against the pre-change consumed baseline and other surviving candidates before deciding whether transfer is materially strong enough for a fresh qualification cohort.
