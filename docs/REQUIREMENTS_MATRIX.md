# Signalpost requirements matrix

This file separates official requirements, starter behavior, measured status, and work still required. Do not mark a row PASS merely because a related module exists.

Status meanings: **PASS** = reproduced or directly verified; **PARTIAL** = foundation exists but final requirement is not yet fully demonstrated; **OPEN** = not yet measured/implemented; **GAP** = current behavior conflicts with or does not implement the documented requirement.

| Requirement | Authority | Current implementation/evidence | Status | Next verification/action |
|---|---|---|---|---|
| Use Norwegian organisation number as entity anchor | Live challenge + starter | BRREG bulk/live lookup keyed by exact org number | PASS | Preserve invariant in all connectors |
| Public eligible universe is 411,160 frozen 2025-filer companies | Live challenge + `data/universe-metadata.json` | Universe metadata and selector included | PASS | Verify downloaded universe hash in release process |
| Submit at least 1,000 completed profiles + exact manifest | Live challenge + README | `select_entry_batch.py` deterministically produced a 1,000-company manifest in benchmark | PARTIAL | Generate/freeze final 1,000+ completed profiles and submission manifest |
| Generalize to random unseen companies | Live challenge | Generic batch pipeline completed frozen 100-company development slice | PARTIAL | Zero-overlap validation and held-out release audit still required |
| Exactly one terminal result per evaluation company | Live challenge | Frozen output-contract qualification emitted exactly 100 unique contract objects from 100 internal terminal envelopes; zero silent drops | PASS | Revalidate in locked final orchestrator |
| Final documented claims/evidence output envelope | `OUTPUT_CONTRACT.md` | `output_contract.py` + `project_output_contract.py`; frozen 100 qualification emitted the documented top-level shape for all 100 companies | PASS | Preserve shape in final orchestration/release fixture |
| Final `run.terminal_status` | `OUTPUT_CONTRACT.md` | Deterministic internal-state projection implemented; frozen 100 produced 100 `completed` terminal statuses | PASS | Add explicit failed-envelope release fixture as well as unit regression |
| Claims contain field/value/availability/confidence/evidence IDs | `OUTPUT_CONTRACT.md` | Frozen 100 emitted 1,568 validated claims, each with deterministic evidence linkage | PASS | Preserve claim-level regression coverage as fields expand |
| Evidence contains URL/source class/retrieval/hash/claim span | Live challenge + `OUTPUT_CONTRACT.md` | Hardened frozen 100 emitted 1,568 claim-specific evidence items for 1,568 claims; all available claims had URL, retrieval time, 64-char content hash and claim span | PASS | Continue enforcing for future external claims |
| Reporting period retained where relevant | Live challenge | Financial projection carries normalized reporting period and currency; zero/None regression tests pass | PASS | Preserve when financial history is extended |
| Missing/blocked/not-applicable remain distinct; never silently zero | Live challenge + contract | Tested mapping: not-found→not-available, blocked→blocked, source-error→failed, not-applicable preserved; not-fetched stays explicit in errors because final vocabulary has no not-fetched state; zero values remain available zeros | PASS | Do not collapse states in UI/research layers |
| No fabricated financial values | Live challenge | Official BRREG accounting path is deterministic, not LLM-generated; zero and reporting-period regressions pass through final adapter | PASS baseline | Preserve regression/audit on validation and held-out runs |
| External precision >=95% and no material wrong-company publication | Live challenge | Conservative identity gate + H1c risk guard exist; H1c frozen audit caught and quarantined wrong-domain collisions before merge | OPEN | Run larger zero-overlap external precision audit before claiming threshold |
| Weighted external company recall >=60% | Live challenge | H1c improves verified-site discovery but current qualified external footprint remains far below final recall target | OPEN | Expand only qualified zero-cost external/company-owned signals and measure recall |
| Coverage >=21/35 | Live challenge | Not directly measurable from current official + limited verified-site stack | OPEN | Evaluate after qualified source expansion |
| Overall score >=65/100 | Live challenge | Hidden judge authoritative; local proxy not equivalent | OPEN | Use local proxy for diagnostics only; submit for independent evaluation when gates are supported |
| Idempotent refresh | Live challenge | Refresh replay fixture reproduced: 2 TP, 0 FP, 0 FN, idempotent rerun | PASS | Extend tests when external observations enter refresh |
| Previous snapshot/history preserved | Live challenge | Snapshot/refresh implementation exists | PASS for fixture | Audit external connector refresh semantics later |
| 45-minute wall-clock for 100-company batch | Live challenge | Frozen output-contract qualification's internal 100-company pipeline completed in ~95 seconds after frozen inputs were available | PASS current stack | Revalidate final connector stack with evaluator-style end-to-end runner |
| <=2,000 outbound requests per 100-company batch | Live challenge | Hardened output-contract qualification used 622 research requests | PASS current stack | Add final global budget guard and remeasure with future qualified layers |
| <=$10 third-party API cost per 100-company batch | Live challenge + project decision | Frozen output-contract qualification declared and verified $0 third-party spend; project policy targets $0 | PASS current stack | Preserve $0 production constraint in final orchestrator |
| Machine-readable run report | README | Internal runner + contract projection emit machine-readable validation reports | PASS current stack | Combine into final orchestrator report |
| One evaluator command | Live challenge + README | Core runner plus final projection are still two commands; experiments remain separate | PARTIAL | Build final orchestrator only after remaining qualified layers are frozen |
| Source rights documented | Live challenge + starter external model | Acquisition modes/rights gates exist; connector register added in `CONNECTOR_STATUS.md` | PARTIAL | No experimental source promoted by relabeling; verify each production provider |
| Server-side secrets/private keys not committed | Live challenge + how-to-enter | Final strategy currently requires no paid API secrets | PASS current stack | Keep release secret scan even with $0 architecture |
| Safe URL handling | Live challenge | Website/HTTP stack includes private-network/redirect protections | PASS design/tests | Preserve and extend regression coverage for new URL-taking connectors |
| Pinned/reproducible dependencies | README | `uv.lock` exists; `uv sync --locked` passes CI | PASS | Consider pinning CI uv tool version separately |
| Core regression suite | Starter | Full GitHub Actions suite passes with added H1c/output-contract regressions | PASS | Required on every PR |
| Live baseline smoke | Starter README | 10-company live run reproduced successfully | PASS | Keep manual/reproducible workflow |
| Frozen 100-company development benchmark | Project plan | Exact manifest/input hashes and failure-bucket report recorded in `BASELINE_100.md`; reused for H1c and output-contract qualification | PASS | Continue same manifest for before/after development comparisons |
| Search candidates independently verified before publication | Live challenge/starter docs | H1a/H1c candidate discovery is separated from independent fetch + exact identity publication gate | PASS for promoted zero-cost domain paths | Preserve zero-overlap precision audit before any new discovery source |
| UI makes evidence/gaps/changes inspectable | Live challenge UX category | Existing `build_prototype.py` provides substantial static prototype | PARTIAL | Improve after engine/qualified evidence stabilizes |
| Research answers only from supported evidence | Live challenge + starter | Deterministic/evidence-bounded research layer exists | PARTIAL | Extend only with qualified observations; test abstention |
| Models/APIs/licences/caches/hosting assumptions declared | Submission contract | Starter docs + connector-status/project decisions cover current stack | PARTIAL | Produce final release manifest from actual promoted stack |
| Expected cost per 100-company run declared | Submission contract | Current qualified path measured at $0 third-party spend | PARTIAL | Re-measure locked final orchestrator and declare final expected cost |

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

## H1c zero-cost discovery record

- H1c was promoted only after false-positive audit and registry-risk hardening.
- Frozen 100 exact-site coverage improved from 3 canonical exact sites after H1a to 6 after hardened H1c.
- Combined H1a + H1c path remained well below the 2,000-request gate and used $0 third-party API spend.
- Single-token names require registry-location or organisation-number corroboration; foreign/holding collisions are quarantined rather than blacklisted case-by-case.

## Output-contract qualification record

- Workflow: `Output Contract 100 Qualification`, hardened run `34876799814`.
- Frozen development corpus: 100 companies, same manifest SHA-256 `51a96f25f79532b9ba285304d540887e0f17410907909dbe6c85c0b41b8341d3`.
- 100 internal envelopes → exactly 100 unique final contract objects.
- 1,568 claims and 1,568 claim-specific evidence items; no dangling evidence references.
- Availability distribution: 1,379 available, 184 not-available, 4 ambiguous, 1 blocked.
- All 1,379 available claims had a 64-character content SHA-256 in the hardened artifact.
- 100/100 final `run.terminal_status` values were `completed`.
- 622 total research requests; $0 third-party cost.
- Per-company measured runtime is derived from that profile's request latencies when available, rather than copying the whole batch wall-clock into every output object.
- Qualification artifact digest: `sha256:1a2ba378e16d8a1f9a47983fa38853ad4ae9aa4a8c623c37a30fc7f18816e070`.

Update this matrix when a requirement changes state; link the PR/benchmark evidence rather than changing status from memory.
