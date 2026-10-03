# V7 M2a — next recall-source shortlist

Date: 2026-10-03

Base production SHA: `d783b3423870a10ea7da3eafedad8ea0f1c3993b`

## Decision

**NO-GO for M2b at this time. Do not start another source connector or spend a fresh qualification cohort.**

The three strongest remaining zero-cost/exact-identity candidates were rechecked against the current V7 score-lift objective. None currently clears the pre-screen bar for a 10–20 company feasibility implementation.

This is an intentional milestone result, not a failure. M2a exists to prevent expensive connector work when the source economics or score relevance are not yet strong enough.

## Promotion bar

A source advances to M2b only if it can plausibly satisfy all of the following before production coding:

1. unlocks a genuinely unsolved Builderr-relevant information family;
2. permits the intended acquisition/publication path;
3. supports exact legal-entity attribution without relaxing identity rules;
4. stays within the project's $0 third-party API policy;
5. has evidence suggesting roughly 5–10% random-company reach, or unusually high evaluator value;
6. can fit the 100-company request/runtime budget with headroom;
7. supports deterministic evidence and refresh semantics.

These are consistent with `FINAL_SOURCE_LANDSCAPE_AUDIT.md` and `CONNECTOR_STATUS.md`.

## Candidate comparison

| Candidate | Rights / access | Exact identity route | Evidence on reach / request economics | Scored family unlocked | M2a decision |
|---|---|---|---|---|---|
| NAV Arbeidsplassen job-ad API | Strong. NAV states the job-ad API is free and may be used to republish/display job ads or for analytics, subject to update/removal and privacy obligations. | Potentially strong where vacancy employer organisation number is available, with BRREG subunit-to-main verification. | Already measured in H2i: 20 targets, 30,000 feed items traversed, 54 logical requests, 3 vacancy-detail requests, **0 exact active-job matches / 20 companies**. Production workforce coverage is already near-saturated, reducing incremental value. | Direct hiring/job-posting semantics; strongest semantic fit of the three. | **NO-GO unchanged.** Do not repeat broad feed scanning. Reopen only if NAV exposes a materially different exact-org retrieval/index route that avoids the measured scan cost and there is evidence of better random-company reach. |
| Doffin procurement announcements | Strong open-data basis. Data.norge currently lists a public CSV distribution under CC BY 4.0, updated monthly; no API is registered for that dataset. Doffin itself describes distribution to API/Doffindata, but public acquisition mechanics are not a stronger path than the existing open dataset for this milestone. | Potentially exact only where supplier/participant organisation numbers are actually present. DFØ notes supplier org numbers are desirable for secure identification, but result publication and supplier detail are incomplete/partly voluntary. | Prior source audit already classified random-company reach as sector-biased/uncertain. DFØ states competition results are published in fewer than half of competitions. | Procurement/commercial activity, not a direct substitute for reviews, social engagement, sentiment, hiring, or dated company-owned news. | **NO-GO.** Useful product intelligence, but insufficient score alignment and uncertain random-company supplier coverage. |
| Patentstyret open patent/trademark/design data | Strong. Official API data is free and published under NLOD 2.0 with attribution requirements. | Strong where rights are linked to a Norwegian organisation number; official `IprCasesByCompany` endpoint is specifically designed for company portfolios. | Potentially meaningful for IP-owning firms, but no project evidence of broad random-company reach and likely structurally concentrated in a subset of firms. | IP/product intelligence. It does not honestly become review, buzz/engagement, sentiment, hiring, or company-news evidence. | **NO-GO for score-lift M2.** Keep deferred for future product intelligence rather than force it into recall scoring. |

## Why NAV is not promoted despite being the best semantic fit

NAV remains the only candidate here that directly represents a currently valuable fact family: concrete active job postings. Its public API terms remain compatible with zero-cost use and republication.

However, the project already ran the required kind of cheap feasibility screen:

- 20 companies;
- 90-day lookback;
- 30 feed pages / 30,000 feed items;
- 19,972 active headers;
- 7 candidate employer headers;
- 3 detail requests;
- 0 exact organisation-number matches;
- 0/20 companies with an exact active job;
- 54 logical requests;
- $0 third-party cost.

That measured result is below the project's 5–10% random-company promotion heuristic and has poor information gained per request. Re-running the same strategy on another 10–20 companies would not be a new hypothesis.

A future NAV revisit requires a **materially new retrieval primitive**, for example an official exact-employer organisation-number index/query or an equivalent batch route that changes request economics. A renamed endpoint or another broad feed scan is not sufficient new evidence.

## Why Doffin is not promoted

Doffin has attractive open-data rights, but the company-side identity signal is not reliably complete enough for a random-company recall milestone. DFØ has explicitly noted that results are published for fewer than half of competitions, and organisation numbers for bidders/suppliers are recommended for secure identification rather than guaranteed across all records.

Even when exact supplier evidence exists, a procurement award is legitimate commercial/public-sector activity; it must not be relabelled as a review, social post, engagement metric, sentiment, hiring fact, or company-authored dated update merely to increase a score.

## Why Patentstyret is not promoted

Patentstyret has the cleanest combination of rights and exact-company lookup among the deferred sources. That makes it a good future product-intelligence source, but a weak V7 score-lift source. IP rights are real facts, yet they do not resolve the information families currently driving the score gap.

Adding a technically excellent but weakly scored connector would increase system complexity, refresh obligations and evidence surface without a justified expected qualification lift.

## M2 outcome

Because no candidate clears the M2a promotion bar:

- **M2b — 10–20 company feasibility screen: SKIPPED**;
- **M2c — fresh transfer qualification: NOT SPENT**;
- **M2d — production integration: NOT STARTED**.

No new source code, network dependency, request class, API key, fresh cohort, or publication semantics are introduced by M2.

## Next roadmap action

Proceed according to the serial micro-milestone plan:

1. Do **not** run M3 website discovery unless a genuinely new candidate signal appears. Previously rejected `.com` guessing, tested ML/rule ranking, annual-report domain nomination, and BRREG subunit website hints remain closed hypotheses.
2. With no new website-discovery signal currently present, the next actionable production phase is **M4a — rebase/compatibility of the existing V6 UI onto current `main`**, without a visual redesign or backend feature expansion.

## References

Project evidence:

- `docs/FINAL_SOURCE_LANDSCAPE_AUDIT.md`
- `docs/CONNECTOR_STATUS.md`

Current public source references rechecked 2026-10-03:

- NAV job-ad API terms: https://arbeidsplassen.nav.no/vilkar-api
- Patentstyret open-data documentation: https://developer.patentstyret.no/
- Patentstyret API docs: https://developer.patentstyret.no/docs-open-data
- Doffin open dataset metadata: https://data.norge.no/nb/datasets/a77b0408-85f9-3e12-8a66-8d500b492e9d/kunngjoringer-av-offentlig-anskaffelser
- DFØ note on procurement-result/supplier data completeness: https://www.anskaffelser.no/nyhetsarkiv/publisering-av-anskaffelsesdata
