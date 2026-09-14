# H1c — deterministic zero-cost domain discovery

## Goal

Recover a small amount of missing company-site coverage without a search API, paid API, or external discovery provider.

H1c is a fallback after registry website handling and H1a registry-email-domain discovery. It does **not** replace exact-entity verification.

## Candidate generation

For a company with no already verified website, generate at most two `.no` candidates from the distinctive legal-name tokens:

1. compact legal-name form, e.g. `mastersurgerysystems.no`;
2. hyphenated legal-name form, e.g. `master-surgery-systems.no`.

No fuzzy search, typo expansion, broad acronym generation, keyword search, or paid provider is used.

## Fetch budget

Candidate discovery uses a homepage-only fetch path:

- SSRF/public-address checks from the starter;
- robots.txt check;
- one bounded HTML homepage request;
- no secondary-page crawl during the discovery attempt;
- default timeout 6 seconds;
- maximum two candidates/company;
- third-party API cost: `$0`.

A candidate that does not resolve creates no company claim.

## Publication guard

A guessed/resolving domain is never evidence by itself.

The candidate must first pass the starter's ordinary website identity gate. H1c then requires independent page-level proof:

- exact 9-digit organisation number on the fetched page; **or**
- complete distinctive legal name on the fetched page plus a company-compatible final domain or registry-location corroboration.

If a guessed candidate redirects to an unrelated parent/portfolio domain, the original guessed domain cannot be used to justify publication. The **final** domain or registry location must corroborate the legal identity.

Generic/parked pages, namesake pages, parent-company mentions, and unresolved candidates remain quarantined.

## Evaluation

The first live experiment uses the same frozen 100-company development corpus as the baseline and H1a benchmark:

`51a96f25f79532b9ba285304d540887e0f17410907909dbe6c85c0b41b8341d3`

Run order:

`official baseline -> H1a -> H1c`

The audit records:

- exact website count before/after H1c;
- candidate attempts;
- HTTP requests;
- latency;
- wall runtime;
- every promoted organisation/domain;
- combined request count;
- third-party API spend, which must remain exactly `$0`.

No H1c promotion is production-qualified solely because an automated gate labels it exact. Every promoted domain from the frozen audit must be manually checked before merge/integration.

The final 200-company held-out release corpus remains untouched.
