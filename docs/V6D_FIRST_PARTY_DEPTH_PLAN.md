# V6d — Deeper Verified-Site Extraction Plan

## Why V6d now

V6c candidate ranking is a measured NO-GO: both deterministic and local-ML rankers produced zero net-new verified websites on the untouched V6c cohort. V6d therefore does **not** continue guessing domains. It asks a different question:

> Given a website that V5 has already verified as the exact company, can a small bounded first-party crawl unlock materially more high-precision company facts per charged request?

The existing exact-company website identity gate remains authoritative. V6d may deepen an already-verified site; it may never create website identity.

## Hard constraints

- `$0` third-party API spend.
- No search API, browser automation, platform scraping, LLM, or external inference service.
- Same registered-domain pages only.
- Existing verified website must already be `status=available` with `identity_assessment.publishable=true`.
- Robots policy is fetched once per site and reused for all V6d page decisions.
- Bounded deterministic crawl only; no recursive spider.
- Every accepted fact must retain source URL, retrieval time, content hash, and a narrow evidence span/value.
- Generic careers/news indexes never become job/update facts by themselves.
- No result-based company replacement in the validation cohort.

## Controlled crawl

For each already-verified site, V6d may use a bounded sequence:

1. one robots request;
2. one current homepage refetch to recover navigation, JSON-LD, social links, feed links and page-level provenance;
3. optionally one `/sitemap.xml` request;
4. a deterministic set of same-domain section pages, at most one per useful category (`contact/about/team/locations/news/careers`) and subject to the global experiment request budget;
5. at most one specific news/update detail page and one specific job detail page nominated by an already-fetched section page;
6. at most one explicitly declared same-domain RSS/Atom feed.

The experiment runner has a **global added logical-request ceiling**, so even an unusually high verified-site rate cannot break the challenge budget.

## Extractors measured independently

V6d reports the incremental yield from these evidence families rather than blending them into one score:

- same-domain contact email from a retained exact-site page;
- company-declared social profile with deterministic handle identity assessment and per-page provenance;
- structured location from exact-site JSON-LD;
- structured leadership person (`name` + leadership `jobTitle`) only on about/team/leadership pages;
- strict company-owned job detail page using the existing role/apply/detail gate;
- `JobPosting` JSON-LD with a specific title and sufficient job-detail fields;
- strict dated company update using the existing detail-page/date gate;
- dated item from an explicitly declared first-party RSS/Atom feed.

Candidate links, sitemap URLs, rank/order and page category are **not evidence by themselves**.

## Validation design

V6d uses a fresh zero-overlap development cohort selected after excluding all historical cohorts through V6c. V5 runs first on the exact cohort. V6d then runs only on V5-verified sites.

Primary metric:

**net-new accepted decision-useful facts / added conservative request charge**

Also record:

- verified sites available to V6d;
- sites actually crawled;
- facts by extractor and companies covered;
- net-new contacts/socials/jobs/updates;
- structured leadership/location candidates;
- logical requests, conservative charge, bytes and runtime;
- robots blocks, source errors and out-of-domain rejections;
- identity conflicts published (must be zero);
- third-party API cost (must remain `$0`);
- manual audit payload for every fact that would be promoted.

## Promotion gate

V6d is promoted only if all of the following hold on untouched data:

1. measurable net-new high-precision facts are produced;
2. manual audit finds zero wrong-company publications;
3. generic careers/news pages remain excluded;
4. request/runtime cost fits the production evaluator budget with structural headroom;
5. existing V5 contract/identity tests remain green;
6. the gain is material enough to justify the added crawl complexity.

If the experiment yields little or no useful incremental coverage, close it as NO-GO and proceed to V6e NAV jobs / the next weakest-category experiment without weakening evidence rules.
