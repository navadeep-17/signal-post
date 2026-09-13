# Signalpost requirements matrix

This file separates official requirements, starter behavior, measured status, and work still required. Do not mark a row PASS merely because a related module exists.

Status meanings: **PASS** = reproduced or directly verified; **PARTIAL** = foundation exists but final requirement is not yet fully demonstrated; **OPEN** = not yet measured/implemented; **GAP** = current behavior conflicts with or does not implement the documented requirement.

| Requirement | Authority | Current implementation/evidence | Status | Next verification/action |
|---|---|---|---|---|
| Use Norwegian organisation number as entity anchor | Live challenge + starter | BRREG bulk/live lookup keyed by exact org number | PASS | Preserve invariant in all connectors |
| Public eligible universe is 411,160 frozen 2025-filer companies | Live challenge + `data/universe-metadata.json` | Universe metadata and selector included | PASS | Verify downloaded universe hash in release process |
| Submit at least 1,000 completed profiles + exact manifest | Live challenge + README | `select_entry_batch.py` deterministically produced a 1,000-company manifest in benchmark | PARTIAL | Generate/freeze final 1,000+ completed profiles and submission manifest |
| Generalize to random unseen companies | Live challenge | Generic batch pipeline completed frozen 100-company development slice | PARTIAL | Zero-overlap validation and held-out release audit still required |
| Exactly one terminal result per evaluation company | Live challenge | 100-company baseline emitted 100 unique internal terminal envelopes with zero silent drops | PASS baseline | Revalidate after final-output adapter and qualified connectors |
| Final documented claims/evidence output envelope | `OUTPUT_CONTRACT.md` | No adapter found; internal runner emits `state/modules/profile` | GAP | Design and test explicit final-output adapter in its own bounded PR |
| Final `run.terminal_status` | `OUTPUT_CONTRACT.md` | Internal runner uses top-level `state`; no `terminal_status` implementation found | GAP | Map internal terminal state deliberately in adapter |
| Claims contain field/value/availability/confidence/evidence IDs | `OUTPUT_CONTRACT.md` | Rich internal evidence exists; no final `claims[]` adapter found | GAP | Define deterministic claim projection and tests |
| Evidence contains URL/source class/retrieval/hash/claim span | Live challenge + `OUTPUT_CONTRACT.md` | Evidence framework captures source/retrieval/hash; coverage varies by module | PARTIAL | Audit final projected claims for complete linked evidence |
| Reporting period retained where relevant | Live challenge | Official financial records preserve periods | PARTIAL | Assert period survives final claim adapter for all material financial claims |
| Missing/blocked/not-applicable remain distinct; never silently zero | Live challenge + contract | Internal evidence distinguishes source states; final availability vocabulary differs | PARTIAL | Define tested internal-to-final availability mapping |
| No fabricated financial values | Live challenge | Official BRREG accounting path is deterministic, not LLM-generated; 100-company baseline financial module completed | PASS baseline | Preserve regression/audit on validation and held-out runs |
| External precision >=95% and no material wrong-company publication | Live challenge | Conservative identity gate exists; only 2/7 registry websites were exact in the 100-company baseline | OPEN | Build frozen domain/external identity audit and measure precision before promotion |
| Weighted external company recall >=60% | Live challenge | External framework/experiments exist; current baseline has very low verified external-site coverage | OPEN | Promote only qualified external observations and measure recall on frozen corpus |
| Coverage >=21/35 | Live challenge | Not directly measurable from this official-foundation-only baseline | OPEN | Evaluate after qualified source expansion |
| Overall score >=65/100 | Live challenge | Hidden judge authoritative; local proxy not equivalent | OPEN | Use local proxy for diagnostics only; submit for independent evaluation when gates are supported |
| Idempotent refresh | Live challenge | Refresh replay fixture reproduced: 2 TP, 0 FP, 0 FN, idempotent rerun | PASS | Extend tests when external observations enter refresh |
| Previous snapshot/history preserved | Live challenge | Snapshot/refresh implementation exists | PASS for fixture | Audit external connector refresh semantics later |
| 45-minute wall-clock for 100-company batch | Live challenge | Frozen baseline core run completed in about 61.8 seconds after input snapshots were available | PASS baseline only | Revalidate final connector stack with the evaluator-style end-to-end runner |
| <=2,000 outbound requests per 100-company batch | Live challenge | Frozen 100-company baseline used 536 research requests | PASS baseline only | Add qualified connectors + global budget guard, then remeasure with headroom |
| <=$10 third-party API cost per 100-company batch | Live challenge | Baseline uses no paid external connector | PASS baseline only | Add connector-level and batch-level declared cost accounting |
| Machine-readable run report | README | Current runner emits runtime/request report | PARTIAL | Add/verify third-party cost and final runner totals |
| One evaluator command | Live challenge + README | Core runner is one command, external experiments separate | PARTIAL | Build final orchestrator only after connectors are promoted |
| Source rights documented | Live challenge + starter external model | Acquisition modes/rights gates exist; connector register added in `CONNECTOR_STATUS.md` | PARTIAL | No experimental source promoted by relabeling; verify each production provider |
| Server-side secrets/private keys not committed | Live challenge + how-to-enter | No required API secrets in baseline | PASS baseline only | Use GitHub Actions/repo secrets and add release secret scan |
| Safe URL handling | Live challenge | Website/HTTP stack includes private-network/redirect protections | PASS design/tests | Preserve and extend regression coverage for new URL-taking connectors |
| Pinned/reproducible dependencies | README | `uv.lock` exists; `uv sync --locked` passes CI | PASS | Consider pinning CI uv tool version separately |
| Core regression suite | Starter | GitHub Actions reproduced 104 tests + 5 subtests | PASS | Required on every PR |
| Live baseline smoke | Starter README | 10-company live run reproduced successfully | PASS | Keep manual/reproducible workflow |
| Frozen 100-company development benchmark | Project plan | Exact manifest/input hashes and failure-bucket report recorded in `BASELINE_100.md` | PASS | Reuse same manifest for before/after feature comparisons |
| Search candidates independently verified before publication | Live challenge/starter docs | Discovery + identity gate are separated; existing Brave script independently fetches selected candidates | PARTIAL | Qualify provider rights and domain precision before integration |
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

## Phase 1 baseline record

- Frozen development manifest SHA-256: `51a96f25f79532b9ba285304d540887e0f17410907909dbe6c85c0b41b8341d3`
- 100/100 internal terminal envelopes; built-in validation PASS; zero silent drops.
- 536 research requests; p50 569 ms; p95 614 ms.
- Core 100-company run: about 61.8 seconds after input snapshots were available.
- Registry website missing for 93/100 companies.
- Of 7 registry-site cases: 2 exact, 1 review, 3 related/uncertain, 1 blocked.
- First feature hypothesis: safe missing-domain discovery followed by independent exact-entity page verification. See `BASELINE_100.md`.

Update this matrix when a requirement changes state; link the PR/benchmark evidence rather than changing status from memory.
