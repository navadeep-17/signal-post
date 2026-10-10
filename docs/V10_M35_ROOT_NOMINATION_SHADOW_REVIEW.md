# M35 — Offline root-candidate rejection diagnosis and *shadow-only* title hypothesis

**Decision: synthetic analysis is complete, production integration prohibited.** This document distinguishes (A) observed internal Signalpost pilot outcomes, (B) source-code facts, and (C) unproven hypotheses from synthetic fixtures.

## A. What the previously consumed pilot really established

The four-company M33 diagnostic (run [#37878315446](https://github.com/navadeep-17/signal-post/actions/runs/37878315446)) and the private in-memory M34 analysis (run [#37878595632](https://github.com/navadeep-17/signal-post/actions/runs/37878595632)) established the following **internal** counts only:

| Fact from the encrypted report | Observed |
|---|---:|
| Previously consumed companies processed | 4 |
| Companies with at least one normalized search-result URL | 4 |
| Companies with at least one syntactically plausible HTTPS root URL | 2 |
| Companies with at least one directory or social URL | 4 |
| Companies with at least one unsafe, deep or non-root URL | 4 |
| Original algorithm nominated for fetch | 0 |
| M32 challenger nominated for fetch | 0 |
| Independent first-party GETs attempted | 0 |
| Exact-company legal-entity sites independently verified | 0 |
| Published company claims / observed score lift | 0 |

**Overlapping URL category buckets are not result-level provenance.** The M33 report intentionally discarded source URLs, titles, snippets and ranked result lists, so it **cannot determine** whether the two root-looking candidates represented the target companies, whether they were blocked by *title mismatch*, *domain alias mismatch*, *both*, or other risk checks, or whether the query was optimal. The report contains enough to rule out fully empty search responses in this four-company development set, not enough to rank a search provider or establish provider recall. There has been no score-eligible new verified website.

## B. What the code actually requires

The historical scorer in `src/norway_company_agent/discovery.py` admits a fetch only for a high-scoring first-party-looking result when the exact organisation number and full legal name appear together or a domain directly matches a compact legal-name string with strong corroboration. It previously tolerated a misleading `company.no.attacker.com` substring *as a crawl nominee* (not a published legal-entity claim); isolated M32 checks the entire root hostname before inheriting a nominee.

M32 `nominate_offline` checks the original candidate chooser first. Its alternate candidate must have a two-label root HTTPS domain, no directory or social host, a title containing **all** distinctive legal-name tokens, and domain strength `exact`, `acronym`, or `multi`. That guard can abstain if a genuine brand homepage has only a shortened public-facing title, but *we did not observe that specific scenario in M33* because the provider title was not retained.

All production and previous M23/M26 publication rules remain independent: the site must be independently fetched, first-party provenance confirmed, BRREG legal entity / collision risks checked, redirect registered domain verified, and the **exact nine-digit Norwegian organisation number extracted from the fetched site** before any manual review. Result title/snippet is NEVER sufficient publication evidence.

## C. M35 synthetic-only shadow experiment

New, isolated `src/norway_company_agent/v10_m35_shadow_rejection_analysis.py` contains:

1. `diagnose_url_nomination_reasons(profile, parsed_results)` — emits **only private-safe reason counts**, with no URLs, company identities, title/snippet strings, provider rankings or website calls. This can later help distinguish a full-title mismatch, disallowed domain alias and unsafe URL among synthetically generated candidates.
2. `shadow_nominate_for_fixture_only(profile, parsed_results)` — preserves any M32 nominee unchanged. It considers an additional **potential first-party fetch** only if the legal name contains ≥3 distinctive tokens; the transient result title contains the FIRST and at least one other legal-name token; the URL is a safe HTTPS root hostname with **exact** or deterministic **multi-token** legal-domain strength; the municipality appears in the transient snippet; and no conflicting nine-digit organisation number or competing incorporated/holding/parent/group legal-name title cue appears. Acronym-only matches, partial domain-name matches, directory/social pages, unrelated hosts, unsafe paths, and absent municipality abstain.

This shadow procedure is **NOT wired into M33, V8, any production workflow or any live Tavily transport**. It performs zero HTTP requests, zero provider requests, publishes zero company claims, and does not use any real M33 search-result material.

### Synthetic test matrix (not external search evidence)

| Invented example | Historical/M32 | M35 shadow | Publication |
|---|---|---|---|
| Full title; `nordlysmarin.no` shortened multi-token domain | M32 may nominate | unchanged M32 | **0** |
| Shortened title `Nordlys Marin`; same domain; snippet mentions Tromsø | abstains | **fetch nominee only** | **0** |
| Shortened title; full `nordlysmarinteknologi.no` root domain | abstains | **fetch nominee only** | **0** |
| Shortened title; wrong municipality | abstains | abstains | **0** |
| Competing title `Nordlys Marin Holding AS` | abstains | abstains | **0** |
| Wrong nine-digit number in result metadata | abstains | abstains | **0** |
| Partial-domain news, parent, `company.no.attacker.com` or directory | abstains | abstains | **0** |

**We do not know if either of M33's two plausible HTTPS root candidates resembles the positive fixture cases.** Do not count 2/4 as recovered or claim the new shadow policy has observed lift.

### Verification

[Exact M35 Baseline CI](https://github.com/navadeep-17/signal-post/actions/runs/37879273514) **SUCCESS**, **634 passed + 5 subtests**, including M35 adversarial cases, historical M23/M25/M26/M33 regressions, canonical 1,000-row audit, deterministic refresh and submission-bundle verification. The experimental live M33 job was **skipped** on pull request. No new provider credits spent.

## Recommended next decision

**Do not merge or spend additional Tavily credits at this stage.** Given no original provider titles/snippets were retained, a responsible next step is offline design review against hard negative examples and a carefully scoped future *private, aggregate-only* diagnostic schema that preserves **boolean reason flags**, not provider titles/URLs. Only with fresh express permission and current free credits/PAYG OFF should a small additional dev-only live pilot be considered. That pilot would test whether there are *real first-party exact-organisation-number pages* rather than nominally improving crawl nominations.

Success to justify a later production proposal requires measured net-new site coverage with exact first-party legal-entity proof, zero wrong-company matches or baseline losses, independent transfer (not previously consumed data), and the original 100-company 2,000-charge/2,400-second ceilings. Until then, qualified V8 and `main` remain unchanged; PR #179 is experimental/draft.
