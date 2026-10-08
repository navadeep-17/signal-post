# V10 M21 — three-cohort source-reach bottleneck audit

Date: 2026-10-08  
Status: **READ-ONLY AUDIT COMPLETE / STOP ZERO-COST MICROFALLBACKS / NEW RETRIEVAL PRIMITIVE REQUIRED**  
Production decision: **NO MERGE / NO PROMOTION / NO FRESH QUALIFICATION**

## Scope and provenance

This is a diagnostic, not a new product candidate. It recomputes available claim counts from **three disjoint, previously consumed** 100-company V8 acquisition artifacts. It does not run acquisition again, touch sealed holdouts, fetch new company pages, promote candidate claims, or infer an official Builderr score.

| Observed cohort | Run | Immutable artifact | ZIP SHA-256 |
|---|---:|---:|---|
| M19 Gate A | `37670190338` | `11505218381` | `45a9fb18b6c8e05e7f7d90106de223fc31cf71e50ba6306d9c72c95118503bc9` |
| M19 Gate B | `37717545307` | `11525046472` | `7439ace3eabb7ad3f951abb91396dac23e26cf04bd1e1d25f12ada625ceb4df6` |
| M20 Gate A | `37720279568` | `11525304908` | `3d00b7fc2399fb7bbe6dd2d438ad689313dccd1850cc429b002d499fcb26e05a` |

Each ZIP digest and embedded frozen cohort manifest SHA is asserted, and the three sets contain **300 distinct organisation numbers**. The source of truth is the available `claims[]` in `baseline-out/output.jsonl`, reconciled against the original `baseline-out/report.json` and retained profile counts; a fetched/available website *candidate* is not counted as a published, verified website. The script also asserts each 100-company run passed its own V8 contract and budget, and that search requests and third-party spend were zero.

Reproduction: download the named ZIP artifacts without modifying them; run:

```bash
python scripts/audit_v10_m21_source_reach.py \
  --m19-a m19-gate-a.zip \
  --m19-b m19-gate-b.zip \
  --m20-a m20-gate-a.zip \
  --output evaluation/v10_m21_source_reach_300.json
```

## Published coverage in the consumed samples

| Available company-level field | M19 A | M19 B | M20 A | Aggregate |
|---|---:|---:|---:|---:|
| `official_website` | 21 | 11 | 9 | **41 / 300** |
| `external.profile_handle` | 11 | 9 | 5 | **25 / 300** |
| `external.contact_email` | 10 | 9 | 3 | **22 / 300** |
| `external.careers_page` | 3 | 1 | 1 | **5 / 300** |
| `external.job_posting` | 0 | 0 | 0 | **0 / 300** |
| `external.company_update` | 1 | 2 | 0 | **3 / 300** |
| `external.workforce_snapshot` | 98 | 98 | 98 | **294 / 300** |
| `official.support_award` | 13 | 5 | 3 | **21 / 300** |

Of the 41 independently qualified websites, 25 had qualifying social-profile handles and 22 had qualifying contact emails. Those conditional rates (61% and 54%) do **not** mean every verified website must have contact/social evidence. They do show why incremental verified-site reach is a prerequisite for substantial first-party recall growth.

## Website acquisition failure tree

- **259 / 300**: no qualifying website source was selected (`selected_sources.none`).
- **41 / 300**: websites selected after full qualification — 18 registry-linked, 22 deterministic legal-name domain and 1 hyphenated-name fallback.
- Website evidence records describe **59 available fetched candidate pages** but only **41 published sites**. The other **18 did not clear all publication gates**; this is not evidence that those 18 are safe to promote. Among those candidates are registered manager, parent, brand and different-entity websites. The exact-owner veto and identity rules must remain intact.
- Hyphenated `.no` fallback: 196 attempts, **1 qualified site** across these three cohorts. Wikidata: 2 candidates total; no selected Wikidata website. Re-running those unchanged methods is not a material new hypothesis.

Operational evidence: observed conservative request charges were **1546**, **1342** and **1388** of 2000 respectively; each run passed under 2400 seconds and $0 cost. However, each 100-company structural *theoretical* request ceiling is **exactly 2000**, not 1546/1342/1388. Observed slack does not authorize an unconditional new call. Any additional source must replace/prove reserved call allocation or change the accounting theorem before it can enter the evaluator.

## M19 and M20 context

- M19 composite registry-domain nomination: +1 verified site/100 on consumed Gate A, 0/100 on disjoint Gate B. Final decision `SHELVE_LOW_YIELD`, PR #169.
- M20 byte-equivalent M4 structured-contact port: 0 new claims/100 on independent Gate A, 0 lost claims or non-contact changes. Final decision `SHELVE_LOW_YIELD`, PR #170; Gate B remains sealed, not run.
- V8/main and fresh qualification have not been changed by this audit.

## Decision and next admissible hypothesis

**Do not start M21 production coding for another URL-format guess, contact/phone projection tweak, downstream page parser or broad feed scan.** The highest-value unsolved part is an independently supportable **company → exact first-party domain** nomination mechanism that reaches materially more companies. A provider result or registry/partner lookup must be treated only as a candidate, never as publication evidence.

A new candidate only warrants a staged experiment after it has all of the following:

1. A *materially new* org-number/domain retrieval signal beyond M14–M20 attempts, with documented rights, retention and reproducible provider account/plan/cost terms if applicable.
2. Independent first-party site fetch and exact Norwegian legal-entity evidence; no name-only publication, parent/brand conflation, directory-result laundering, or lowering of the existing owner veto.
3. A request-slot substitution or other proven worst-case bound **≤2000 per 100**, runtime **≤2400 seconds**, and allowed third-party spend.
4. A small **consumed-development** feasibility screen with a predeclared yield and full manual audit of every candidate publication. This cannot be called fresh validation.
5. If the development screen is material, a separate pre-frozen **zero-overlap transfer** cohort, audited for false positives, old-claim losses and evaluator-visible provenance before any promotion.
6. A final evaluator reproducibility check: the exact retrieval dependency must be available in Builderr's execution environment without relying on unconfigured secrets. Otherwise the design remains an opt-in experiment.

**Current actionability:** blocker-driven. Until such a new source signal or a verified reproducible search-provider contract exists, preserve qualified V8 and do not consume more untouched companies. Revisit with an explicit source-rights/budget/identity feasibility proposal, not a new heuristic by default.

## Interpretation limits

These companies came from already-consumed, deterministically partitioned parts of the same frozen 1,000-company corpus. They are disjoint from each other but **not newly randomized independent qualification samples**. Do not extrapolate the exact 41/300 fraction to Builderr's population or infer the official precision, recall or score. This document diagnoses the observed acquisition bottleneck only.