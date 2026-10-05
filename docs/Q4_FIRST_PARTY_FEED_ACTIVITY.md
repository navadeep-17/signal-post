# Q4 — Dated first-party activity via RSS/Atom

Last updated: 2026-10-05

Status: **CONSUMED-ONLY EXPERIMENT / PRODUCTION DISABLED / FRESH COHORT NOT CONSUMED**

## Why this milestone exists

The current consumed Phase-11 evaluator-shaped output has:

- 100 companies;
- 6 exact verified company websites;
- social coverage on 4 of those 6 sites;
- 0 `external.job_posting` claims;
- 0 `external.company_update` claims.

This means social parsing is not the immediate bottleneck. Dated first-party public activity remains structurally zero even though Builderr explicitly scores jobs and public activity inside recall/coverage.

Q4 tests whether an already verified company-owned domain exposes a strict RSS/Atom feed that can provide a title, article URL and publication/update date in one bounded same-site snapshot.

## Safety boundary

Q4 does not discover company identity.

A feed is eligible only when:

1. the company already has a website that passed the current exact-company identity gate;
2. the feed URL remains on that verified site;
3. each retained entry URL remains on that verified site;
4. the entry has a specific title;
5. the entry has an explicit RSS/Atom date;
6. the feed fetch obeys current public-URL, redirect and robots safety rules.

Cross-domain entries, undated items and generic section titles are discarded.

## Consumed screen

The screen reuses the already-consumed Phase-11 owner-veto replay (`37314396820`). It does not touch a new company cohort.

For each of the six exact verified websites, it tries at most two deterministic feed candidates:

1. `/feed/`
2. `/rss.xml`

The first valid feed with dated same-site entries stops further attempts for that company.

Maximum screen cost:

- 6 verified sites;
- 2 candidate feeds/site;
- robots + feed GET = 2 logical requests/candidate;
- hard screen ceiling = 24 logical requests.

This is an experiment-side screen only. The production evaluator request theorem remains unchanged.

## Promotion gate

### Continue toward integration only if

- at least one consumed exact verified site produces a valid dated same-site feed entry;
- 0 cross-company/cross-domain publications;
- all accepted entries carry exact feed URL, retrieval snapshot hash, date and supporting title/date span;
- full Baseline CI remains green.

### Hold/drop if

- yield is 0/6 on the consumed verified sites; or
- feeds are mostly blocked, cross-domain, undated or generic; or
- the gain would require weakening exact-company identity or date evidence.

If Q4 is positive, the next step is a separate production-integration milestone that fits one feed request into the existing per-company request allocation and projects accepted entries through the existing `external.company_update` contract. If Q4 is zero-yield, move to the next external-recall family instead of tuning against the same six websites.
