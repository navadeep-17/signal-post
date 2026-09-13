# Frozen 100-company baseline

Run date: 2026-09-13

Purpose: measure the untouched Builderr research pipeline on a deterministic 100-company development slice before implementing any competitive feature.

## Frozen inputs

- Selection seed: `20260823`
- Entry manifest: deterministic 1,000-company sample from Builderr's frozen public universe
- Development slice: first 100 rows of that deterministic 1,000-company manifest
- Development manifest SHA-256: `51a96f25f79532b9ba285304d540887e0f17410907909dbe6c85c0b41b8341d3`
- Full 1,000 manifest SHA-256: `01d262523f3b1fe71dc7e18b8f7675a866d3a79042e072b4961b0322fe1033b8`
- Builderr universe SHA-256 observed by this run: `1c89710e5b01f8617e86d09fbdff4a52f2f8dbbba297e74f7164b5984f5a0384`
- BRREG bulk snapshot SHA-256: `1817f874fe09747c63207128d341a0b461c1596d070b2e08172cffffa1bb6732`

Feature comparisons must reuse the same development manifest. If the official-data snapshot changes, report that change rather than pretending the comparison is identical.

## Runner result

- Expected companies: 100
- Terminal internal envelopes: 100
- Duplicate organisation numbers: 0
- Silent drops: 0
- Built-in validation: PASS
- Core agent start: `2026-09-13T17:53:23.497144Z`
- Core agent complete: `2026-09-13T17:54:25.257397Z`
- Research requests: 536
- Downloaded response bytes counted by runner: 2,274,606
- Request latency p50: 569 ms
- Request latency p95: 614 ms
- Per-company requests: min 5, median 5, p95 7, max 15, mean 5.36

The large BRREG snapshot download occurs before the timed core run and dominated GitHub Actions setup time. Keep input-snapshot acquisition separate from agent request/runtime analysis.

## Official foundation coverage

| Module | Result |
|---|---:|
| Registry | 100 available |
| Accounting obligation | 100 available |
| Registry live | 100 available |
| Financials | 100 available |
| Roles | 100 available |
| Locations | 100 available |
| Group | 8 available, 92 not found |

This supports the earlier decision not to spend early development time rewriting the official-data foundation.

## Website discovery is the dominant measured gap

Registry website field:

- Missing: **93/100**
- Present: **7/100**

Website module outcome:

- `not_found`: 93
- `available`: 6
- `blocked`: 1

Identity assessment for the seven registry-linked website cases:

- exact: **2**
- review: **1**
- related/uncertain: **3**
- blocked before assessment: **1**

The six fetched websites yielded 16 targeted internal pages total. No publishable social links survived the current identity gates in this slice.

This makes "crawl existing registry websites more deeply" a low-reach first optimization: only seven of the 100 companies even had a registry website seed. The first high-leverage problem is therefore **recovering candidate official domains for companies whose registry website is missing, followed by conservative independent verification**.

## First feature hypothesis

**Hypothesis H1:** A permitted search-provider discovery stage for missing registry websites, followed by the existing independent page fetch + exact-entity identity gate, can materially increase verified company-site coverage without increasing wrong-company publications.

This is a hypothesis, not yet a promoted feature.

The starter's `docs/external-connectors.md` recommends the same shape: query search only when the registry website is absent/invalid/dead; treat provider results as transient candidates; independently crawl the candidate; publish only exact-entity proof. `run_brave_discovery.py` already implements an experimental/transient version of that flow.

## H1 acceptance gate

Do not integrate discovery into the competition runner merely because it finds URLs. Before promotion:

1. Confirm the provider plan/terms permit this use and retention model.
2. Build a frozen labelled domain-discovery audit with hard parent/brand/franchise/namesake negatives.
3. Keep raw provider results transient if storage rights do not allow persistence.
4. Independently fetch every selected candidate.
5. Require exact-entity page proof before canonical website promotion.
6. Measure wrong-domain publications and supported-domain recall on a zero-overlap validation slice.
7. Measure request/runtime/API-cost impact against the final 100-company budget.
8. Add regressions for dangerous false positives before promotion.

The starter's own recommended production discovery gate is stricter than the challenge minimum (99.5% exact-domain precision, zero wrong-company publications). We should retain that conservative internal target unless evidence justifies a documented change.

## Secondary gap

Even among registry-provided websites, only 2/7 were exact under the current identity gate. After domain discovery is measurable, analyze these false-negative/review cases to determine whether additional corroborating evidence (organisation number, address, phone, municipality, verified cross-links) can safely improve exact-match recall without weakening precision.

## Confirmed schema gap

The benchmark again confirms that the executable batch runner emits the starter's internal `state/modules/profile` envelope. `OUTPUT_CONTRACT.md` documents a different final `run/claims/evidence/changes/errors/operations` structure. No adapter implementing `terminal_status`, `evidence_ids` or `third_party_cost_usd` was found in repository search.

This remains a required compatibility task, but it should not be mixed into H1; output projection gets its own bounded PR and contract tests.
