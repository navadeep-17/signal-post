# Signalpost — Current Continuation State

Last updated: 2026-10-04 (Asia/Kolkata)

Repository state and live GitHub metadata are authoritative over chat history. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; architecture and phase order belong in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Live `main` observed before this branch-state update:

`266fc6c3f32f97c31bea1a33a93a0728b164f3ea`

Active production candidate:

- branch: `feature/phase4-activity-date-evidence-hardening`
- PR: #95, `Phase 4: harden dated activity evidence selection`
- PR state before this docs update: open draft, mergeable
- release-shaped code/test head before docs-only updates: `a4b8789a746f6e194186db1ea7dd2a40c78bf7b9`
- measured semantics head: `a220089fccefd63f88555d675194ebefcdd44723`
- active lifecycle: **IMPLEMENTED + TESTED / MERGE PENDING / NOT FRESH-QUALIFIED / NOT MERGED**

Open PRs #76, #78 and #84 remain historical/experimental and are not the active production path.

## 2. Lifecycle state

### Phase 1 — collected-vs-emitted exact BRREG recovery

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** yes
- **MERGED:** yes
- **POST-MERGE GREEN:** yes

Phase 1 is closed.

### Phase 2 — exact website-discovery improvement

- **IMPLEMENTED:** experiment-only strategies
- **TESTED:** yes
- **QUALIFIED:** no
- **MERGED:** no
- **POST-MERGE GREEN:** n/a
- **STATE:** **SHELVED / CANDIDATE-SOURCE CONSTRAINED** under current $0 rights-safe sources

Measured failure funnel on the frozen 100:

- H1c deterministic `.no`: 96 attempts, 79 blocked, 78 DNS non-resolution, 12 loaded, 3 exact sites verified
- H1g hyphenated `.no`: 73 attempts, 73 DNS non-resolution, 0 verified

Rejected paths include Norid rights-incompatible lookup, subunit homepage 0/3, subunit email-domain 0/10, same-domain secondary identity 0/4 and NAV exact-org vacancy feed 0/100 target companies.

### Phase 3 — bounded sitemap/RSS dated-activity expansion

- **IMPLEMENTED:** experiment-only
- **TESTED:** yes
- **QUALIFIED:** no
- **MERGED:** no
- **POST-MERGE GREEN:** n/a
- **STATE:** **DROP / SHELVED**

Sitemap and RSS/Atom screens both produced zero precision-clean net-new dated-activity companies. The RSS screen exposed the date-selection precision defect addressed by Phase 4.

### Phase 4 — page-level dated-activity evidence hardening

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** no fresh qualification requested; this is a precision-only, zero-request hardening phase
- **MERGED:** no
- **POST-MERGE GREEN:** n/a
- **STATE:** **MERGE PENDING**

Implemented behavior:

- semantically ranked page-local publication-date candidates;
- explicit publication metadata wins over generic/dynamic labelled dates;
- same-rank conflicting publication dates abstain;
- unstructured page text is usable only when exactly one unique date remains;
- generic CMS placeholder titles/content such as WordPress `Hello world!` are rejected;
- retained company-update evidence records the selected date method and raw page-local date evidence;
- no new source, network request or identity relaxation was added.

## 3. Phase 4 test and measurement evidence

Exact-head Baseline CI:

- run `37217488481`: **PASS**
- exact release-shaped head: `a4b8789a746f6e194186db1ea7dd2a40c78bf7b9`
- full regressions and repository baseline checks passed

Consumed-cohort deterministic diff:

- measured semantics head: `a220089fccefd63f88555d675194ebefcdd44723`
- run `37217368930`: **PASS**
- artifact: `phase4-activity-evidence-consumed-diff`
- artifact ID: `11308328355`
- artifact digest: `sha256:ddcf4e328edab217a016122801f1ad16f4f60c0a80d3e106b09ba5f67ed59da0`
- frozen profiles: 100
- baseline jobs: 0; Phase-4 jobs: 0
- baseline updates: 0; Phase-4 updates: 0
- added update URLs: 0
- dropped update URLs: 0
- publication-date changes: 0
- network requests added: 0
- third-party cost added: $0
- search API requests added: 0
- `precision_monotonic=true`

The final release-shaped head differs from the measured semantics head only by removing the one-off measurement workflow. Production/test semantics are unchanged.

Adversarial regressions cover:

- strong publication metadata versus a conflicting dynamic/labelled date;
- equal-strength conflicting publication dates -> abstain;
- unique unstructured date preservation;
- multiple weak text dates -> abstain;
- standard WordPress/CMS placeholder rejection.

## 4. Retained qualified production baseline

Second untouched Phase-A qualification run `37203580574` remains the last fresh qualified production baseline:

- 100 unique, overlap 0
- cohort SHA `4078579d4a581da0b8d56e4d03d567c4032d43e93c8bb94ee3c02b140b651e40`
- 100/100 terminal
- evidence/contract/canonical/synthesis errors: 0
- logical requests: 666
- conservative charge: 1,332/2,000
- runtime: 460.916 s
- third-party cost: $0
- search API requests: 0
- artifact `phasea-final-fresh-disjoint-100-v2`, ID `11304401011`
- digest `sha256:31e12e11f2746dcf8c0b6454ab6052ab44281176363b6934889d22d57a08800b`

Phase 4 does not change this request theorem.

## 5. Precision and budget invariants

- exact organisation number remains the legal-entity anchor;
- candidate generation is never publication proof;
- wrong-company publication is a hard failure;
- exact page URL + retrieval/hash provenance is mandatory;
- dates must be page-local and semantically tied to the article/update;
- archive/sitemap/feed dates cannot independently publish a fact;
- missing/blocked/ambiguous stays explicit;
- third-party API spend remains $0;
- four logical site requests/profile remains the production site ceiling;
- fresh cohorts are reserved for changes with meaningful transfer, not this precision-only hardening.

## 6. Known blockers

1. Exact website reach remains about 7–8/100 under current rights-safe $0 sources.
2. Phase-2 candidate generation is dominated by non-resolving speculative domains.
3. Phase-3 sitemap/RSS acquisition added zero precision-clean company coverage.
4. No new deterministic high-yield family/source has yet passed rights + exact-ID + reach screening after Phase 4.

## 7. Exact next 1–3 actions

1. Update PR #95 metadata to reflect TESTED status, mark it ready and merge only with the exact tested release-shaped semantics.
2. Verify post-merge Baseline CI on `main`; then update this state with the merge SHA and post-merge run ID and mark Phase 4 **MERGED + POST-MERGE GREEN**.
3. After Phase 4 closes, run a consumed-only source-selection audit for the next deterministic high-yield exact-ID family/source. Screen rights, expected company reach, exact-ID join quality and request cost before implementing any connector. No fresh cohort yet.

## 8. NEXT

**NEXT: finish the Phase-4 merge/post-merge gate for PR #95. After it is POST-MERGE GREEN, choose the next deterministic high-yield exact-ID source/family by a rights/reach/budget screen; do not return to speculative domain generation.**
