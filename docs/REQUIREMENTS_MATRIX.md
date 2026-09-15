# Signalpost requirements matrix

This file separates official requirements, starter behavior, measured status, and work still required. Do not mark a row PASS merely because a related module exists.

Status meanings: **PASS** = reproduced or directly verified; **PARTIAL** = foundation exists but final requirement is not yet fully demonstrated; **OPEN** = not yet measured/implemented; **GAP** = current behavior conflicts with or does not implement the documented requirement.

| Requirement | Authority | Current implementation/evidence | Status | Next verification/action |
|---|---|---|---|---|
| Use Norwegian organisation number as entity anchor | Live challenge + starter | BRREG bulk/live lookup keyed by exact org number | PASS | Preserve invariant in all connectors |
| Public eligible universe is 411,160 frozen 2025-filer companies | Live challenge + `data/universe-metadata.json` | Universe metadata and selector included | PASS | Verify downloaded universe hash in release process |
| Submit at least 1,000 completed profiles + exact manifest | Live challenge + README | `select_entry_batch.py` deterministically produced a 1,000-company manifest in benchmark | PARTIAL | Generate/freeze final 1,000+ completed profiles and submission manifest |
| Generalize to random unseen companies | Live challenge | Generic batch pipeline completed frozen 100-company development slice | PARTIAL | Zero-overlap validation and held-out release audit still required |
| Exactly one terminal result per evaluation company | Live challenge | Frozen final-evaluator qualification emitted exactly 100 unique completed contract objects from 100 inputs; zero silent drops | PASS | Preserve in locked release runner |
| Final documented claims/evidence output envelope | `OUTPUT_CONTRACT.md` | `output_contract.py` + one-command `run_signalpost_final.py`; frozen 100 qualification emitted the documented top-level shape for all 100 companies | PASS | Preserve shape in release fixture |
| Final `run.terminal_status` | `OUTPUT_CONTRACT.md` | Deterministic internal-state projection implemented; frozen 100 produced 100 `completed` terminal statuses | PASS | Add explicit failed-envelope release fixture as well as unit regression |
| Claims contain field/value/availability/confidence/evidence IDs | `OUTPUT_CONTRACT.md` | Frozen final-evaluator run emitted 1,568 validated claims, each with deterministic evidence linkage | PASS | Preserve claim-level regression coverage as fields expand |
| Evidence contains URL/source class/retrieval/hash/claim span | Live challenge + `OUTPUT_CONTRACT.md` | Hardened frozen 100 emitted 1,568 claim-specific evidence items for 1,568 claims; contract validation passed | PASS | Continue enforcing for future external claims |
| Reporting period retained where relevant | Live challenge | Financial projection carries normalized reporting period and currency; zero/None regression tests pass | PASS | Preserve when financial history is extended |
| Missing/blocked/not-applicable remain distinct; never silently zero | Live challenge + contract | Tested mapping: not-found→not-available, blocked→blocked, source-error→failed, not-applicable preserved; not-fetched stays explicit in errors because final vocabulary has no not-fetched state; zero values remain available zeros | PASS | Do not collapse states in UI/research layers |
| No fabricated financial values | Live challenge | Official BRREG accounting path is deterministic, not LLM-generated; zero and reporting-period regressions pass through final adapter | PASS baseline | Preserve regression/audit on validation and held-out runs |
| External precision >=95% and no material wrong-company publication | Live challenge | Conservative identity gate + H1c risk guard exist; H1c frozen audit caught and quarantined wrong-domain collisions before merge | OPEN | Run larger zero-overlap external precision audit before claiming threshold |
| Weighted external company recall >=60% | Live challenge | H1c improves verified-site discovery but current qualified external footprint remains far below final recall target | OPEN | Expand only qualified zero-cost external/company-owned signals and measure recall |
| Coverage >=21/35 | Live challenge | Not directly measurable from current official + limited verified-site stack | OPEN | Evaluate after qualified source expansion |
| Overall score >=65/100 | Live challenge | Hidden judge authoritative; local proxy not equivalent | OPEN | Use local proxy for diagnostics only; submit for independent evaluation when gates are supported |
| Idempotent refresh | Live challenge | Final refresh-contract qualification reproduced exactly 2 expected changes and a current→current rerun produced zero changes | PASS | Extend the same normalization when qualified external observations enter refresh |
| Previous snapshot/history preserved | Live challenge | Final `changes[]` preserves previous/current values plus previous/current content hashes and source provenance; deterministic fixture qualification passed | PASS for current tracked fields | Audit external connector refresh semantics later |
| 45-minute wall-clock for 100-company batch | Live challenge | One-command frozen final-evaluator run completed the 100-company agent in 93.331 seconds after frozen inputs were available, versus a 2,400-second internal release ceiling and 2,700-second challenge limit | PASS current final runner | Revalidate whenever qualified acquisition layers are added |
| <=2,000 outbound requests per 100-company batch | Live challenge | Final runner has a structural ceiling of 900 logical requests / 1,800 conservative redirect-charged requests; frozen 100 observed 580 logical / 1,160 conservative requests | PASS current final runner | Preserve structural headroom when adding sources |
| <=$10 third-party API cost per 100-company batch | Live challenge + project decision | One-command frozen final-evaluator run used $0 third-party spend, zero search API requests and no experimental connectors | PASS current final runner | Preserve $0 production constraint unless a qualified provider has measured value |
| Machine-readable run report | README | `run_signalpost_final.py` emits one consolidated machine-readable report covering count, contract, refresh, budget, runtime and canonical site-source accounting | PASS current final runner | Keep report/artifact in release workflow |
| One evaluator command | Live challenge + README | `scripts/run_signalpost_final.py` performs official enrichment, bounded verified site resolution, terminal-envelope construction, output-contract projection, optional refresh attachment, validation and budget enforcement in one command | PASS | Keep experimental connectors outside this release path until separately qualified |
| Source rights documented | Live challenge + starter external model | Acquisition modes/rights gates exist; connector register added in `CONNECTOR_STATUS.md`; final runner uses official/company-owned zero-cost paths only | PARTIAL | No experimental source promoted by relabeling; verify each future production provider |
| Server-side secrets/private keys not committed | Live challenge + how-to-enter | Final strategy currently requires no paid API secrets | PASS current stack | Keep release secret scan even with $0 architecture |
| Safe URL handling | Live challenge | Final site path uses public-URL checks plus a one-redirect ceiling; robots parsing regression is covered after live-run bug discovery | PASS design/tests | Preserve SSRF/redirect regressions for new URL-taking connectors |
| Pinned/reproducible dependencies | README | `uv.lock` exists; `uv sync --locked` passes CI | PASS | Consider pinning CI uv tool version separately |
| Core regression suite | Starter | Full GitHub Actions suite passes with final-orchestrator regressions: 178 tests + 5 subtests | PASS | Required on every PR |
| Live baseline smoke | Starter README | 10-company live run reproduced successfully | PASS | Keep manual/reproducible workflow |
| Frozen 100-company development benchmark | Project plan | Exact manifest/input hashes and failure-bucket report recorded in `BASELINE_100.md`; reused for H1c, output-contract and final-evaluator qualification | PASS | Continue same manifest for before/after development comparisons |
| Search candidates independently verified before publication | Live challenge/starter docs | H1a/H1c candidate discovery is separated from independent fetch + exact identity publication gate | PASS for promoted zero-cost domain paths | Preserve zero-overlap precision audit before any new discovery source |
| UI makes evidence/gaps/changes inspectable | Live challenge UX category | Existing `build_prototype.py` provides substantial static prototype | PARTIAL | Improve after engine/qualified evidence stabilizes |
| Research answers only from supported evidence | Live challenge + starter | Deterministic/evidence-bounded research layer exists | PARTIAL | Extend only with qualified observations; test abstention |
| Models/APIs/licences/caches/hosting assumptions declared | Submission contract | Starter docs + connector-status/project decisions cover current stack | PARTIAL | Produce final release manifest from actual promoted stack |
| Expected cost per 100-company run declared | Submission contract | Locked current final runner is qualified at $0 third-party cost per frozen 100-company run | PASS current final runner | Re-measure only if production source set changes |

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

## Refresh-contract qualification record

- Workflow: `Refresh Contract Qualification`, run `34878326293`.
- Deterministic evaluator-owned fixture: 1 company, `registry_live` + `financials`, 2 old-source requests and 2 new-source requests.
- Expected changes: 2; observed changes: 2; attached final `changes[]` events: 2.
- Changed fields: `registry.employees` and `financials.records`.
- Every change preserves previous/current value, source URL/class, retrieval/effective time, previous/current 64-character content hashes, and current source status.
- Wrong-company events, duplicate field events, unchanged old/new values and invalid hashes are regression-tested and rejected.
- Current→current diff produces zero events and therefore an empty final `changes[]` set.
- Qualification artifact digest: `sha256:e317bdf7612e2327324e34a9895a27d82db89702712c82c7b981ac274d3291cf`.

## Final one-command evaluator qualification record

- Workflow: `Final Evaluator 100 Qualification`, corrected run `34925250107` at branch head `138083dc942917975d6007d1913ee9448ec4458c`.
- Same frozen development manifest SHA-256: `51a96f25f79532b9ba285304d540887e0f17410907909dbe6c85c0b41b8341d3`.
- Exactly 100 unique final objects; 100/100 `run.terminal_status=completed`; internal zero-silent-drop validation PASS.
- 1,568 claims and 1,568 evidence items; contract errors 0; refresh-change errors 0; budget errors 0.
- Request model: 5 official logical requests + at most 4 site logical requests per company; one redirect maximum per logical request; structural challenge-charge ceiling 1,800.
- Observed: 580 logical requests and 1,160 conservative challenge-charged requests, leaving 640 requests of headroom to the internal 1,800 cap and 840 to the challenge's 2,000 cap.
- Wall runtime: 93.331 seconds; internal release ceiling 2,400 seconds; challenge limit 2,700 seconds.
- Third-party cost: $0; search API requests: 0; experimental connectors enabled: false.
- Canonical verified-site accounting: 4 verified sites = 3 H1c deterministic-domain sites + 1 registry-linked site; 96 unresolved. The report derives these counts from final canonical evidence so transient discovery metrics cannot disagree with published profiles.
- Final report consistency gate PASS; all hard-gate workflow checks PASS.
- Qualification artifact digest: `sha256:12843ba6b616fa1999521a1060e764aaeb0ed67f43f1b46ff79a7269e8f97031`.

Update this matrix when a requirement changes state; link the PR/benchmark evidence rather than changing status from memory.
