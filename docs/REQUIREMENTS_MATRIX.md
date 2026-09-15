# Signalpost requirements matrix

Updated: 2026-09-15

This file separates official requirements, starter behavior, measured status and remaining work. The current live Builderr Signalpost challenge page is authoritative for scoring, qualification and run limits. The starter's local competition scorer is a diagnostic proxy only.

Status meanings: **PASS** = directly reproduced/verified; **PARTIAL** = working foundation but the full scored requirement is not demonstrated; **OPEN** = hidden-evaluator dependent or not yet implemented; **GAP** = known current shortfall.

## Qualification and execution requirements

| Requirement | Authority | Current implementation/evidence | Status | Next action |
|---|---|---|---|---|
| Use Norwegian organisation number as entity anchor | Live challenge + starter | BRREG bulk/live and every promoted discovery path are keyed back to exact org number | PASS | Preserve invariant for future external observations |
| Public eligible universe is 411,160 frozen 2025-filer companies | Live challenge + universe metadata | Deterministic selector and published universe are used in validation workflows | PASS | Verify universe hash in submission bundle |
| Submit at least 1,000 completed profiles + exact manifest | Live challenge | Exact deterministic 1,000-company manifest was run as 800 non-heldout + predeclared 200 heldout; all 1,000 completed | PASS for release corpus | Assemble submission bundle/manifest from audited stack |
| Generalize beyond development companies | Live challenge | Multiple fresh zero-overlap 300-company validations plus final predeclared heldout 200 completed | PASS observed | Do not tune on consumed heldout; use new disjoint companies for later changes |
| Exactly one terminal result per evaluation company | Live challenge | Frozen 100, 800 and heldout 200 all had exact expected counts, unique org numbers and zero silent drops | PASS | Preserve in final runner |
| Final documented claims/evidence envelope | `OUTPUT_CONTRACT.md` | `run_signalpost_final.py` emits validated `claims[]`, `evidence[]`, `changes[]`, errors and operations | PASS | Keep contract regression on every PR |
| Claim-level source, retrieval time and period where relevant | Live challenge + contract | Release artifacts validate claim-specific evidence and financial periods/currency | PASS | Extend same requirement to every new external signal |
| Missing/blocked/not-applicable remain distinct | Live challenge + contract | Explicit mapping and regressions; missing is never silently zero | PASS | Preserve in UI/research layers |
| No fabricated financial values | Live challenge | Official deterministic BRREG accounting path; missing values remain missing | PASS | Preserve |
| External precision >=95%; no material wrong-company publication | Live challenge | Final heldout website audit: 20 correct / 0 wrong; extensive wrong-entity regressions for Oslo Mikrosement, ØkonomiBistand and St. Hanshaugen Venstre | PARTIAL / strong observed evidence | Builderr hidden evaluation remains authoritative; 20/20 does not statistically prove population >=95% |
| Weighted external company recall >=60% | Live challenge | Current production external path is mainly exact company website + company-owned fields; official hidden denominator is unavailable locally | **OPEN / PRIMARY RISK** | Expand qualified zero-cost external signals and submit for independent measurement |
| Coverage >=21/35 | Live challenge | Cannot be computed from own outputs because Builderr owns the versioned union and availability labels | **OPEN / PRIMARY RISK** | Same as above |
| Overall score >=65/100 | Live challenge | Hidden judge authoritative | OPEN | Cannot honestly self-score; use readiness diagnostics only |
| Idempotent refresh | Live challenge | Deterministic refresh fixture: expected changes reproduced; current→current rerun yields zero changes | PASS current tracked fields | Extend normalization/refresh to each promoted external signal |
| Previous snapshot/history preserved | Live challenge | Changes preserve old/new values, hashes, source provenance and times | PASS current tracked fields | Extend to external observations |
| 45-minute wall-clock / 100 companies | Live challenge | Frozen 100 about 95 s; 800 run 518.772 s; heldout 200 122.656 s | PASS with large headroom | Revalidate after each production connector |
| <=2,000 outbound requests / 100 companies | Live challenge | H1e final structure: <=901 logical / <=1,802 conservative challenge-charged requests per 100; frozen 100 observed 583 logical / 1,166 conservative | PASS | Do not spend headroom without measured coverage gain |
| <=$10 external API spend / 100 | Live challenge + project decision | Final policy is stricter: $0; search API requests 0 | PASS | Preserve $0 unless user explicitly changes policy |
| Machine-readable run report | Starter | Consolidated count, contract, refresh, budget, runtime and site-source report | PASS | Include in submission evidence |
| One evaluator command | Live challenge + starter | `scripts/run_signalpost_final.py` runs the promoted production stack | PASS | Keep setup/run path documented |
| Source rights documented | Live challenge | `CONNECTOR_STATUS.md` records approved/conditional/experimental/blocked paths; production uses official/company-owned plus CC0 Wikidata candidate nomination | PASS current production stack | Re-review any new source before promotion |
| Server-side secrets / no committed keys | Live challenge | Production stack requires no paid API secret | PASS current stack | Keep secret scan |
| Safe URL handling | Live challenge | public-URL checks, SSRF protection, robots handling and bounded redirects | PASS | Preserve for all URL-taking connectors |
| Pinned dependencies | Starter | `uv.lock`; `uv sync --locked` passes CI | PASS | Keep CI |
| Core regression suite | Starter | Current release CI: 205 tests + 5 subtests | PASS | Required on every PR |
| Snapshot drift does not crash batch | Hard terminal-output gate | Missing current BRREG bulk row is retained; live official lookup can recover; no fabricated identity | PASS | Keep drift regression |
| Candidate discovery independently verified | Live challenge/starter | H1a/H1c/H1d/H1e nominate candidates; company page identity is independently fetched/gated before publication | PASS | Keep discovery separate from evidence |
| UI makes evidence/gaps/changes inspectable | UX category | Static prototype exists | PARTIAL | Improve after external coverage work |
| Research answers only from supported evidence | Synthesis category | deterministic answer/screen layer with explicit abstention on unqualified topics | PARTIAL / safe | Add qualified external observations before richer synthesis |
| Models/APIs/licences/caches/hosting declared | Submission contract | Connector register and decisions document current stack | PARTIAL | Produce final submission manifest/checklist |
| Expected cost per 100 declared | Submission contract | $0 third-party API spend measured on frozen release runs | PASS | Re-measure after any production change |

## Current official-scoring readiness

The live official scoring is 35 coverage / 30 accuracy / 20 refresh / 10 synthesis / 5 UX.

| Official category | Current readiness | Why |
|---|---|---|
| Coverage & source discovery (35) | **RED / not established** | Builderr weights external company recall heavily; production still lacks major jobs/reviews/activity/metrics/sentiment families |
| Accuracy, identity & evidence (30) | **GREEN / strongest** | exact-org anchoring, conservative entity gates, claim evidence, 20/20 heldout website audit |
| Refresh & extensibility (20) | **GREEN current fields / YELLOW breadth** | robust idempotent refresh but narrow dynamic external signal set |
| Decision-useful synthesis (10) | **YELLOW** | safe cited answers/screens; explicit abstention limits external insight |
| UX & interaction (5) | **YELLOW** | usable static prototype, but data breadth matters more now |

Do not convert these readiness labels into an invented official point score. Builderr's hidden companies/labels and versioned external union are required for the real score.

## Full 1,000 release evidence

Audited application SHA:

`24145ffb98e36c31a16145d6408a7556a38b5289`

### Non-heldout 800

- workflow `34946808243`
- artifact digest `sha256:153fd7bf25a424650fe427bde8d0da559aec0835184892ba2fa231900d08655e`
- 800/800 completed
- 12,696 claims / 12,696 evidence items
- 4,688 logical / 9,376 conservative requests
- 518.772 s
- $0, search API 0
- 0 contract/change/budget errors
- 55 verified sites
- one known current-BRREG snapshot drift org safely retained

### Predeclared heldout 200

Heldout SHA:

`fb81f7695ee91606d1af7eee00e8323a326ebc33b79b3cb1a4f046573ae3368f`

- workflow `34948307697`
- artifact digest `sha256:d2e87c64324df31643ef969b9fd432d33fe971c8689c36833b9a56edf5176efd`
- 200/200 completed
- 3,191 claims / 3,191 evidence items
- 1,208 logical / 2,416 conservative requests = 1,208 conservative/100
- 122.656 s
- $0, search API 0
- 0 contract/change/budget errors
- 20 verified websites
- manual website audit: 20 correct / 0 wrong

The 200-company heldout is consumed and cannot be used for future tuning.

## Observable external reach across the full 1,000

These are diagnostics from the exact release artifacts, **not official recall**:

- verified official website: 75/1,000 = 7.5%
- company description from verified site: 56/1,000 = 5.6%
- publishable company-declared social links: 32/1,000 = 3.2%
- 55 publishable declared handle URLs across those 32 companies
  - Facebook: 25 companies
  - Instagram: 19
  - LinkedIn: 10
  - YouTube: 1
- 19 companies have at least two publishable social platforms declared by the exact company site

These declarations do not imply social-platform posts, metrics, jobs, reviews or sentiment were fetched.

## Historical qualification highlights

- starter baseline: 104 tests + 5 subtests; 10-company live smoke green.
- frozen development 100 manifest SHA: `51a96f25f79532b9ba285304d540887e0f17410907909dbe6c85c0b41b8341d3`.
- output-contract qualification: 100 objects, 1,568 claims/evidence, artifact `sha256:1a2ba378e16d8a1f9a47983fa38853ad4ae9aa4a8c623c37a30fc7f18816e070`.
- refresh qualification: exact 2/2 changes + idempotent rerun, artifact `sha256:e317bdf7612e2327324e34a9895a27d82db89702712c82c7b981ac274d3291cf`.
- H1d final fresh 300: 15→18 verified sites, 18/18 audit correct, no request-ceiling increase.
- H1e fresh 300: 16→17 verified sites, sole new site manually correct; production ceiling became 1,802 conservative requests/100.
- snapshot-drift live smoke: 2/2 terminal outputs with missing bulk entity retained honestly.

## Next action

See `SCORING_READINESS_AUDIT.md`. The next bounded experiment is **H2a company-declared social profile observations**: port the conservative dormant social-handle extractor onto current `main`, emit only the narrow evidence-backed `profile_handle` claim from exact company pages, add no social-platform fetches, spend $0 and validate on a new disjoint corpus outside the consumed original 1,000.

Update this matrix whenever a requirement changes state. Do not mark the official coverage/recall gates PASS from a self-defined denominator.
