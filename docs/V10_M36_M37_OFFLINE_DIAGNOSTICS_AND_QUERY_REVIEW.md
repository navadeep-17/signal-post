# M36 + M37 — Offline rejection diagnostics and single-search hypotheses

**Decision: OFFLINE DESIGN ONLY / NO LIVE SEARCH / NO VERIFIED WEBSITE LIFT / DO NOT MERGE.**

## Previously observed internal Signalpost facts (from consumed development)

M33 four-company live diagnostic: https://github.com/navadeep-17/signal-post/actions/runs/37878315446
M34 encrypted aggregate analysis: https://github.com/navadeep-17/signal-post/actions/runs/37878595632

| Internal funnel stage | Observed |
|---|---:|
| Companies with normalized candidate search-result URLs | 4/4 |
| Companies with syntactically plausible HTTPS root URLs | 2/4 |
| Original selection algorithm nominated | 0/4 |
| Experimental M32 algorithm nominated | 0/4 |
| Independently fetched company pages | 0 |
| Verified new first-party exact-organisation-number sites | 0 |
| Published claims or proven score improvement | 0 |

These categories overlap. The earlier private report deliberately omitted URLs, titles, snippets and provider ranks. Consequently we cannot retrospectively attribute either of the two root-looking candidates to legal-name TITLE mismatch, deterministic DOMAIN alias mismatch, both, or incorrect search results. Homepage-shaped does NOT prove company ownership.

## M36: provider-neutral transient rejection reason flags

New file: src/norway_company_agent/v10_m36_offline_rejection_diagnostics.py

- Pure summary of at most ten transient search-candidate dictionaries; no provider HTTP, company HTTP, source persistence or credentials.
- Four mutually exclusive URL-shape counters: invalid/missing, directory/social, unsafe or deep/non-root, and syntactically plausible HTTPS root. These sum to inspected results.
- Separate overlapping reason counts on safe roots: incomplete full legal-name title, missing deterministic domain alias, both mismatches, missing municipality in transient result, missing exact organisation number in transient result and weak legal name.
- Compare per-result fetch nomination by old selector, M32 and M35. NOMINATION IS NOT A PUBLISHABLE LEGAL ENTITY CLAIM.
- Output is fixed integer-only/categorical aggregate flags, with NO source URLs, titles, snippets, organisation identifiers, ranks, search queries, or provider response text. Do not publish individual company-specific diagnostics.

## M37: pre-registered mutually exclusive one-query alternatives

New file: src/norway_company_agent/v10_m37_offline_query_design.py

| Variant name | Hypothetical query shape |
|---|---|
| v8_unchanged | quoted full legal name, exact 9-digit organisation number and municipality |
| legal_name_municipality_homepage | quoted full legal name, municipality, Norwegian homepage keyword |
| distinctive_name_municipality_website | quoted distinctive legal name without legal suffix, municipality, Norwegian website keyword |

The idea that removing organisation numbers might surface more first-party homepages is only an UNTESTED HYPOTHESIS. No provider results, recall gains, precision changes or challenge scores have been measured for either alternate query.

The compiler selects exactly ONE string variant and has no fallback search. All variants require a legal name, exact nine-digit organisation number and registry municipality; shortened distinctive-name queries require at least two informative tokens. It rejects quote/control injection, ambiguous/overlong inputs. The comparison output is anonymous query-shape FLAGS, not source query strings or provider outputs. No live transport imports this module.

## Synthetic example explanations, not observations from the four real companies

- Shortened company title on a deterministic multi-token root domain can fail the full-title gate even though the root is name-aligned.
- Full legal title with an unrelated root fails the deterministic domain-alias gate.
- Both title and alias can be missing at once, so their counts must NOT be added to estimate companies rejected.
- Directory/social, lookalike nested host, private IP, HTTP-only and deeper URLs must never become a first-party claim.
- Even when an M35 synthetic shadow nominee passes its fetch test, it publishes ZERO verified websites until independent exact Norwegian legal-entity evidence exists.

## Experiment gates: do not loosen

1. One Basic Search per eligible company in any FUTURE separately approved pilot, no multi-query retry or sequential fallback.
2. In 100-company production, provider search must REPLACE—not add—a website action inside the existing 4 site slots, preserving at most 1000 logical/2000 conservative redirect-counted requests and <=2400 seconds. Third-party dollar spend must remain $0.
3. Private report, encrypted artifact only, abort on key/rate/credit errors, PAYG OFF plus adequate remaining free credits confirmed before any live requests. Never publish provider-specific benchmarks or raw results.
4. A new verified site requires independent robots/homepage fetch, same registered-domain redirect, the exact target 9-digit organisation number on fetched first-party text, registry collision and wrong-entity vetoes, and manual review of every proposed positive.
5. Promotion: at least 2 net-new verified company sites / 20 already consumed dev examples, zero wrong entities and baseline losses, independent manual audit and separate disjoint consumed transfer proof before main. Sealed holdout untouched.

## Validation

Draft PR #180: https://github.com/navadeep-17/signal-post/pull/180
First full baseline CI with both new modules and tests: https://github.com/navadeep-17/signal-post/actions/runs/38023763496 — SUCCESS, 656 passed and 5 subtests, canonical 1000, refresh and submission-bundle audits.
Existing M33 live-only job skipped for normal PR CI. No API credits spent, no pages fetched and no real company websites verified by M36/M37.

**Next:** Only consider a new, separately approved tiny development search after privacy-safe rejection reason flags and a single pre-chosen query can be evaluated with hard request slots. Do not conflate more nominations with verified website score improvement.
