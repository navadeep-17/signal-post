# V9 M2 structured first-party discovery

Status: **EXPERIMENT / SUPPORTING INFRASTRUCTURE — NOT PRODUCTION-PROMOTED**

Updated: 2026-10-03

M2 tests whether sitemap, RSS/Atom and JSON-LD discovery on an already verified company domain can expose additional first-party news, careers and job surfaces without weakening exact-company identity precision.

## Identity boundary

M2 never discovers or proves the company website itself. A profile is eligible only when the existing website evidence is `available` and its current identity assessment is publishable.

All sitemap/feed/structured-data URLs must remain on the same registered domain as that already verified site. Cross-domain redirects are quarantined and not parsed.

## Publication boundary

Everything produced by M2 is **discovery metadata only**.

- sitemap `lastmod` is not treated as article publication time;
- a `/news` or `/nyheter` archive URL is not a company update;
- Article/NewsArticle JSON-LD is not published without a later destination-page/date validation step;
- JobPosting JSON-LD is not a qualified active vacancy until M3 validates the exact employer, role page and currentness;
- no M2 candidate enters canonical facts directly.

## M2a offline parser gate

Implemented parsers cover:

- sitemap indexes and URL sets;
- RSS and Atom entries;
- declared RSS/Atom links in verified-site HTML;
- Article, NewsArticle and BlogPosting JSON-LD;
- JobPosting JSON-LD;
- conservative news/careers path classification.

The parser gate rejects malformed XML, off-domain URLs and unverified website profiles.

Exact-head Baseline CI for M2a passed the full repository suite, certified 1,000-company canonical audit, frozen submission verifier and refresh checks.

## M2b bounded fetch gate

The experimental runner uses at most five requests per already verified site:

1. robots.txt;
2. homepage;
3. up to two sitemap documents;
4. at most one declared feed.

It uses the existing public-URL/SSRF-safe network boundary and adds a registered-domain redirect check before parsing robots, sitemap, homepage or feed content.

Third-party API cost is $0.00.

## Reused-site development screen

Workflow run: `37113139267`

Artifact: `v9-m2-reused-site-screen`

The screen reused the seven websites already accepted in V7 release qualification run `37107505656`. It did **not** consume a fresh qualification cohort.

Measured result:

- verified sites attempted: 7;
- companies with at least one structured discovery surface: 3/7;
- `news_or_article` candidates: 2;
- `structured_article` candidates: 1;
- structured job candidates: 0;
- careers/job path candidates: 0;
- network requests: 27 / 35 ceiling;
- third-party API cost: $0.00.

Observed candidates:

1. Trysilfjellbooking: sitemap candidate `.../sv/article-0`, with sitemap `lastmod` from 2024;
2. Elviria del Sol: homepage-level Article JSON-LD with no publication date;
3. Effektrevisjon: sitemap `/nyheter` archive surface with an old `lastmod`.

These are **not promoted facts**. The screen demonstrates that the mechanism can discover first-party surfaces, but it does not yet demonstrate enough scoreable dated company updates or jobs to justify production integration on its own.

## Decision

M2 is retained as supporting infrastructure for M3/M4 rather than promoted to the V8/V9 evaluator path now.

Current decision: **HOLD / NO DIRECT PRODUCTION PROMOTION**.

Reason: 3/7 discovery coverage is useful, but the observed candidates still require stricter job/update qualification, and none of the seven sites produced a directly qualified job posting from M2 alone.

Next use:

- M3 may consume verified company careers/job surfaces and linked ATS destinations;
- M4 may consume specific article candidates and require explicit destination-page publication dates;
- future website-discovery gains from M1 can increase the number of domains on which M2 operates.

A low-yield M2 direct-promotion decision is considered successful engineering because it prevents unqualified archive/homepage metadata from inflating public-activity recall.
