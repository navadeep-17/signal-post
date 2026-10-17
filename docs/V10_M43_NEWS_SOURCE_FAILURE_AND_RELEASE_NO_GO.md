# M43 — Prior-consumed first-party dated-news source failure breakdown and release go/no-go

**Decision: No demonstrable net-new correct claim; do not merge, retune source priorities, or submit M43.**

## Why now

The October 17 C300 evaluation notes provided a precise deadline for another revision (October 18) but no completed official synthesis / UX verdict. Soham's direct evidence note to Navadeep v8 says zero unmatched claims and zero failed product checks on current retained evidence; synthesis and official scoring remained pending. The prior submitted reference is `8a20eb2bfc0b315b9553e66395d9be4bc6ad020b`. Its news/site/precision/runner Git blobs are unchanged by the M42/M43 audit.

Do not conflate Builderr private C300 verified-news denominator with the three archived M19-A/B/M20-A 100-company cohorts. The latter are **previously consumed development evidence**, not fresh scored transfer.

## M43 fixed-count source-status audit on original N=300

M43 uses exactly the same 300 source profiles, frozen manifest hash checks and no-network replay as M42, counts only `website.status = available` and exact-site identity `publishable == true`:

| Archived source outcome on 41 exact-verified company websites | Companies |
|---|---:|
| Feed returned current, eligible dated entries | 3 |
| Feed URL returned explicit HTTP 404 or 410 | 18 |
| Feed fetched/parsed but yielded no qualifying dated same-site entries | 9 |
| No retained feed attempt/outcome | 7 |
| Non-404 HTTP source error | 1 |
| `not_found` without a more specific qualifying source reason | 3 |
| **Total** | **41** |

The available feeds furnished the same **8 already-published** update claims across 3 company profiles from M42. Exactly **2** verified homepages had a nominated news article URL; **both** had no retained feed attempt and no independently retained article detail page. M42 separately confirmed **0** strict page-backed publication candidates and **0** new claims in a no-network replay of the current postprojection. A nominated URL alone carries no publication date or independently fetched article content.

The status categories are *observation types* not proof of the absence of all news on these 41 companies. A `/feed/` 404 does not establish that `/rss.xml`, `/atom.xml`, a different article path or a third-party licensed news source contains an exact-company dated article. The 7 unattempted sources must remain unknown. The retained profiles do not preserve why the two nominated news pages failed to yield retained article evidence; do not assert network failure or budget exhaustion without recorded attempt metrics.

## What the research rules out now

- **Projection-only fix:** M42 replay found 0 lost original updates, 0 newly eligible updates and 0 precision-guard removal of available update claims.
- **Expanding `/feed/` blindly:** 18 explicit 404/410 failures and 9 empty/unqualified outcomes make the same exact path low-yield; retuning to other paths lacks stored article body/date proof and demands new network requests and separate validation.
- **News-link nomination:** 2 websites with 3 nominated URLs, 0 independently fetched article snapshots retained. No candidate can be legitimately promoted from a URL alone.
- **Reallocating the final two-request slot:** existing 100-company worst-case conservative request ceiling is exactly 2,000/2,000. Reallocation is theoretically possible but not justified by a demonstrable successful new dated article in this source record.
- **Promotion claim:** no new company news, no official score delta, no disjoint holdout validation, no evidence permitting a revised submission to claim better performance.

## Safe next work and decision deadline

1. Keep the exact submitted `8a20eb2`, qualified V8, and current `main` unchanged.
2. If Builderr supplies the exact failed dated-news matched company/article evidence (company ID, legal exactness, article URL, date and site evidence), **privately** test ONE source and then prove the complete coverage, precision, budget, disjoint-transfer and code-score delta. Do not automatically hard-code any public examples.
3. Without a positive independent validation before Oct 18, **do not submit a speculative revised SHA**. Request or await the official C300 synthesis/UX evaluation outcome, and protect zero wrong-company claims.
4. Continue offline work on precision-safe legitimate alternative source strategy only after explicit proof of a source with transferable coverage and $0 per official run.

## Implementation, testing, privacy

- Research helper: `src/norway_company_agent/v10_m43_archived_news_source_failures.py`
- Original-SHA-pinned offline runner: `scripts/run_v10_m43_archived_news_source_failures.py`
- Synthetic negative tests: `tests/test_v10_m43_archived_news_source_failures.py`
- Read-only archived pipeline: `.github/workflows/v10-m42-archived-news-funnel.yml`
- Reused M42 tests and original archived proofs; no plaintext source outputs or archived artifact uploads.
- [M42+M43 original-archive workflow](https://github.com/navadeep-17/signal-post/actions/runs/39005258387), 64 focused tests PASS.
- Current experiment remains DRAFT PR #185. No modified production files; no company/provider web requests, no LLM/API credits, no source identities in output; release is not automatically eligible for promotion.
