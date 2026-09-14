# Connector qualification status

This file is the publication-rights and readiness register for external evidence. Code existing in the repository does not by itself make a source competition-safe or publishable.

Status meanings:

- **QUALIFIED BASELINE** — suitable for baseline publication under the starter's current evidence/identity rules.
- **CONDITIONAL** — usable only after an exact-source/company gate or field-specific requirement passes.
- **EXPERIMENTAL** — useful for local measurement, not final publication yet.
- **PLANNED** — preferred production acquisition path not yet implemented/qualified.
- **BLOCKED** — do not use for qualification/production under the currently reviewed rights, cost, or technical conditions.
- **DEFERRED** — not worth prioritizing until higher-value gaps are solved.

Project cost policy: the final strategy targets **$0 third-party API spend**. A free trial or small introductory quota that requires paid continuation is not a production dependency.

| Source / connector | Current code/path | Status | Publication rule / next action |
|---|---|---|---|
| Brønnøysund bulk/live registry | `official.py`, `batch.py` | QUALIFIED BASELINE | Exact organisation-number anchor; retain official-source provenance |
| BRREG normalized financials | `official.py` | QUALIFIED BASELINE | Preserve reporting period; 404/not-returned is not zero |
| BRREG roles/group/subunits | `official.py` | QUALIFIED BASELINE | Company-centric public role context only; preserve source state |
| Registry-listed company website | `website.py` + `identity.py` | CONDITIONAL | Publish/use only when exact website identity gate passes |
| BRREG email-domain website discovery (H1a) | `domain_discovery.py`, `run_registry_email_domain_discovery.py`, opt-in `run_competition_batch.py` flag | EXPERIMENTAL / AUDITED 600 / OPT-IN | Candidate derives from official public email only; independently fetch and hardened exact-entity gate. Frozen 600-company qualification audit had 62 candidates, 8 audited exact promotions, 54 quarantined, 267 requests and $0 third-party cost. Runner integration remains off by default and is enabled only with `--enable-email-domain-discovery`. The frozen 100-company runner benchmark improved canonical exact websites 2→3 at +86 requests. |
| Deterministic legal-name `.no` discovery (H1c) | `zero_cost_discovery.py`, `run_zero_cost_domain_discovery.py` | EXPERIMENTAL / ZERO-COST AUDIT | Generates at most two compact/hyphenated `.no` candidates, performs no search API call, independently fetches candidate homepages, and requires the normal identity gate plus an H1c page-level guard. Never treat DNS/HTTP success as company identity. |
| Company-site structured data/text | `website.py`, Scrapy pipeline | CONDITIONAL | Must inherit exact verified site identity and source URL/hash/time |
| Company-site social links | `identity.py`, `normalize_social_links.py` | CONDITIONAL | Company website must be exact and individual social handle must also pass its identity gate |
| Company-site news/activity | `extract_company_site_news.py`, `extract_company_site_activity.py` | CONDITIONAL | Exact verified company site; dated/evidence-backed claims only |
| Annual-report workforce | `run_annual_report_workforce_connector.py` | CONDITIONAL | Official filing evidence and correct reporting period required |
| Brave Search API standard terms | `run_brave_discovery.py`, `discovery.py` | BLOCKED | Rights review already blocked H1 benchmark use; paid/custom search is also outside the zero-cost final strategy |
| SerpApi Google Search API | `run_search_discovery.py`, `discovery.py`, manual `h1b-search-discovery.yml` | BLOCKED BY COST POLICY | Keep the provider-neutral H1b code dormant as research infrastructure. Do not configure or use SerpApi in the final strategy; its free quota is not sufficient as a permanent no-spend production dependency. |
| Tavily search | no promoted production integration | BLOCKED BY COST POLICY | Do not make a paid/limited commercial search API a final dependency. |
| Existing Google Maps result normalization | `normalize_google_maps_results.py` | EXPERIMENTAL | Do not relabel experimental data; no paid Google Places dependency will be added. |
| Official Google Places API | not yet promoted | BLOCKED BY COST POLICY | Paid/metered Places usage is outside the final zero-cost strategy. |
| Existing YouTube search connector | `run_youtube_search_connector.py` | EXPERIMENTAL | Prefer website-declared exact channel; do not depend on unofficial scraping for publication. |
| Official YouTube Data API | not yet promoted | DEFERRED / FREE-QUOTA REVIEW | Consider only if the required usage remains genuinely zero-cost without a paid continuation dependency and exact-channel proof is available. |
| Google News RSS | `run_google_news_rss_connector.py` | EXPERIMENTAL / RIGHTS REVIEW | Do not publish until rights and exact-entity article capture are validated; no paid news provider fallback. |
| LinkedIn company discovery | `discover_linkedin_company_profiles.py` | EXPERIMENTAL DISCOVERY | Useful as candidate/URL research only unless a permitted zero-cost path is established. |
| LinkedIn guest experiment | `run_linkedin_guest_experiment.py` | EXPERIMENTAL | Not a production foundation; platform terms/reproducibility unresolved. |
| LinkedIn guest jobs | `run_linkedin_guest_jobs_connector.py` | EXPERIMENTAL | Prefer company careers pages; no paid jobs provider dependency. |
| Fagfolkguiden reviews | `run_fagfolkguiden_reviews_connector.py` | EXPERIMENTAL / RIGHTS REVIEW | Do not publish before rights + entity precision + evidence-span audit. |
| Company careers/jobs pages | current website stack can be extended | PLANNED CANDIDATE | Prefer exact company-owned career pages; emit conservative evidence-backed hiring/job observations. |
| Independent licensed news/search provider | no final provider selected | BLOCKED BY COST POLICY | A paid licensed search/news service is outside the final zero-cost strategy. |
| Sentiment | `sentiment.py`, `run_sentiment_model.py` | DEFERRED / EXPERIMENTAL | Requires independent source evidence and labelled Norwegian evaluation; never infer company sentiment from marketing copy alone. |
| Public LinkedIn/Meta/Indeed/Glassdoor scraping as core source | experimental/reference only | DEFERRED / REJECTED FOUNDATION | Starter architecture rejects this as a foundation due rights/reproducibility concerns. |

## Promotion checklist

A connector cannot move to qualified publication until all of the following are demonstrated on a frozen audit corpus:

1. Acquisition mode and source rights are documented and genuinely valid.
2. Exact legal entity attribution is measured, not assumed from name similarity.
3. Evidence includes source URL, retrieval time, content hash and field-specific evidence span where required.
4. Wrong-company publication does not regress the accuracy gate.
5. The connector adds useful supported coverage on the development corpus.
6. The gain transfers to a zero-overlap validation corpus.
7. Request/runtime impact fits the final 100-company batch budget with headroom and third-party API cost remains $0.
8. Refresh behavior is deterministic/idempotent for the signal type.

If a connector fails rights, exact-entity validation, or the zero-cost policy, its data remains experimental even if it increases the local proxy score.
