# Final source, licence, acquisition and runtime declaration

Updated: 2026-10-01

This document describes the current production submission path used by `scripts/run_signalpost_v2.py`. The filename of that wrapper is retained for compatibility with the previously submitted revision; the current evaluator path includes the subsequently qualified V3–V5 layers documented in `SUBMISSION.md`.

Experimental scripts elsewhere in the repository are not enabled by the evaluator path and must not be interpreted as submission sources.

This is an engineering/source-rights declaration, not legal advice. When a source does not grant a blanket content-reuse licence, Signalpost minimizes retained material and publishes bounded factual evidence with provenance instead of republishing source pages.

## Production source register

| Source | Production use | Acquisition | Licence / rights basis | What is retained/published | Important boundary |
|---|---|---|---|---|---|
| Brønnøysundregistrene entity bulk/live API | exact identity anchor, legal name/form, municipality, industry/status facts, registered activity/purpose, employee count, latest-account metadata | Official bulk download and official REST API | BRREG open-data datasets are published under NLOD 2.0. Attribution: Brønnøysundregistrene. | normalized facts plus source URL, retrieval time, hash/evidence metadata | org number remains the anchor; absence is not converted to zero |
| BRREG roles/group/subunits | leadership roles, group relationships, registered establishments | Official REST APIs | BRREG open-data datasets under NLOD 2.0 | company-centric role/location/group facts and provenance | birth dates are discarded; inactive/departed appointments are not presented as current canonical people facts |
| BRREG normalized accounts | annual financial fields | Official REST API | BRREG open-data datasets under NLOD 2.0 | period-aware normalized financial claims and evidence | missing records/source errors remain explicit; values are not imputed |
| BRREG annual-account copy | company-scope workforce evidence and conservative company-description evidence | Official BRREG account-copy endpoint; local PDF text extraction/OCR | Official BRREG service. Signalpost stores bounded extracted claim evidence/hash metadata and does not redistribute filing PDFs in the repository. | source URL, retrieval time, PDF SHA-256, reporting/effective year and bounded workforce/description claim spans | target org number must be recovered from the filing; group-only, ambiguous or conflicting text abstains |
| BRREG Enhetsregister update feed | recent exact-org official registry-change history | Official REST API with exact `organisasjonsnummer` batching and `includeChanges=true` | BRREG open-data service / NLOD 2.0 attribution basis | event id, event date/type, allowlisted change path/value, source/retrieval URL, retrieval time, content hash and bounded summary | **official registry change only**; never presented as company-authored news, hiring, social activity or press release; unknown paths abstain |
| Wikidata structured data | candidate discovery for an official website | Bounded WDQS batches keyed by Norwegian organisation number (P2333) and official website (P856) | Wikidata structured data is CC0 | candidate URL and lookup diagnostics sufficient for discovery | candidate only; independent company-page identity proof is required before website publication |
| Verified company-owned public web pages | official-site proof and bounded description/contact/social/job/update evidence | bounded public HTTP retrieval with safe URL/redirect handling and robots behavior | No blanket content-reuse licence is assumed | source URL, retrieval time, hash, bounded factual claim span, normalized outbound URL/email and narrowly scoped role/update facts when strict gates pass | exact-company proof required; ambiguous/wrong-entity pages abstain; generic careers/news indexes, cross-domain pages and weak pages are not published as facts |

Official references:

- BRREG open data: https://www.brreg.no/bruke-data-fra-bronnoysundregistrene/apne-data/
- BRREG Enhetsregisteret documentation: https://data.brreg.no/enhetsregisteret/api/dokumentasjon/en/index.html
- NLOD 2.0: https://data.norge.no/nlod/en/2.0
- Wikidata licensing: https://www.wikidata.org/wiki/Wikidata:Licensing

## Exact-org BRREG registry narrative boundary

The current runner reuses the exact organisation-number registry row already retained by the base collector. It can expose:

- literal `aktivitet` as a fallback company description when no stronger published description exists; and
- literal `vedtektsfestetFormaal` separately as `registered_purpose`.

This projection performs zero additional network requests. It does not infer a description from an industry code and does not rewrite a legal purpose as operating activity.

## BRREG annual-account copy boundary

The annual-account layer is deliberately bounded. It may use `pypdf` digital-text extraction and, when necessary, local Poppler/Tesseract OCR. The filing is used only after exact organisation-number proof is recovered from the document.

Workforce extraction requires unambiguous company-scope employee/FTE language. Company-description extraction requires conservative company-scope descriptive language and rejects false-positive/group-only patterns. Missing, weak or conflicting evidence abstains.

The full filing PDF is not committed as submission evidence. The output retains bounded factual spans, source URL, timestamps and hashes sufficient to audit the published fact.

## Official BRREG registry-change boundary

Production connector: `src/norway_company_agent/brreg_changes.py`.

Endpoint:

`https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter`

The connector:

- filters by exact 9-digit organisation number;
- batches up to 100 organisations/request;
- requests `includeChanges=true`;
- uses a 365-day lookback;
- publishes at most the three newest qualified events/company;
- rejects returned organisations outside the requested batch;
- preserves BRREG event id/date/type and exact JSON-patch paths;
- publishes only a conservative allowlist of paths with stable interpretation;
- treats source-attribution/schema integrity errors as hard qualification failures;
- adds no paid or secret-bearing API.

Published claim boundary:

> an exact target organisation had this dated update recorded by Brønnøysundregistrene.

It does **not** mean:

- the company authored an announcement;
- the company posted to social media;
- the company is hiring;
- a press/news outlet reported the change;
- the event proves an operational cause or intent.

Canonical registry-change facts therefore live under `company.registry_change`, not `public_activity`.

Fresh exact-production-head qualification (`36892430561`) produced 156 qualified registry-change claims across 100/100 fresh companies in one shared request, with zero integrity/evidence/contract/canonical/synthesis errors and $0 third-party cost. Full measurement details are in `docs/V5_BRREG_CHANGE_PRODUCTION.md`.

## Company-owned page policy

The web layer is used to establish exact company identity and retain narrowly scoped factual evidence. Public accessibility is not treated as permission to republish an entire site.

Production behavior:

- validates URL/redirect destinations and blocks unsafe/private-network targets;
- uses bounded page retrieval rather than open-ended crawling;
- follows the repository's robots/safe-HTTP policy;
- stores source URL, retrieval time, content hash and bounded evidence span;
- publishes a website only after exact-company identity evidence passes;
- treats parent, brand, franchise and namesake pages as non-exact unless the target legal entity is proven;
- does not infer a missing value from a page that was not successfully qualified.

### Strict first-party hiring boundary

A generic careers page, careers keyword, navigation link or section index is never a hiring fact. Signalpost publishes a job only from an already-retained page on the exact verified company-owned site when all strict conditions hold: a job/career-like **detail URL**, a specific non-generic title, a job-detail marker and an explicit apply/application action. Cross-domain pages and generic filtered indexes are rejected.

The claim records the role title/page URL plus bounded evidence/provenance. It does not assert that a job is still open after retrieval time or infer organisation-wide hiring intensity.

### Strict first-party company-update boundary

A generic news/blog/press index is never a company-update fact. Signalpost publishes an update only from an already-retained same-site **detail page** with a specific non-generic title and an explicit date. Undated section pages are rejected.

The system retains the normalized title/URL/date and bounded evidence metadata; it does not republish the article body.

## Social-platform boundary

The production runner makes **zero requests to social platforms**.

`external.profile_handle` claims are derived only from social URLs explicitly declared by an exact verified company-owned page. The claim means only:

> the verified company page declared this profile URL at retrieval time.

It does **not** mean the platform page was fetched, is currently controlled by the company, is platform-verified, is active, or has any known follower/engagement/sentiment metric.

LinkedIn, Meta, YouTube, TikTok and X are therefore URL destinations in this claim family, not scraped production sources.

## Contact-email boundary

`external.contact_email` is a zero-network projection over retained verified company-page evidence. Publication requires the email to appear in a bounded footer/contact/legal context and its registered domain to match the verified company website registered domain.

The claim does not assert mailbox deliverability, inbox ownership, response likelihood or consent for marketing use.

## Models and local processing

The production runner invokes **no LLM and no sentiment model**.

Annual-report extraction may use local:

- Poppler `pdftoppm` for PDF rasterization;
- Tesseract OCR with language `eng`;
- `pypdf` for digital-text extraction.

These are local processing tools, not paid external inference APIs. If OCR executables are unavailable, OCR-dependent extraction abstains and the run continues producing terminal company output.

## API, request and cost declaration

Production policy:

- paid third-party APIs: **none**;
- LLM APIs: **none**;
- search APIs: **none**;
- social-platform APIs/scraping: **none**;
- third-party API spend: **$0.00**;
- conservative request ceiling: **2,000 per 100 companies**.

V5 request budgeting reserves the BRREG registry-change feed before running the base collector. For 100 companies:

- change-feed logical ceiling: 1 request;
- conservative multiplier: 2;
- reserved charge: 2;
- base-runner maximum: 1,998;
- combined theoretical ceiling: 2,000.

The exact-production-head fresh 100 observed 1,382 conservative requests total and completed in 414.534 seconds.

## Cache and retention declaration

The production runner writes local per-run work artifacts such as normalized profiles and internal envelopes. Evidence records contain provenance metadata required for auditability: source URL, retrieval timestamp, content hash and bounded claim span.

The submission does not require a hosted database or persistent third-party cache. The BRREG bulk file is a run input/snapshot. Wikidata candidate responses are not publication proof; the independently fetched qualifying company page is.

## Hosting declaration

No external hosting is required to execute or inspect the submission. The evidence workspace is a static HTML artifact generated locally from final JSONL. The historical deterministic product built from the immutable certified corpus remains committed at `submission/signalpost-v2.html`.

## Explicitly excluded from the production stack

The following experiments/ideas are not submission sources:

- paid/permitted search-provider experiments;
- direct LinkedIn guest/profile/jobs collection;
- Meta platform collection;
- Google Maps/review scraping;
- Fagfolkguiden/Google-derived review publication;
- NAV job-feed publication;
- independent-news sentiment;
- Hugging Face sentiment models;
- guessed `.com` fallback;
- broad additional guessed-domain variants beyond the qualified website-discovery order;
- Støtteregisteret production enrichment after its fresh 0/20 exact-org screen;
- Patentstyret/Doffin production connectors until credentialed exact-org screening is possible.

Historical design documents may discuss those experiments. `SUBMISSION.md`, `submission/manifest.json`, this file, `docs/V5_BRREG_CHANGE_PRODUCTION.md` and the immutable release audit are authoritative for the submitted path.
