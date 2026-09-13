# Signalpost requirements matrix

This file separates official requirements, starter behavior, measured status, and work still required. Do not mark a row PASS merely because a related module exists.

Status meanings: **PASS** = reproduced or directly verified; **PARTIAL** = foundation exists but final requirement is not yet fully demonstrated; **OPEN** = not yet measured/implemented; **GAP** = current behavior conflicts with or does not implement the documented requirement.

| Requirement | Authority | Current implementation/evidence | Status | Next verification/action |
|---|---|---|---|---|
| Use Norwegian organisation number as entity anchor | Live challenge + starter | BRREG bulk/live lookup keyed by exact org number | PASS | Preserve invariant in all connectors |
| Public eligible universe is 411,160 frozen 2025-filer companies | Live challenge + `data/universe-metadata.json` | Universe metadata and selector included | PASS | Verify downloaded universe hash in release process |
| Submit at least 1,000 completed profiles + exact manifest | Live challenge + README | `select_entry_batch.py` enforces 1,000 selection | PARTIAL | Generate/freeze final 1,000+ profiles and manifest |
| Generalize to random unseen companies | Live challenge | Generic batch pipeline exists | PARTIAL | 100-company baseline, zero-overlap validation, held-out release audit |
| Exactly one terminal result per evaluation company | Live challenge | Internal runner validates expected count/unique orgs/zero silent drops | PASS for 10 smoke | Re-run at 100 and final 1,000 |
| Final documented claims/evidence output envelope | `OUTPUT_CONTRACT.md` | No adapter found; internal runner emits `state/modules/profile` | GAP | Design and test explicit final-output adapter |
| Final `run.terminal_status` | `OUTPUT_CONTRACT.md` | Internal runner uses top-level `state`; no `terminal_status` implementation found | GAP | Map internal terminal state deliberately in adapter |
| Claims contain field/value/availability/confidence/evidence IDs | `OUTPUT_CONTRACT.md` | Rich internal evidence exists; no final `claims[]` adapter found | GAP | Define deterministic claim projection and tests |
| Evidence contains URL/source class/retrieval/hash/claim span | Live challenge + `OUTPUT_CONTRACT.md` | Evidence framework captures source/retrieval/hash; coverage varies by module | PARTIAL | Audit final projected claims for complete linked evidence |
| Reporting period retained where relevant | Live challenge | Official financial records preserve periods | PARTIAL | Assert period survives final claim adapter for all material financial claims |
| Missing/blocked/not-applicable remain distinct; never silently zero | Live challenge + contract | Internal evidence distinguishes source states; final availability vocabulary differs | PARTIAL | Define tested internal-to-final availability mapping |
| No fabricated financial values | Live challenge | Official BRREG accounting path is deterministic, not LLM-generated | PASS design | Regression/audit on 100/held-out runs |
| External precision >=95% and no material wrong-company publication | Live challenge | Conservative identity gate exists | OPEN | Build labelled/frozen external identity audit and measure precision |
| Weighted external company recall >=60% | Live challenge | External framework/experiments exist | OPEN | Measure only qualified external observations on 100-company benchmark |
| Coverage >=21/35 | Live challenge | Not directly measured yet | OPEN | Evaluate after qualified source expansion |
| Overall score >=65/100 | Live challenge | Hidden judge authoritative; local proxy not equivalent | OPEN | Use local proxy for diagnostics only; submit for independent evaluation when qualified |
| Idempotent refresh | Live challenge | Refresh replay fixture reproduced: 2 TP, 0 FP, 0 FN, idempotent rerun | PASS | Extend tests when external observations enter refresh |
| Previous snapshot/history preserved | Live challenge | Snapshot/refresh implementation exists | PASS for fixture | Audit external connector refresh semantics later |
| 45-minute wall-clock for 100-company batch | Live challenge | 10-company core smoke ~26 sec after snapshots were available | OPEN | Run locked 100-company benchmark; do not extrapolate blindly |
| <=2,000 outbound requests per 100-company batch | Live challenge | 10-company smoke used 56 research requests | OPEN | Measure 100; add global budget guard before release |
| <=$10 third-party API cost per 100-company batch | Live challenge | Baseline uses no paid external connector | PASS baseline only | Add connector-level and batch-level declared cost accounting |
| Machine-readable run report | README | Current runner emits runtime/request report | PARTIAL | Add/verify third-party cost and final runner totals |
| One evaluator command | Live challenge + README | Core runner is one command, external experiments separate | PARTIAL | Build final orchestrator only after connectors are promoted |
| Source rights documented | Live challenge + starter external model | Acquisition modes/rights gates exist | PARTIAL | Maintain per-connector status; no experimental source promoted by relabeling |
| Server-side secrets/private keys not committed | Live challenge + how-to-enter | No required API secrets in baseline | PASS baseline only | Use GitHub Actions/repo secrets and add release secret scan |
| Safe URL handling | Live challenge | Website/HTTP stack includes private-network/redirect protections | PASS design/tests | Preserve and extend regression coverage for new URL-taking connectors |
| Pinned/reproducible dependencies | README | `uv.lock` exists; `uv sync --locked` passes CI | PASS | Consider pinning CI uv tool version separately |
| Core regression suite | Starter | GitHub Actions reproduced 104 tests + 5 subtests | PASS | Required on every PR |
| Live baseline smoke | Starter README | 10-company live run reproduced successfully | PASS | Keep manual/reproducible workflow |
| Search candidates independently verified before publication | Live challenge/starter docs | Discovery + identity gate separated conceptually | PARTIAL | Ensure every future search connector follows this path |
| UI makes evidence/gaps/changes inspectable | Live challenge UX category | Existing `build_prototype.py` provides substantial static prototype | PARTIAL | Improve after engine/qualified evidence stabilizes |
| Research answers only from supported evidence | Live challenge + starter | Deterministic/evidence-bounded research layer exists | PARTIAL | Extend only with qualified observations; test abstention |
| Models/APIs/licences/caches/hosting assumptions declared | Submission contract | Starter docs cover baseline components | PARTIAL | Produce final release manifest from actual promoted stack |
| Expected cost per 100-company run declared | Submission contract | No final qualified connector stack yet | OPEN | Measure locked release candidate, do not estimate from marketing/API list prices alone |

## Phase 0 reproducibility record

- Untouched starter commit: `d0d4599cbb9a1ed00303976c9984630a004ed37a`
- Preserved branch: `baseline/builderr-starter-2026-08-24`
- Offline baseline CI: 104 tests + 5 subtests passed.
- Refresh replay: 2 expected/observed changes, precision 1.0, recall 1.0, complete evidence, idempotent rerun.
- Live smoke: 10/10 internal terminal envelopes, 56 research requests, p50 682 ms, p95 750 ms, zero silent drops.

Update this matrix when a requirement changes state; link the PR/benchmark evidence rather than changing status from memory.
