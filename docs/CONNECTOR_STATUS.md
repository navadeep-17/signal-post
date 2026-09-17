# Connector qualification status

Updated: 2026-09-17

This is the publication-rights and production-readiness register. Code existing in the repository does not by itself make a source competition-safe or publishable.

Project cost policy: **$0 third-party API spend**. Builderr permits more, but paid/metered services are intentionally excluded unless the user explicitly changes this project policy.

Status meanings:

- **PRODUCTION / QUALIFIED** — enabled in the final runner under documented evidence/identity rules.
- **CONDITIONAL** — used only after an exact-company or field-specific gate passes.
- **EXPERIMENTAL** — measured locally; not final publication.
- **DROP / BLOCKED** — do not promote under current evidence, rights, cost, or measured yield.
- **DEFERRED / SHELVED** — potentially useful product intelligence, but not worth another connector cycle now.

| Source / connector | Current path | Status | Publication rule / measured result |
|---|---|---|---|
| Brønnøysund bulk/live registry | `official.py`, `batch.py` | **PRODUCTION / QUALIFIED** | Exact organisation-number anchor; preserve official provenance and missing states. |
| BRREG normalized financials | `official.py` | **PRODUCTION / QUALIFIED** | Preserve reporting period; missing/not-returned is never zero. |
| BRREG roles/group/subunits | `official.py` | **PRODUCTION / QUALIFIED** | Public exact-entity context only. |
| Registry-listed company website | `website.py`, `identity.py` | **CONDITIONAL / PRODUCTION PATH** | Publish/use only when exact website identity passes. |
| BRREG email-domain discovery H1a | `domain_discovery.py` | **EXPERIMENTAL / AUDITED** | Safe candidate nomination but off by default; 600-company audit qualified only a small number of domains. |
| Deterministic `.no` discovery H1c/H1d | `zero_cost_discovery.py`, registry/secondary identity guards | **PRODUCTION / QUALIFIED** | Candidate must be independently fetched and prove exact entity; known wrong-domain regressions remain quarantined. |
| Wikidata exact-org website fallback H1e | `wikidata_discovery.py`, `wikidata_fallback.py` | **PRODUCTION / QUALIFIED** | Exact `P2333` → `P856` only; Wikidata nominates a candidate and never proves identity. Candidate must pass independent company-page verification. |
| Hyphenated `.no` fallback H1g | final runner | **PRODUCTION / QUALIFIED** | Runs only when stronger website paths fail and request slots remain; fresh 300 gained 4 audited sites without changing the structural ceiling. |
| Company-owned description/structured page evidence | `website.py` | **CONDITIONAL / PRODUCTION PATH** | Must inherit exact verified site identity, source URL, retrieval time and hash. |
| Company-declared social handles H2a | `company_site_social.py`, `external_contract.py`, final runner | **PRODUCTION / QUALIFIED** | Narrow claim only: exact verified company page declared this profile URL. No claim of social activity/metrics. Fresh 300: 10 handles across 5 companies, zero added requests. |
| Company-site contact emails H2c | contact-email extractor + final contract | **PRODUCTION / QUALIFIED** | Email must occur in retained first-party evidence and registered email domain must match verified website domain. Fresh 300: 24 correct observations across 19 companies, zero added requests. |
| BRREG live workforce H2e | `registry_workforce.py`, `workforce_contract.py` | **PRODUCTION / QUALIFIED** | Exact BRREG employee count, zero added requests. Fresh 300: 45/300 companies. |
| BRREG annual-account OCR workforce H2g | production annual-report connector + final runner | **PRODUCTION / QUALIFIED** | Official exact-org PDF; exact org number recovered in OCR; company-scope FTE/employee phrase only; conflicts/group phrases abstain. Integrated fresh 300: 296/300 combined H2e+H2g workforce coverage; default 100 smoke: 100/100; $0. |
| Company-owned dated activity H2b | experimental extractors | **DROP unchanged design** | Fresh 300: only 1 company with qualifying dated activity. |
| Company careers/jobs H2f | experimental career-page screen | **DROP unchanged design** | 36 verified sites → 3 careers pages → 0 strict structured job claims; weak incremental leverage because workforce is already saturated. |
| Fagfolkguiden ratings/reviews H2h | coverage-screen script | **DROP / RIGHTS BLOCKED** | Fresh 100: 21 exact pages, 0 usable aggregate ratings. Source also exposed Google-derived review content without an identified sublicensing basis. |
| NAV jobs H2i | bounded feasibility screen | **SHELVED** | 20-company screen traversed 30,000 feed items and found 0 exact active jobs; adds little scoring leverage after H2e/H2g workforce saturation. |
| Brave / SerpApi / Tavily search | dormant discovery code | **BLOCKED** | Commercial/paid or terms unsuitable for the current $0 production strategy. |
| Google Places / commercial review APIs | not promoted | **BLOCKED BY COST POLICY** | Strong semantic fit to ratings, but paid/metered. |
| LinkedIn/Glassdoor/Indeed/public-platform scraping | experimental/reference only | **BLOCKED / REJECTED FOUNDATION** | Rights/reproducibility unresolved or adverse. |
| Official YouTube Data API | not promoted | **DEFERRED** | Exact declared channel reach is too sparse to justify a production dependency now. |
| Google News RSS / independent news | experimental | **DEFERRED / RIGHTS REVIEW** | No qualified broad zero-cost path. |
| Patentstyret open data | no production integration | **DEFERRED PRODUCT INTELLIGENCE** | Strong rights and exact-org potential, but IP filings are not an honest substitute for the remaining ratings/buzz/sentiment fields. |
| BRREG Støtteregisteret | no production integration | **DEFERRED PRODUCT INTELLIGENCE** | Strong official funding evidence, but weak fit to remaining scored external signal families. |
| Doffin procurement data | no production integration | **DEFERRED** | Useful activity evidence, but weak fit to remaining unsolved scoring families. |
| OpenStreetMap exact-org place data | no production integration | **REJECT as foundation** | Exact `ref:NO:orgnr` coverage is too sparse for systematic production use. |
| Sentiment | `sentiment.py`, experiment scripts | **DEFERRED** | Requires broad independent evidence and a labelled Norwegian evaluation set; never infer sentiment from company marketing text. |

## Stop rule for new connectors

Do not start another full connector cycle unless a candidate can plausibly satisfy all of these before production coding:

1. improves a genuinely unsolved Builderr-relevant information family rather than duplicating workforce;
2. publication/acquisition rights are suitable;
3. exact entity attribution is possible without weakening identity thresholds;
4. third-party cost remains $0 under current policy;
5. a cheap screen suggests roughly 5–10% random-company reach or equally strong hidden-evaluator value;
6. request/runtime cost fits the 100-company evaluator budget;
7. deterministic evidence and refresh semantics are possible.

Under the current source audit, broad connector hunting is paused. See `FINAL_SOURCE_LANDSCAPE_AUDIT.md`.

## Promotion checklist

A future connector cannot move to production until rights, exact identity, evidence metadata, precision, measured coverage gain, zero-overlap transfer, request/runtime/$0 constraints, and deterministic refresh behavior are all demonstrated on a frozen audit corpus.