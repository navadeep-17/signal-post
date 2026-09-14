# Connector qualification status

This file is the publication-rights and readiness register for external evidence. Code existing in the repository does not by itself make a source competition-safe or publishable.

Status meanings:

- **QUALIFIED BASELINE** — suitable for baseline publication under the starter's current evidence/identity rules.
- **CONDITIONAL** — usable only after an exact-source/company gate or field-specific requirement passes.
- **EXPERIMENTAL** — useful for local measurement, not final publication yet.
- **PLANNED** — preferred production acquisition path not yet implemented/qualified.
- **BLOCKED** — do not use for qualification/production under the currently reviewed rights or technical conditions.
- **DEFERRED** — not worth prioritizing until higher-value gaps are solved.

| Source / connector | Current code/path | Status | Publication rule / next action |
|---|---|---|---|
| Brønnøysund bulk/live registry | `official.py`, `batch.py` | QUALIFIED BASELINE | Exact organisation-number anchor; retain official-source provenance |
| BRREG normalized financials | `official.py` | QUALIFIED BASELINE | Preserve reporting period; 404/not-returned is not zero |
| BRREG roles/group/subunits | `official.py` | QUALIFIED BASELINE | Company-centric public role context only; preserve source state |
| Registry-listed company website | `website.py` + `identity.py` | CONDITIONAL | Publish/use only when exact website identity gate passes |
| BRREG email-domain website discovery (H1a) | `domain_discovery.py`, `run_registry_email_domain_discovery.py` | EXPERIMENTAL / AUDITED 200 | Candidate derives from official public email only; independently fetch and exact-entity gate; frozen dev+validation audit promoted 2/200 and both were manually correct, but sample is too small to claim 99.5% production precision; do not wire into competition runner yet |
| Company-site structured data/text | `website.py`, Scrapy pipeline | CONDITIONAL | Must inherit exact verified site identity and source URL/hash/time |
| Company-site social links | `identity.py`, `normalize_social_links.py` | CONDITIONAL | Company website must be exact and individual social handle must also pass its identity gate |
| Company-site news/activity | `extract_company_site_news.py`, `extract_company_site_activity.py` | CONDITIONAL | Exact verified company site; dated/evidence-backed claims only |
| Annual-report workforce | `run_annual_report_workforce_connector.py` | CONDITIONAL | Official filing evidence and correct reporting period required |
| Brave Search API standard terms | `run_brave_discovery.py`, `discovery.py` | BLOCKED FOR H1 BENCHMARK | 2026-09-01 standard terms reviewed 2026-09-13 restrict retention and use of Search Results for evaluating/benchmarking AI models/services; keep code reference-only unless custom terms explicitly permit this use |
| Tavily search | no promoted production integration | PLANNED / RIGHTS REVIEW | Candidate only; confirm exact current plan/terms, source-rights responsibilities, cost and transient-result handling before any H1b benchmark |
| Existing Google Maps result normalization | `normalize_google_maps_results.py` | EXPERIMENTAL | Do not relabel experimental data; evaluate official Google Places API path and audit entity precision |
| Official Google Places API | not yet promoted | PLANNED CANDIDATE | Implement only if Phase-1 failure map shows material value; document API terms/cost and exact-place/entity validation |
| Existing YouTube search connector | `run_youtube_search_connector.py` | EXPERIMENTAL | Prefer website-declared exact channel plus official API; search-only similarity is insufficient proof |
| Official YouTube Data API | not yet promoted | PLANNED CANDIDATE | Exact channel proof, declared cost/quota, dated metrics/activity evidence |
| Google News RSS | `run_google_news_rss_connector.py` | EXPERIMENTAL / RIGHTS REVIEW | Do not publish until acquisition/reproduction rights are documented and exact-entity article capture is validated |
| LinkedIn company discovery | `discover_linkedin_company_profiles.py` | EXPERIMENTAL DISCOVERY | Useful as candidate/URL research only unless a permitted/licensed path is established |
| LinkedIn guest experiment | `run_linkedin_guest_experiment.py` | EXPERIMENTAL | Not a production foundation; platform terms/reproducibility unresolved |
| LinkedIn guest jobs | `run_linkedin_guest_jobs_connector.py` | EXPERIMENTAL | Prefer company careers pages or permitted/licensed job feeds |
| Fagfolkguiden reviews | `run_fagfolkguiden_reviews_connector.py` | EXPERIMENTAL / RIGHTS REVIEW | Do not publish before rights + entity precision + evidence-span audit |
| Company careers/jobs pages | current website stack can be extended | PLANNED CANDIDATE | Prefer exact company-owned career pages; emit `job_posting` observations with dated URL/evidence |
| Independent licensed news/search provider | no final provider selected | PLANNED CANDIDATE | Choose only if measured activity gap justifies cost; declare licence/API/cost |
| Sentiment | `sentiment.py`, `run_sentiment_model.py` | DEFERRED / EXPERIMENTAL | Requires independent source evidence and labelled Norwegian evaluation; never infer company sentiment from marketing copy alone |
| Public LinkedIn/Meta/Indeed/Glassdoor scraping as core source | experimental/reference only | DEFERRED / REJECTED FOUNDATION | Starter architecture rejects this as a foundation due rights/reproducibility concerns |

## Promotion checklist

A connector cannot move to qualified publication until all of the following are demonstrated on a frozen audit corpus:

1. Acquisition mode and source rights are documented and genuinely valid.
2. Exact legal entity attribution is measured, not assumed from name similarity.
3. Evidence includes source URL, retrieval time, content hash and field-specific evidence span where required.
4. Wrong-company publication does not regress the accuracy gate.
5. The connector adds useful supported coverage on the development corpus.
6. The gain transfers to a zero-overlap validation corpus.
7. Request/runtime/cost impact fits the final 100-company batch budget with headroom.
8. Refresh behavior is deterministic/idempotent for the signal type.

If a connector fails rights or exact-entity validation, its data remains experimental even if it increases the local proxy score.
