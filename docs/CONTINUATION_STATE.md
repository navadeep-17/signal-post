# Signalpost — Current Continuation State

Last updated: 2026-10-04 (Asia/Kolkata)

Repository state and live GitHub metadata are authoritative over chat history. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; architecture and phase order belong in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Phase-4 production merge:

`07f01734ba9bb5ed850a5a494c6c38f7cdaf66a3`

PR #95 `Phase 4: harden dated activity evidence selection` is **MERGED**.

Lifecycle:

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** no fresh qualification requested; precision-only zero-request hardening
- **MERGED:** yes
- **POST-MERGE GREEN:** yes

Post-merge Baseline CI:

- run `37219278337`: **PASS**
- merge SHA: `07f01734ba9bb5ed850a5a494c6c38f7cdaf66a3`
- full tests, certified-1000 canonical audit, submission-bundle verification and deterministic refresh replay all passed

Open PRs #76, #78 and #84 are historical/experimental and are not the active production path.

## 2. Closed phases and retained state

### Phase 1 — collected-vs-emitted exact BRREG recovery

**CLOSED / QUALIFIED / MERGED / POST-MERGE GREEN**.

Last fresh qualified baseline remains run `37203580574`:

- 100 unique companies, overlap 0
- cohort SHA `4078579d4a581da0b8d56e4d03d567c4032d43e93c8bb94ee3c02b140b651e40`
- 100/100 terminal
- evidence/contract/canonical/synthesis errors: 0
- 666 logical requests
- 1,332/2,000 conservative charge
- runtime 460.916 s
- third-party cost $0
- search API requests 0
- artifact `phasea-final-fresh-disjoint-100-v2`, ID `11304401011`
- digest `sha256:31e12e11f2746dcf8c0b6454ab6052ab44281176363b6934889d22d57a08800b`

### Phase 2 — exact website discovery

**SHELVED / CANDIDATE-SOURCE CONSTRAINED** under current $0 rights-safe sources.

Failure funnel on frozen 100:

- H1c deterministic `.no`: 96 attempts, 79 blocked, 78 DNS non-resolution, 12 loaded, 3 exact sites verified
- H1g hyphenated `.no`: 73 attempts, 73 DNS non-resolution, 0 verified

Rejected/do-not-repeat without genuinely new evidence:

- guessed `.com` and broader legal-name domain generation
- annual-report domain hints
- Norid public lookup because rights/purpose terms are incompatible
- exact-parent subunit homepage hints: 0/3
- exact-parent subunit email domains: 0/10
- same-domain secondary identity verification: 0/4
- NAV exact-org vacancy screen: 0/100 target companies after complete 180-day traversal
- provider/model-search PRs #78/#84 unless provider/key/budget constraints materially change

### Phase 3 — sitemap/RSS dated-activity expansion

**DROP / SHELVED** on the consumed cohort.

- sitemap run `37215062164`, artifact `11308151116`: 0 accepted dated-activity companies
- hardened RSS run `37215793652`, artifact `11308790825`: 0 precision-clean dated-activity companies

The RSS experiment exposed the date-selection false-positive class fixed by Phase 4.

### Phase 4 — page-level dated-activity evidence hardening

**IMPLEMENTED + TESTED + MERGED + POST-MERGE GREEN**.

Implemented:

- typed semantic ranking of page-local publication-date candidates;
- explicit publication metadata wins over generic/dynamic labelled dates;
- same-rank conflicting dates abstain;
- unstructured page text is accepted only when exactly one unique date remains;
- generic CMS placeholder updates such as WordPress `Hello world!` are rejected;
- retained activity evidence records date extraction method and raw page-local date evidence;
- no new source, request, identity relaxation or third-party spend.

Validation:

- measured semantics head `a220089fccefd63f88555d675194ebefcdd44723`
- consumed diff run `37217368930`: PASS
- artifact `phase4-activity-evidence-consumed-diff`, ID `11308328355`
- artifact digest `sha256:ddcf4e328edab217a016122801f1ad16f4f60c0a80d3e106b09ba5f67ed59da0`
- frozen 100: jobs 0 -> 0, updates 0 -> 0
- added update URLs 0; dropped update URLs 0; date changes 0
- network requests added 0; search requests added 0; cost added $0
- `precision_monotonic=true`
- docs-inclusive PR head Baseline CI `37219207340`: PASS
- merge commit `07f01734ba9bb5ed850a5a494c6c38f7cdaf66a3`
- post-merge Baseline CI `37219278337`: PASS

## 3. Precision and budget invariants

- exact organisation number remains the legal-entity anchor;
- candidate generation is never publication proof;
- parent/subsidiary/subunit relation alone never authorizes inheritance;
- wrong-company publication is a hard failure;
- exact page URL + retrieval/hash provenance remains mandatory;
- dates must be page-local and semantically tied to the article/update;
- sitemap/feed/archive dates cannot independently publish an activity fact;
- missing/blocked/ambiguous remains explicit;
- third-party API spend remains $0;
- four logical site requests/profile remains the site ceiling;
- fresh cohorts remain reserved for promotion of meaningful new transfer, not source ideation.

## 4. Current blockers

1. Exact website reach remains about 7–8/100 under current rights-safe $0 sources.
2. Phase-2 candidate generation is dominated by non-resolving speculative domains.
3. Phase-3 sitemap/RSS expansion produced zero precision-clean net-new activity coverage.
4. No next deterministic source/family has yet passed rights + exact-ID + reach + budget screening.

## 5. Exact next 1–3 actions

1. Run a **consumed-only source-selection audit**, not a connector implementation. Compare plausible deterministic official/rights-safe sources such as Doffin, Støtteregisteret and Patentstyret on: rights, exact organisation-number join, likely company-level reach, scored-family value, freshness and request/runtime cost.
2. Select at most one source/family only if it has a credible path to meaningful net-new company coverage without weakening exact-company precision or exceeding the 2,000/100 theorem. Record PROMOTE/RETUNE/SHELVE/DROP in the repository before implementation.
3. If one source passes the selection gate, implement it on a consumed cohort first. Otherwise advance to another roadmap phase rather than forcing a low-yield connector. **No fresh cohort yet.**

## 6. NEXT

**NEXT: consumed-only deterministic source/family selection audit. Screen rights, exact-ID join quality, likely evaluator-shaped reach and budget for Doffin, Støtteregisteret, Patentstyret or another official source before implementing any new connector.**
