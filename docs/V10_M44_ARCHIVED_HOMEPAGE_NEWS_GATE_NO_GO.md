# M44 — Zero-request homepage dated-news proof gate (three archived nominations)

**Decision: NO-GO.** No existing archived nomination qualifies even as a strictly structured *human-review candidate*. No article was independently fetched, no new dated-news claim was published, and no official score improvement was measured. Keep branch **DRAFT and unmerged**.

## Frozen experimental input / scope

- Submitted evaluator code reference: `8a20eb2bfc0b315b9553e66395d9be4bc6ad020b`.
- Parent research: M42/M43 previously consumed M19-A/M19-B/M20-A transfer archive ZIPs, SHA-validated by the existing M40 runner; exactly 300 unique existing V8 company outputs and their retained site evidence.
- This is **not** Builderr's private C300 reference set, not a fresh disjoint holdout, and not a score delta.
- Only aggregate statuses and failure reason counts appear in logs. No organisation numbers, article titles, URLs, identity excerpts or article text are printed or uploaded.
- No new company HTTP, search/provider requests, API credits or LLM calls; $0 third-party spend.
- No changes whatsoever to submitted V8 runner, crawl, feed, projection, synthesis, website identity or output-contract code.

## Why this gate was needed

The archived M42 audit found 2 exact-verified websites with 3 nominated news-detail URLs, but **zero retained downloaded news-detail pages**. A first-party homepage's news link only proves the link was present; it does **not** prove a dated news article, its content, or its company-specific publication date. Trying to promote nomination URLs directly is not a legitimate recall improvement.

M44 therefore checks the retained homepage nomination and original first-party homepage source, strictly:

1. website must already be exact-verified and publishable;
2. HTTPS homepage URL and a valid pinned source SHA-256, including matching homepage/nomination URL and hash;
3. HTTPS *exact same hostname* for nominated article URL;
4. preserved `nomination_only = True` provenance;
5. date visible in a bounded local homepage article card, exactly one unambiguous publication-date candidate and no future/stale timestamp;
6. specific linked title actually appears within that local dated card;
7. homepage source explicitly identifies only the **exact nine-digit target legal organisation number**, not a different entity.

Even passing all seven conditions would be **review-only**, never sufficient for an independently fetched article or new published `external.company_update` claim. This is intentionally more conservative than older homepage identity heuristics: absence of an explicit legal number is lack of positive proof for this new claim, not proof the prior company site match is wrong.

## Exact aggregate result, original 300 companies

| Type | Count |
|---|---:|
| Companies in pinned source | 300 |
| Exact-verified websites | 41 |
| Websites with nominated news links | 2 |
| Individual nominated link URLs | 3 |
| Links meeting all source/title/date/legal-entity gates | **0** |
| Independently retained news-detail pages | **0** |
| Additional verified dated article claims / official score uplift | **0 / not measured** |

Non-exclusive failure counts among the three nominations (one link may fail several independent checks):

| Failure reason | Nominations |
|---|---:|
| Homepage lacks exclusive explicit exact-organisation-number evidence in retained text | 3 |
| Specific linked title not contained in the retained dated homepage card | 3 |
| No dated local homepage card context | 2 |
| Insufficiently specific link/anchor title | 2 |
| Dated context exists but no single eligible date is established | 1 |

No responsible publication can be made from the historical snapshots, even if the source website remains otherwise publishable under V8. No content change and no score claim follows.

## Validation

- [M44 archived original-archive audit and focused tests](https://github.com/navadeep-17/signal-post/actions/runs/39005818283) **PASS** — 76 tests after correcting one synthetic test's expected *classification label*, not changing publication criteria.
- Inputs reverified via M40 checksum gates, fully reconstructed from already-consumed original 300 records.
- Source audit: `src/norway_company_agent/v10_m44_homepage_news_proof_gate.py`.
- CLI: `scripts/run_v10_m44_homepage_news_proof_gate.py`.
- Adversarial tests: `tests/test_v10_m44_homepage_news_proof_gate.py`.
- CI workflow: `.github/workflows/v10-m44-homepage-news-card-gate.yml`; branch push only, no manual trigger, no source archive upload, wipes temporary archive copies.
- Baseline full CI: link to exact-head passing run appended after final verification.

## Next decision

**No M44 production change and no revised submission** based on this zero-yield proof screen. Our current next meaningful dependency is an independently validated, legal-entity exact, dated article source with direct content evidence and a positive disjoint score/coverage delta; absent that, retain submitted `8a20eb2` for Soham's pending official C300 review.

Expanding requests to other RSS URLs, using third-party search results or substituting homepage snippets without article corroboration would violate the current promotion criteria unless independently tested, with the 2,000/2,000 theoretical challenge request ceiling and full budget re-proved first. Do not treat a hypothetical new source as success.
