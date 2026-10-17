# M42 — Dated-news source funnel on frozen, already-consumed V8 evidence

**Decision: OFFLINE ROOT-CAUSE AUDIT COMPLETE — NO NEW PUBLICATION / NO PROVEN SCORE UPLIFT / DO NOT MERGE.**

## Goal, provenance and boundaries

Soham's October 14 C300 directional feedback says no dated-news item matched the verified reference pool. The October 17 emails say the stricter C300 scoring is directional; full synthesis and official qualification remain pending. These emails do **not** identify which news candidate(s) in the exact Builderr C300 reference pool would have matched. Do not conflate local dated company updates with verified scored dated news.

M42 audits three ORIGINAL, SHA-pinned, ALREADY CONSUMED V8 transfer archives, M19-A/M19-B/M20-A, 100 companies each and 300 unique exact Norwegian organisation numbers. All archived ZIP bytes and frozen manifests are hash validated by the existing M40 audit before reuse. Original contract source records, organisation numbers, URLs, company names and article bodies are never written to logs or published.

**Critical SHA invariance check:** The exact Git blob hashes of all seven production files for news discovery, feed parsing/projection, first-party activity, external precision guard and V8 runner are identical between submitted SHA `8a20eb2bfc0b315b9553e66395d9be4bc6ad020b` and the M42 experiment's branch base. M42 adds only separate offline test/audit files; the original production implementation is unchanged.

The M19/M20 archives are prior-consumed development data, NOT the private C300 reference pool, NOT an untouched holdout and NOT proof of a higher official score. No web, search, paid provider, scorer or new company requests are made.

## Audited source-to-output funnel (N=300)

| Stage | Exact archived observation |
|---|---:|
| Original terminal companies audited | 300 |
| Exact-verified company websites | 41 |
| Exact homepages with news-link nominations | 2 |
| Total qualifying homepage news-link nominations | 3 |
| Successfully retained separately fetched news-detail pages | 0 |
| Strict eligible dated update facts from page detail evidence | 0 |
| Verified sites with recorded first-party feed attempt/outcome | 34 |
| Verified sites with available qualifying RSS/Atom feed | 3 |
| Accepted dated RSS/Atom entries | 8 |
| Companies with accepted dated RSS/Atom entries | 3 |
| Companies with previously published first-party company updates | 3 |
| Previously published typed `external.company_update` claims | 8 |
| Published feed-backed update claims | 8 |
| Published page-backed or unidentified-method update claims | 0 |

Among the 41 exact sites, archived feed outcomes: **3 available, 30 `not_found`, 1 `source_error`, 7 with no retained feed attempt**. `not_found` can mean an HTTP 404/410 or a fetched feed without any strictly eligible current dated same-site entry; it does not by itself establish that all 30 companies lacked feeds. A homepage URL nomination is **not** verified dated news, and a missing retained detail page does not reveal whether a fetch was attempted but failed or never attempted.

## Submitted code path: source reach is the visible bottleneck

1. Website collection/identity first: only exact verified company sites may nominate source-owned news or feeds. Only **41/300** previously passed this stage.
2. Homepage news candidate: `extract_news_detail_links` nominates a limited selection of same-domain detail links using a specific news-path pattern or homepage-card visible date. `_attach_bounded_news_detail` attempts only the first nomination when its two-request slot is available. In the original 300 archived profiles, **2** homepages nominated links but **0** news-detail pages were retained, so the strict page-date projector had **0** eligible page-backed updates.
3. Site feed: `fetch_verified_activity_feed` in submitted V8 attempts **only the verified host's `/feed/`** when the existing request allocator can spare a two-request slot. RSS/Atom entries need a specific title, direct same-site entry URL, explicit valid publication date and provenance. On these original 300 companies, **34** exact websites retained feed evidence, only **3** provided eligible entries, and **8** entries were originally published across those **3** companies.
4. Projection: `project_first_party_feed_updates`, `project_first_party_activity_provenance`, `project_external_precision_guard` and canonical/synthesis mapping are deterministic and add no network calls. Replaying the existing feed projector and precision guard against the **original** 300 contracts and retained profiles yielded:
   - **0** additional pre-guard dated-update candidate claims;
   - **0** additional post-guard dated-update candidate claims;
   - **0** dated-update claims removed by the precision guard;
   - **0** original dated-update claims lost under this replay.

**Diagnosis in this scope:** the visible gap lies **upstream in exact-company site coverage and qualifying dated-source capture**, not in lost available company-update claims during the existing final news projection. This is a measured statement about *these prior-consumed 300*, not a claim about Builderr's private C300 evaluator sample. Eight valid internal feed-backed updates do not mean eight Builderr-matched dated-news facts.

## Do NOT promote any proposed shortcut

- Never treat a news category link or homepage nomination as a dated article.
- Never relabel an official registry change, support award, social profile handle, or undated page as published news.
- Never infer missing news to be zero or negative.
- Never treat an RSS entry's article URL as independently fetched detail-page evidence when only the feed was fetched.
- Do not add unconditional website/search requests: the qualified V8 theoretical conservative bound remains **2,000/2,000 challenge charges per 100 companies**, **2,400 seconds**, **$0 paid provider**.
- Do not tune /feed/ to arbitrary additional endpoints or loosen identity/date semantics without an isolated consumed-source gain, re-proved structural request ceiling, adversarial source audit and independent disjoint transfer.

## Outcome and next experiment selection

1. **M42 root-cause review: PASS**. [SHA-pinned original-archive audit and 52 focused tests](https://github.com/navadeep-17/signal-post/actions/runs/39004682649). Artifact source data held only temporarily on the private runner and wiped.
2. **Score uplift: none proven**. Zero new claims or external requests. Production V8 and submitted SHA are immutable.
3. The next potentially useful research task is to **screen a genuinely different, licensed $0 dated-news source or a proven zero-extra-request source path** on already-consumed exact-company records, with explicit title + article URL + date + exact legal-entity verification. A candidate URL alone is not a positive. A source claiming to cover these 41 sites is not enough if none of its articles matches exact entities and dates.
4. Even after a positive development screen, submit nothing until company-level independent evidence audit, zero incorrect-company assertions, unchanged/valid request-time-cost theorem, disjoint transfer and measured positive delta. Otherwise **NO-GO**.

## Reproducibility and confidentiality

- Auditor: `src/norway_company_agent/v10_m42_archived_news_funnel.py`.
- Archive runner: `scripts/run_v10_m42_archived_news_funnel.py`.
- Tests: `tests/test_v10_m42_archived_news_funnel.py`, prior strict news/feed/precision tests.
- Workflow: `.github/workflows/v10-m42-archived-news-funnel.yml`, isolated experimental branch only, GitHub archival downloads only, no secret source providers, no uploaded plaintext artifacts.
- M42 is a research deliverable in a separate DRAFT PR. No push to submitted `8a20eb2`, qualified V8 or `main`.
