# M32 — Offline-only company-site crawl-nomination challenger

**Decision:** SYNTHETIC TESTS ONLY / NO LIVE SEARCH / NO SCORE CLAIM / DO NOT MERGE.

Base: the unchanged M26 development pilot at commit `649aa9dcb0ceecf5947d2271ee846b0dc9d76e13`, itself descended from qualified V8 `200f056a5a60cad23610a3958b6bec62dfb624a5`.

## Problem actually established by M28 / M31

The previously consumed 20-company private development pilot completed without recorded provider errors, but yielded zero sites eligible for manual audit. Encrypted report analysis (M31 jobs `37873262921` and `37873331600`) showed:

- **17/20** ended in `no_candidate_qualified_for_independent_fetch`, meaning no search result passed the baseline crawl-selection gate; **this does not prove that the search provider returned zero URLs**.
- **3/20** fetched first-party pages and then failed the original M23 independent legal-entity identity gate (`first_party_identity_rejected`).
- **0/20** failed exclusively on M26's extra exact-nine-digit-number page requirement or site unavailability.
- **0** qualified sites, zero new published company claims. No fresh/company-cohort or official Builderr score was measured.

The M28 report omitted raw result lists, titles, snippets and queries; **we cannot retroactively determine number of URLs returned, directory prevalence, or a provider recall score**.

## Why the original selection gate can abstain

The baseline `score_search_candidate` in `src/norway_company_agent/discovery.py` takes an exact Norwegian legal name, nine-digit org number and municipality. A target domain can fail crawl nomination when its **abbreviated or shortened root hostname** does not contain the complete compact legal name and the *search snippet* does not repeat the exact organisation number.

One alternate hypothesis is that the Basic Search query itself is over-constrained: `"<legal-name>" <orgnr> <municipality>`. The M28 report does **not** distinguish an over-constrained query (zero relevant results) from restrictive candidate scoring (results present but rejected). No new query experiments have been conducted.

A synthetic caveat discovered while testing: the **original v2 scorer already accepts a complete legal-name title on an exact-name hostname without an org number**. Therefore simply relaxing that case is **not a new capability**. Another adversarial test showed that the historical substring hostname comparison might nominate a malicious nested domain such as `company.no.attacker.com` for a fetch (not automatically publish it). The M32 wrapper checks candidate root-host syntax before reusing a baseline nomination; **the existing production M23 scorer is not changed**.

## M32 changes (isolated code)

`src/norway_company_agent/v10_m32_offline_nomination.py` adds two PURE, synthetic-fixture-only functions:

1. `nominate_offline(profile, parsed_results)` first uses the original chooser, but only inherits a plausibly safe public HTTPS root homepage. If it abstains, the challenger may nominate **one** full legal-name-title result from a root domain that matches a distinctive legal-name compact form, a deterministic acronym, or a multi-token legal-name alias. It needs at least two distinctive legal-name tokens; only existing baseline exact-org corroboration can exempt a short-name case. It rejects known directory/social platforms, partial-name-only roots, nested-host spoofing, private/IP/localhost hosts, userinfo, nonstandard ports, query strings and deep paths. A candidate is a proposed FIRST-PARTY FETCH, never a company claim.
2. `screen_independent_fixture(...)` applies exactly the pre-existing M23 independent-page provenance, `apply_website_identity_gate`, `qualify_search_discovered_website`, foreign/wrong-owner and conflicting org-number vetoes, plus the M26 same-registered-domain and exact nine-digit target-organisation-number-page requirement. It returns **status flags only**, never provider output, domain names, company identifiers or publishable claims.

In particular this experiment **does not weaken publication confidence**, alter BRREG legal entity facts, add or substitute any production request, fetch any site, use the Tavily key, perform new provider searches, change the evaluator, or modify `main`.

## Verifiable offline evidence

[Focused M32 CI](https://github.com/navadeep-17/signal-post/actions/runs/37873808970) passed **86** tests across M32's synthetic positive/negative cases, original M23/M25/M26 regressions and original search discovery tests. The CI source scan verified that the new module has no HTTP client or environment-key access.

Synthetic examples (invented names, NOT Norwegian company observations):

- Legacy gate abstains where a full legal-name title uses the plausible shortened root domain `nordlysmarin.no`; M32 nominates one first-party fetch but returns **0 published claims**.
- An acronym first-party-looking domain `arkjv.no` can be nominated without an organisation number in the search result, but only a separately fetched page with exact legal-entity proof can advance to manual review.
- Parent-company domains, mismatched title, directory domains, lookalike `*.attacker.com`, wrong organisation numbers and redirected/foreign owner pages remain quarantined.
- A full legal-name root domain `nordlysmarinteknologi.no` was ALREADY accepted by the baseline and is explicitly **not counted as any novel lift**.

These are controlled fixture behaviors, **not data from the sealed holdout, the previous 20 companies or a live search provider**.

## Next pre-registered private diagnostic, ONLY if user approves another credit spend

Before touching production or spending another 20 requests, propose at most **4 already-consumed companies from the frozen 20** and ONE Basic Search per selected company. Instrument only private, minimized in-memory counts:

- Raw search-result entries present.
- Valid HTTP(S) URL entries.
- Domain/category rejections (directory/social, unsafe root, weak title).
- Original-gate nominated versus challenger-only nominated.
- Independent robots/homepage fetch attempted/available.
- Exact-company first-party verification rejected/eligible.

Never persist provider titles, snippets, raw answers, scored result lists or API keys, and **never publish provider-specific service-performance benchmarking**. Company-level manual audit of every positive first-party proof remains required. Only aggregate, provider-neutral Signalpost internal funnel counts may enter public documentation, subject to the support permission scope.

If a future diagnostic is explicitly authorized, the maximum must be structurally capped at **4 search calls + 4 × 2 first-party requests = 12 logical / 24 conservative challenge charges** for the entire selected dev cohort, no automatic retry, no multi-query search. Stop on key/credit/rate failure. Use existing free credits only with PAYG OFF, write any sensitive report to an encrypted artifact, and do not touch the M20 sealed Gate B.

**NOT YET PROVEN:** real query relevance, raw-result yield, 2+ net new independently verified sites per original 20, complete V8 2,000-charge substitution, 2,400-second budget, evaluator secret availability, or any positive official competition score.

## Promotion policy

No code from M32, M31 or M28 enters `main` without measurable **real** exact-company improvement, zero wrong-company matches and independent manually audited transfer. Qualified V8 remains the safe and best validated submission.
