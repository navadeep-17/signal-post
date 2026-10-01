# V6b — search-assisted verified website discovery

Date: 2026-10-02

Status: **EXPERIMENT ONLY — not submission-qualified**

This experiment follows the public-competitor teardown in `V6_PUBLIC_COMPETITOR_TEARDOWN.md` and the no-go result of PR #45. The deterministic `.com` fallback produced **0 net-new websites on a fresh zero-overlap 50-company cohort** while adding 18 logical requests / 36 conservative request charge, so it was rejected.

The next hypothesis is narrower and stronger:

> Search can nominate a domain that deterministic spelling rules cannot find, but search output can never prove the company. Only an independently fetched page can do that.

## Why test this next

Several public Signalpost implementations widen website nomination before first-party extraction. The clearest architecture is AnSa30-06/signalpost-norway:

```text
registry site
  -> registry email domain
  -> deterministic domains
  -> search fallback for unresolved companies
  -> independently fetch candidate
  -> exact-company identity gate
  -> first-party extraction
```

The important lesson is not to copy its thresholds. Its public remediation history shows that name/domain/place evidence can publish the wrong company. Search therefore gets a deliberately stricter publication gate here.

A verified site is a multiplier because it can later unlock description, same-site contacts, company-declared social profiles, structured jobs, dated news, RSS/sitemap activity, leadership and extra locations. None of those downstream facts are enabled in this experiment yet; V6b first tests whether search materially increases **verified website coverage**.

## Provider and cost

The first adapter is Brave Search API because it exposes ordinary web results suitable for candidate nomination.

Public Brave pricing checked 2026-10-02:

- Search plan: **$5 / 1,000 requests = $0.005/query**.
- Brave advertises $5 monthly credits, but we declare the list-price marginal cost rather than treating credits as zero cost.
- One V6b development attempt uses at most one Brave query per unresolved company.

A 40-company first screen therefore has a maximum declared search charge of **$0.20**, before any future production integration.

Important reproducibility caveat: Builderr's current challenge page says evaluator runs cannot depend on a credential tied to the entrant's own account on another service. Therefore a Brave-backed path is **not submission-ready merely because it fits the dollar budget**. Before production use, Builderr must confirm an evaluator-reproducible server-side key/provider arrangement. Until then this remains an architecture/coverage experiment.

## Data boundary

Search results are transient nomination data only.

Never persisted as company evidence:

- raw Brave JSON;
- result title;
- result snippet;
- result rank;
- plaintext query.

Persisted operational audit fields may include:

- provider name and endpoint;
- SHA-256 of the query;
- provider status and result count;
- whether one result was selected for an independent fetch;
- declared provider cost;
- the independently fetched page URL only after that fetch occurs.

The company website evidence is always the independently fetched page, never the search response.

## Candidate nomination

One query only in the first screen:

```text
"<exact legal name>" <organisation number> <municipality>
```

The existing transient candidate scorer can nominate a result when either the hostname strongly aligns with the legal name or exact organisation-number + full-name search evidence makes an acronym/brand homepage worth fetching. This is deliberately a **crawl gate, not a publication gate**.

Directory, registry, social, marketplace and aggregator hosts are blocked before nomination. Only one domain is independently fetched per company in V6b.

## Independent publication gate

After search nomination, the destination is fetched with the existing SSRF-safe, robots-aware bounded homepage fetcher. Search fields are discarded before identity publication.

A search-nominated page publishes only through one of two routes:

1. **Exact target organisation number on the fetched page**, with **no explicitly labelled different organisation number** on the captured page; or
2. **Legal company name in a site-owner identity position** (title, structured organisation identity, footer/legal/contact identity text) **plus a strong BRREG address pair**:
   - exact street expression including house number; or
   - postcode + postal town together.

Explicitly insufficient:

- legal name + municipality/place only;
- legal name + bare postcode;
- legal name + guessed/exact-name hostname;
- name token similarity;
- search snippet or rank;
- target company mentioned only in ordinary body text;
- a page that also explicitly identifies another organisation number.

This directly guards the public failure classes documented by competitors: group sites, parent/holding pages, company directories, chain portals, multi-company pages and the `THE FJORDS DA -> fjords.com` place-name collision.

## Request budget for the first screen

Per attempted unresolved company:

- Brave query: 1 logical request;
- independent site verification: normally robots + homepage = up to 2 logical requests.

Worst case: **3 logical requests** or **6 conservative request charge** under the V5 multiplier of 2.

The default 40-company experiment therefore caps itself at 300 added conservative requests and $1 provider spend. The intended fresh-50 benchmark should combine this with the observed V5 baseline request charge and remain below the 50-company proportional ceiling used in the benchmark workflow.

Production integration is a later decision. If search qualifies, the final runner should allocate search from actual remaining global budget first and let annual-report OCR consume only the remaining headroom, rather than increasing the structural 2,000-request ceiling.

## Qualification protocol

V6b may advance only if all of these hold on fresh zero-overlap companies:

1. V5 baseline and V6b use the exact same cohort.
2. Search produces a meaningful positive delta in verified websites.
3. Every net-new website is manually reviewed against the target organisation number and registry identity.
4. Zero wrong-company promotions.
5. No weakening of V5 registry/email/deterministic website behavior.
6. Added requests, runtime and declared provider cost stay within headroom.
7. Search result content never enters claim evidence.
8. A second zero-overlap transfer cohort reproduces the gain before production integration.
9. Builderr confirms evaluator-reproducible provider credentials before any submitted version depends on Brave.

If website gain is weak, V6b is dropped and the next independent experiment is NAV jobs with exact BRREG subunit -> parent mapping. If website gain is strong, the next test is bounded first-party deep extraction (JSON-LD, sitemap/RSS, targeted contact/about/team/news/careers pages) on the newly verified sites.

## Files

- `src/norway_company_agent/search_verified_discovery.py` — provider-independent nomination filtering and strict fetched-page publication gate.
- `scripts/run_brave_verified_discovery.py` — one-query Brave experiment with cost/request accounting and provider-content-free audit output.
- `tests/test_search_verified_discovery.py` — wrong-company and evidence-boundary regressions.
- `.github/workflows/v6b-search-assisted-development.yml` — fresh zero-overlap development benchmark, live only when a Brave key is configured.
