# M40 — Undercovered information-family feasibility gate (consumed evidence)

**Decision: OFFLINE GAP AUDIT COMPLETE; NO NEW EXTERNAL CONNECTOR QUALIFIED. A narrow careers-link PROJECTION discrepancy is under review. M40 must remain DRAFT and unmerged.**

## Frozen evidence basis

Three SHA-verified, previously consumed V8 M19-A/M19-B/M20-A 100-company artifacts, covering 300 unique existing organisation numbers. Original per-archive ZIP and frozen-company-list digests are checked before analyzing contract claims and retained profiles. No collection, company HTTP, Tavily requests, provider result reuse, official scorer query or fresh cohort was used.

- Consumed sample is NOT independent transfer or untouched release holdout.
- Only explicitly **available**, evidence-ID-backed claims count toward typed company-level family reach.
- External observations must pass existing legal-entity/provenance/rights validation before being counted.
- Unknown, missing or source-error values are never converted to negative or neutral claims.
- Government support awards do not become company news, customer reviews, social posts, or sentiment.
- Workforce snapshots do not become job postings.
- Verified first-party declared profile handles do not imply independent engagement or verified activity.

## Measured previously present information, N=300

| Precisely typed existing evidence | Companies |
|---|---:|
| Workforce snapshot | 294 |
| Verified company website | 41 |
| Company-declared profile handle | 25 |
| First-party site contact email | 22 |
| At least two distinct declared profile platforms | 15 |
| BRREG official support award | 21 |
| Verified homepage careers-link presence claim | 5 |
| First-party company-authored update | 3 |
| Concrete external job posting | 0 |
| Independent rating/review/place evidence | 0 |
| Independent public buzz/engagement/profile-metric evidence | 0 |
| Admissible independently sourced labeled sentiment input | 0 |

This is a local **claim-reach audit**, NOT Builderr's weighted official recall, coverage score, precision score, or a score improvement. `companies_with_publishable_external_observations` largely reflects existing workforce/source observations and is not a review/buzz/sentiment count.

## Conditional first-party source opportunity on same archived profiles

| Retained indicator (only on 41 already exact-verified homepages) | Companies |
|---|---:|
| Homepage explicitly carries a careers link | 6 |
| Homepage carries a news-detail link | 2 |
| Homepage has extracted job-listing candidates | 0 |
| Homepage explicitly marks active hiring | 0 |

The six careers-link homepages should not automatically produce six claims. The project's existing narrow careers projector requires an exact verified homepage with stable final URL, source timestamp/hash, and candidate link provenance pointing to **that same homepage URL and hash**. The claimed field means only the verified company page linked to a careers surface. It does **not** assert an active job, individual vacancy, role, or employee count. The current archived output has five careers-page companies.

## Extra M40 consistency replay — candidate, NOT verified improvement

A read-only replay of `project_careers_page_claims` on the exact original 300 profiles and contracts has zero requests. It compares existing careers-page values to what the unchanged strict projector would currently produce, without altering the original output or publishing its candidate URLs/company identities. The replay finds:

- 6 already-verified company homepages with careers links.
- 1 of the 6 has no careers-page claim in the historical output.
- 0 of the 6 are ineligible under the **current deterministic source-provenance checks**.
- 2 companies have at least one newly replayable URL compared with their historical output, but **only 1 company** is a candidate for *net-new company-level careers-page coverage*.
- 0 existing careers-claim regressions under the replay.
- 0 new claims published; 0 independently manually audited positive additions; **no official scored improvement**.

This **one-company** lead is a narrowly scoped possible projection gap worth an independent private source-level manual audit, not a reason to promote an unreviewed algorithm. Even if confirmed, it is 1/300 company (0.33 percentage points) on a previously consumed population and would not establish broad external recall improvement.

## External-source decision

The project's previously reviewed source landscape is still applicable in this scope:

- **Reviews/place ratings:** prior 100-company Fagfolkguiden screen yielded 0 usable ratings; reused Google-derived review material had uncertain licensing. Google/commercial review APIs conflict with the current no-dollar-API-spend rule. Don't fabricate reviews from company descriptions, official awards, place listings or consumer assumptions.
- **Public engagement/profile metrics:** verified site-declared profile handles have narrow company-level reach, and provider access/ownership/rights plus per-company metrics are not presently qualified. Don't infer engagement from social URL existence.
- **Independent sentiment:** requires substantive licensed independent review/news/mention text and an independently qualified label; none exists in these consumed 300 outputs. No sentiment model by itself can manufacture source coverage.
- **Hiring/dated activity:** published careers links and updates are real but rare. With zero retained job-listing candidate pages and zero hiring markers, repeating the unchanged first-party hiring-crawl proposal has no observed source opportunity. The existing two news links are not automatically company-authored dated news.
- **Official grants/workforce/registries:** already covered and valid, but typed differently from the unsolved families; relabeling them would be score hacking.

There is currently **no measured, legally qualified, zero-dollar, high-reach new independent source** for the three biggest empty families. This is a decision against spending another development cycle on the already-rejected connector designs, not a universal claim that no source could ever exist.

## Next small evidence gate

1. Privately inspect the one *net-new* careers-link replay candidate against its original retained exact-company homepage URL/hash, captured link URL/hash, retrieval time, and source evidence. Check legal-entity identity and redirect/register-domain veto; do not publish source details or identities to Actions logs.
2. If the original source truly proves the narrow claim and contract/canonical/synthesis validators accept it with zero losses, measure +1 genuine company-level careers-link fact on this **consumed** corpus. Keep it in a separate experimental candidate patch and manually audit 100% of the positives.
3. A later disjoint consumed transfer (and preferably separate official evaluator feedback) must show measurable beneficial coverage/score impact with 0 wrong-company, 0 baseline loss and unchanged 100-company request/wall theorem before any `main` merge.
4. Otherwise mark this lead NO-GO and prioritize evidence-bounded UX/synthesis quality gates, since the recorded historical official UX/synthesis scores had more headroom than the currently source-blocked review/buzz/sentiment categories. Do not treat old official scores as current unless re-evaluated.

## Reproducibility / safety

- Draft research PR: [#183](https://github.com/navadeep-17/signal-post/pull/183).
- Audit module: `src/norway_company_agent/v10_m40_offline_family_reach.py`.
- Historic SHA-pinned audit runner: `scripts/run_v10_m40_consumed_family_gap.py`.
- No-network workflow: `.github/workflows/v10-m40-consumed-gap-audit.yml`.
- No production runner/import changes, no secrets, no external GETs, no new paid credits, no plaintext company-source artifacts, no published positives. Qualified V8 and `main` unchanged.
