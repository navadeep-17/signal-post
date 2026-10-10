# M39 — Already-consumed BRREG/first-party evidence source inventory

**Decision: NO-GO for a new website signal from these retained fields. RESEARCH ONLY; draft/unmerged; never change production on zero gain.**

## Source basis and non-goals

Read only the original, SHA-pinned and already consumed M19-A/M19-B/M20-A archived 100-company baseline profiles/output each (300 distinct companies) and their exact M24 frozen 20 website-unverified subset.
Provenance and validation live at scripts/run_v10_m39_consumed_source_inventory.py; the existing M24 freeze/load asserts original ZIP digests, old frozen org IDs and unique records.
No BRREG refresh, independent website GET, provider search, Wikidata SPARQL lookup, or other new external data acquisition occurred. This is SOURCE-FIELD COVERAGE and existing pipeline status, NOT a source of newly verified websites.

## Exact 20-company previously consumed targeted findings

| Signal in retained profile/evidence fields | Count of 20 | Interpretation |
|---|---:|---|
| BRREG homepage on profile root | 0 | Deliberately absent from M24 selection |
| BRREG bulk registry original `hjemmeside` | 0 | No overlooked official website from this path |
| BRREG live normalized website | 0 | No overlooked live registry website from this path |
| Website field present in raw BRREG but missing from root projection | 0 | No source-to-profile projection issue observed |
| Parsed public registry email present | 1 | Contact evidence, not domain ownership |
| Generic/rejected registry mailbox | 1 | Must never nominate public mailbox domain |
| Eligible company-domain email under existing H1a filter | **0** | No previously untried registry-email-domain lead found in this cohort |
| Deterministic compact legal-name `.no` candidate representable | 20 | Already used by V8 H1c path; not a new source, not ownership proof |
| Deterministic hyphenated legal-name `.no` candidate representable | 17 | A known candidate family previously separately researched; NOT new verification |
| Retained website record unavailable/nonavailable | 20 | No already-fetched available first-party page to re-verify |
| Previously verified exact website | 0 | This 20-person development cohort was selected as website-unverified |

Thus this targeted 20-company cohort contains **no overlooked first-party website URL or non-generic BRREG email-domain candidate** among the explicitly audited fields. A legal-name guess being syntactically possible does not mean the guessed domain exists or belongs to the legal entity. No exact-org website has been newly verified.

## Broader original 300-company historical context

| Existing source/evidence category | Profiles |
|---|---:|
| Baseline profiles originally consumed | 300 |
| Complete registry name + municipality for this offline inventory | 297 |
| Incomplete registry legal-name/municipality (explicitly marked ineligible) | 3 |
| Profiles with root website seeds | 78 |
| Raw BRREG bulk registry website field | 55 |
| Live normalized BRREG website field | 55 |
| Raw or live website field missing from root projection | 0 |
| Registry contact emails parseable via existing H1a routine | 45 |
| Eligible non-consumer email domains under H1a in these retained records | 0 |
| Synthetic compact `.no` candidate available | 256 |
| Synthetic hyphenated `.no` candidate available | 201 |
| Previously verified website in baseline claims | **41** |

Counts are NONEXCLUSIVE, except the 297 complete + 3 incomplete identity partition. Counts come from frozen profile snapshots, not present-day live BRREG. The H1a email filter reads profile evidence `registry.value.epostadresse` and should not be confused with generic email fields or website ownership. Snapshot-wide contact/email candidate numbers are conditioned on these retained fields and current helper implementation; they are not general estimates for all Norwegian businesses.

Source provenance note: the root profile website can include earlier verified/enriched values, so root seeds (78) are NOT a direct measure of official BRREG `hjemmeside` (55). Some source pages existed but failed independent verification; they are not counted as new websites. The 41 originally published website claims reconcile exactly with the 41 earlier verified sites; this M39 audit publishes none.

## Prior implemented discovery paths already cover these signals

- `official.normalize_entity`: retains BRREG `hjemmeside` and `epostadresse` in official source evidence.
- `final_site_discovery.discover_final_website`: attempts root registry homepage (when present), then one business registry-email-domain candidate, then compact legal-name `.no` guess and optional same-domain identity proof within four logical site requests.
- `zero_cost_discovery.deterministic_domain_candidates`: compact and hyphenated legal-name `.no` candidates are only GUESSES; partial-name/hostname evidence cannot publish a legal entity.
- `wikidata_discovery`: exact-org `P2333` / website `P856` candidate path exists experimentally but is NOT data already present in the frozen BRREG profile fields. No live Wikidata lookup was part of M39.
- `zero_network_social_recovery` and `company_site_contact`: only recover extra claims from an ALREADY exact-verified company website, and cannot create a new website in an unresolved cohort.

## What we must not do

Do not report a candidate URL, email-domain match, `.no` guess, social profile, parent/affiliate website or syntactically plausible homepage as an exact legal entity without independent first-party page verification and the exact nine-digit Norwegian org-number evidence. The prior wrong-company example documented in H1C_SECONDARY_IDENTITY is why this remains non-negotiable.

Do not merge any M39 module into `main` as a coverage enhancement: observed new verified sites = 0, added production evidence = 0. No query fallback/spending or Wikidata/company-page requests occurred. A future experiment needs a materially NEW candidate signal and proper budget/manual-review proof; repeating registry-email or `.no` guesses without different evidence is not a new hypothesis.

## Checks

- [Draft PR #182](https://github.com/navadeep-17/signal-post/pull/182), based on immutable qualified V8 branch, remains research-only.
- [Zero-credit pinned historic archive audit #38025997513](https://github.com/navadeep-17/signal-post/actions/runs/38025997513): PASS, 54 focused tests, 20+300-source aggregate counts, no provider/site HTTP.
- [Exact source code full Baseline CI #38026001274](https://github.com/navadeep-17/signal-post/actions/runs/38026001274): PASS, 685 tests and 5 subtests, frozen evaluator and submission checks; both M33/M38 live-only jobs skipped.

**Next decision:** Do not add another website discovery source from BRREG profile fields. Either (a) establish a materially new, independently licensed exact-org-to-first-party-site candidate dataset with evidence it can improve random-company reach, or (b) prioritize existing V8 release reliability and scoring elsewhere. In either case require real net-new verified coverage, zero wrong-company matches/losses, disjoint consumed transfer, and 100-company budget proof before touching `main`.
