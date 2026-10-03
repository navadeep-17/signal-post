# V9 M4 — dated first-party company updates

Status: **HOLD / supporting infrastructure only**

Production V8 remains untouched. This milestone is stacked on V9 M3 and used only previously qualified company websites; no fresh qualification cohort was consumed.

## Objective

Turn M2-discovered company-owned article surfaces into precise dated company updates without treating sitemap/feed metadata or archive pages as publication evidence.

## Publication gate

A company update can be marked publishable only when all of the following hold:

1. the destination remains on the already verified company's registered domain;
2. the URL is a specific article/update page rather than a generic `/news`, `/nyheter`, `/aktuelt`, blog or archive surface;
3. the page has a specific non-generic title;
4. the destination page itself exposes an explicit parseable publication date via matching Article/NewsArticle/BlogPosting JSON-LD or page-level publication metadata;
5. the publication date is not in the future;
6. a bounded destination content hash exists;
7. bounded article/main text exists.

Explicitly **not sufficient** on their own:

- sitemap `lastmod`;
- RSS/Atom entry date;
- discovery labels;
- archive/homepage metadata;
- cross-domain pages.

## M4a offline gate

`src/norway_company_agent/first_party_updates.py` implements the strict qualifier and `tests/test_first_party_updates.py` covers:

- specific dated first-party articles;
- JSON-LD dates/headlines;
- generic archive rejection;
- locale + archive rejection;
- cross-company domain rejection;
- missing destination publication dates;
- future dates;
- optional staleness handling;
- generic title rejection;
- bounded article-text requirement;
- content-hash requirement.

M4b adds `scripts/run_dated_first_party_update_screen.py` and focused screen tests. It reuses M2 for nomination only, independently fetches at most two destination candidates per verified site, re-checks robots and registered-domain boundaries, and then invokes the M4 publication gate.

## Reused-site live screen

Workflow run: `37114794313`

Artifact: `11270489438` (`v9-m4-reused-site-update-screen`)

Exact head: `0013c17600682e2adef2b6ccce2a449111332fd7`

Cohort:

- 9 previously qualified websites;
- the 7 sites reused from V7 release qualification;
- Lucerna and BK Ventilasjon reused from the earlier V7 careers qualification;
- no fresh companies consumed.

Result:

- 9/9 verified sites attempted;
- 5/9 companies produced article discovery candidates;
- 1/9 companies produced a publishable dated first-party update;
- 1 total publishable update;
- 47 observed conservative requests;
- 81 hard request ceiling;
- $0 third-party API cost;
- no production integration.

Qualified example:

- organisation `936618200` — BK Ventilasjon;
- `https://bkventilasjon.no/flik-eiendom/`;
- title: `Flik Eiendom - BK Ventilasjon`;
- page-level publication date: `2025-10-22`;
- date method: Article JSON-LD;
- destination content hash captured and bounded article text present.

Rejected examples behaved as intended:

- generic `/nyheter` and `/aktuelt` archive surfaces were rejected;
- homepage Article metadata was not treated as a company update;
- a generic `Article` title was rejected even though an article-level date existed.

## Decision

**HOLD.**

The strict gate works and produced one real dated company-owned update, but 1/9 company-level yield is not enough to justify adding the M2+M4 request cost to production while verified-site coverage remains sparse.

Keep M4 available as downstream infrastructure. Re-evaluate it after M1 Website Discovery 2.0 materially increases the population of independently verified company websites. A larger website population may make the same precise M4 gate score-positive without weakening precision.
